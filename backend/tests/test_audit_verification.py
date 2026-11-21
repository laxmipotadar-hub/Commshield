"""Tests verifying strict adherence to empirical data sources, dynamic attribution, and dwell time.

1. Benchmark endpoint returns only numbers present in result files (no hardcoded metrics).
2. Control-slice concordance is computed dynamically, not a constant.
3. SHAP values sum consistently for a sample window.
4. Dwell time blocks a second promotion inside the interval.
"""

from datetime import datetime, timezone
import json
from pathlib import Path
import pytest
from fastapi import HTTPException
import numpy as np
from sklearn.ensemble import IsolationForest
import shap

from backend.app.database import SessionLocal
from backend.app.models import (
    ApprovalLog,
    Baseline,
    BaselineRegistry,
    CanonicalWindow,
    DetectionResult,
    AttributionResult,
)
from backend.app.services.governance import governance_service
from backend.app.services.detection import detection_service
from backend.app.api.governance import get_three_arm_comparison
from backend.app.api.windows import explain_window
from ml_engine.attribution.metrics import compute_control_slice_concordance, evaluate_threat_indicators
from ml_engine.governance.candidate import build_shadow_candidate
from ml_engine.governance.config import DWELL_TIME_MIN_SECONDS
from ml_engine.preprocessing.windowing import FEATURE_NAMES

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def embb_baseline_bundles(db):
    slice_id = "sst-1-sd-010203"
    act_bundle = detection_service.get_baseline_bundle(slice_id, db=db)
    anc_row = db.query(Baseline).filter(Baseline.slice_id == slice_id, Baseline.is_anchor == True).first()
    anc_bundle = act_bundle
    if anc_row and anc_row.model_artifact_path and Path(anc_row.model_artifact_path).is_file():
        import joblib
        anc_bundle = joblib.load(anc_row.model_artifact_path)
    return act_bundle, anc_bundle


def test_benchmark_endpoint_returns_only_numbers_from_result_files(db):
    """Verify that three-arm comparison endpoint loads real persisted numbers without hardcoded mock values."""
    synth_summary_path = PROJECT_ROOT / "experiments" / "results" / "experiment_summary.json"
    if not synth_summary_path.is_file():
        synth_summary_path = PROJECT_ROOT / "experiments" / "snapshot" / "experiment_summary.json"

    assert synth_summary_path.is_file(), "experiment_summary.json must exist"

    with open(synth_summary_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    expected_sc = data["summaries"]["attack_in_growth"]
    expected_arm_c = expected_sc["arms"]["arm_c_commshield"]

    # Call endpoint function directly
    res = get_three_arm_comparison(dataset_id="attack_in_growth", db=db)
    res_dict = res.model_dump()

    assert "arms" in res_dict
    assert "arm_c_commshield" in res_dict["arms"]
    arm_c = res_dict["arms"]["arm_c_commshield"]

    # Must match real measured numbers exactly
    assert arm_c["recall"] == expected_arm_c["recall_mean"]
    assert arm_c["false_alarm_rate"] == expected_arm_c["fpr_mean"]
    assert arm_c["contamination"] == expected_arm_c["contamination_mean"]
    assert arm_c["adaptations"] == expected_arm_c["adaptations_mean"]

    # Verify poisoning_susceptibility is completely absent
    for arm_k, arm_val in res_dict["arms"].items():
        assert "poisoning_susceptibility" not in arm_val


def test_control_slice_concordance_is_computed_not_constant():
    """Verify control_slice_concordant computes from second slice data and toggles dynamically."""
    base_comp = {"registration_ratio": 0.08, "session_setup_ratio": 0.90, "failure_ratio": 0.01, "other_signalling_ratio": 0.01}
    slice1_win = {
        "slice_id": "sst-1-sd-010203",
        "composition_vector": base_comp,
        "ratio_features": {"pdu_session_rate_per_ue": 1.0},
    }

    # 1. Matching control slice -> True
    slice2_matching = {
        "slice_id": "sst-2-sd-010203",
        "composition_vector": base_comp,
        "ratio_features": {"pdu_session_rate_per_ue": 1.05},
    }
    assert compute_control_slice_concordance(slice1_win, slice2_matching) is True

    # 2. Diverging control slice -> False
    slice2_divergent = {
        "slice_id": "sst-2-sd-010203",
        "composition_vector": {"registration_ratio": 0.60, "session_setup_ratio": 0.20, "failure_ratio": 0.15, "other_signalling_ratio": 0.05},
        "ratio_features": {"pdu_session_rate_per_ue": 5.0},
    }
    assert compute_control_slice_concordance(slice1_win, slice2_divergent) is False

    # 3. Missing second-slice data -> None
    assert compute_control_slice_concordance(slice1_win, None) is None

    # 4. evaluate_threat_indicators reflects concordance status
    indicators_none = evaluate_threat_indicators(
        current_ratios={}, baseline_bundle={}, control_slice_concordant=None
    )
    assert indicators_none["control_slice_concordance"] is None

    indicators_true = evaluate_threat_indicators(
        current_ratios={}, baseline_bundle={}, control_slice_concordant=True
    )
    assert indicators_true["control_slice_concordance"] == "NETWORK_WIDE_EXPANSION"

    indicators_false = evaluate_threat_indicators(
        current_ratios={}, baseline_bundle={}, control_slice_concordant=False
    )
    assert indicators_false["control_slice_concordance"] == "LOCALIZED_TO_SLICE_1"


def test_shap_values_sum_consistently_on_flagged_window(db):
    """Verify SHAP values additivity property with TreeExplainer on IsolationForest."""
    rng = np.random.RandomState(42)
    X = rng.randn(60, len(FEATURE_NAMES))
    clf = IsolationForest(n_estimators=30, random_state=42).fit(X)

    sample = X[:1]
    explainer = shap.TreeExplainer(clf)
    sv = explainer.shap_values(sample)[0]

    # SHAP additivity: expected_value + sum(shap_values) == raw prediction
    expected_val = float(explainer.expected_value[0] if hasattr(explainer.expected_value, "__len__") else explainer.expected_value)
    computed_sum = float(np.sum(sv))
    total_val = expected_val + computed_sum

    raw_pred = explainer.model.predict(sample)[0]
    assert np.isclose(total_val, raw_pred, atol=1e-5), f"SHAP sum {total_val} != raw {raw_pred}"
    assert len(sv) == len(FEATURE_NAMES)

    # Verify explain_window endpoint logic on DB window
    now_dt = datetime.now(timezone.utc)
    win_id = f"test-explain-win-{int(now_dt.timestamp())}"
    win = CanonicalWindow(
        id=win_id,
        slice_id="sst-1-sd-010203",
        nf_id="UPF-01",
        window_start=now_dt,
        window_end=now_dt,
        duration_sec=60,
        raw_counters={"total_packets": 1000},
        ratio_features={f: 1.0 for f in FEATURE_NAMES},
        composition_vector={"registration_ratio": 0.08, "session_setup_ratio": 0.90, "failure_ratio": 0.01, "other_signalling_ratio": 0.01},
    )
    active_base = db.query(Baseline).filter(Baseline.slice_id == "sst-1-sd-010203", Baseline.is_active == True).first()
    base_id = active_base.id if active_base else "base-test-id"

    det = DetectionResult(
        id=f"det-{win_id}",
        window_id=win_id,
        slice_id="sst-1-sd-010203",
        baseline_id=base_id,
        if_score=0.5,
        if_percentile=99.0,
        ae_recon_error=0.1,
        ae_percentile=98.0,
        fused_percentile=99.2,
        cusum_score=0.0,
        agreement_state="both_fired",
        is_anomalous=True,
    )
    attr = AttributionResult(
        id=f"attr-{win_id}",
        window_id=win_id,
        slice_id="sst-1-sd-010203",
        drift_detected=False,
        verdict="likely_attack",
        jsd_divergence=0.0,
        scaling_factor_k=1.0,
        evidence_signals={},
    )
    db.add(win)
    db.add(det)
    db.add(attr)
    db.commit()

    explain_resp = explain_window(window_id=win_id, db=db)
    assert explain_resp.is_anomalous is True
    assert len(explain_resp.shap_values) == len(FEATURE_NAMES)
    assert not np.isnan(sum(explain_resp.shap_values.values()))


def test_dwell_time_blocks_second_promotion_inside_interval(db, embb_baseline_bundles):
    """Verify dwell time enforces minimum delay between promotions and appends to decision trace."""
    act_bundle, anc_bundle = embb_baseline_bundles
    slice_id = "sst-1-sd-010203"

    # Ensure clean approval log for slice
    db.query(ApprovalLog).filter(ApprovalLog.slice_id == slice_id).delete()
    db.commit()

    legit_win = {
        "window_id": f"win-dwell-1-{int(datetime.now(timezone.utc).timestamp())}",
        "slice_id": slice_id,
        "raw_counters": {"total_bytes_uplink": 100_000, "total_bytes_downlink": 500_000},
        "ratio_features": {f: 0.0 for f in FEATURE_NAMES},
        "composition_vector": {"registration_ratio": 0.08, "session_setup_ratio": 0.90, "failure_ratio": 0.01, "other_signalling_ratio": 0.01},
        "attribution": {"verdict": "likely_benign"},
    }

    try:
        # 1. Build and promote Candidate 1
        _, cand_row1 = build_shadow_candidate(
            slice_id=slice_id,
            active_bundle=act_bundle,
            anchor_bundle=anc_bundle,
            adaptation_windows=[legit_win],
            db=db,
        )
        cand_row1.gate_metrics = {"all_mandatory_passed": True, "overall_passed": True}
        db.commit()

        governance_service.approve_and_promote(
            candidate_id=cand_row1.id,
            analyst_id="analyst_test",
            notes="First promotion",
            db=db,
        )

        db.refresh(cand_row1)
        assert any("Dwell time check: PASSED" in line for line in cand_row1.decision_trace)

        # 2. Build Candidate 2 immediately (within DWELL_TIME_MIN_SECONDS interval)
        _, cand_row2 = build_shadow_candidate(
            slice_id=slice_id,
            active_bundle=act_bundle,
            anchor_bundle=anc_bundle,
            adaptation_windows=[legit_win],
            db=db,
        )
        cand_row2.gate_metrics = {"all_mandatory_passed": True, "overall_passed": True}
        db.commit()

        # Promotion 2 should be rejected with 409
        with pytest.raises(HTTPException) as exc_info:
            governance_service.approve_and_promote(
                candidate_id=cand_row2.id,
                analyst_id="analyst_test",
                notes="Second promotion too rapid",
                db=db,
            )

        assert exc_info.value.status_code == 409
        assert "Dwell time violation" in exc_info.value.detail

        db.refresh(cand_row2)
        assert any("Dwell time check: FAILED" in line for line in cand_row2.decision_trace)
    finally:
        # Clean up: rollback to trusted anchor and clear test approval logs
        try:
            governance_service.rollback_baseline(
                slice_id=slice_id,
                target_version="v1.0.0-anchor",
                analyst_id="analyst_test",
                reason="Cleanup dwell time test promotion",
                db=db,
            )
        except Exception:
            pass
        db.query(ApprovalLog).filter(ApprovalLog.slice_id == slice_id).delete()
        db.commit()
        detection_service.clear_cache()
