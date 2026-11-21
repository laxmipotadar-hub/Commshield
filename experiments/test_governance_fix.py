"""Unit tests for CommShield Governance Fix (Stage S5):
1. Ratio-only drift budget is invariant under 2x scaling.
2. Canary attacks are rescaled equally for anchor and candidate.
3. Poisoned candidate fails at least one mandatory governance gate.
"""

from copy import deepcopy
import json
from pathlib import Path
import sys
import pytest
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
backend_path = PROJECT_ROOT / "backend"
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

from ml_engine.governance.checks import (
    DriftBudgetCheck,
    NormalHoldoutBacktestCheck,
    ProportionalGrowthCheck,
    CanaryRetentionTestCheck,
    build_default_governance_pipeline,
)
from ml_engine.governance.canary import (
    evaluate_canary_retention,
    load_canary_dataset,
    rescale_canary_window,
)
from ml_engine.governance.candidate import (
    build_shadow_candidate,
    load_base_training_windows,
)
from ml_engine.governance.naive_adapter import naive_retrain_on_drift
from ml_engine.governance.config import (
    RATIO_FEATURE_NAMES,
    DRIFT_BUDGET_CUMULATIVE_B_RMS,
    DRIFT_BUDGET_MAX_FEATURE_B_MAX,
    CANARY_RECALL_MARGIN_DELTA,
)
from ml_engine.preprocessing.windowing import FEATURE_NAMES, RobustScaler
from ml_engine.detection.isolation_forest import IsolationForestDetector

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SYNTHETIC_DIR = PROJECT_ROOT / "data" / "synthetic"


@pytest.fixture
def base_anchor_bundle():
    """Build a standard benign anchor baseline bundle for testing."""
    slice_id = "sst-1-sd-010203"
    base_windows = load_base_training_windows(slice_id)
    assert len(base_windows) > 0, "Base training windows required for testing"

    scaler = RobustScaler(feature_names=FEATURE_NAMES)
    scaler.fit(base_windows)

    X_list = [
        [scaler.transform_vector(w.get("ratio_features", {}))[f] for f in FEATURE_NAMES]
        for w in base_windows
    ]
    X = np.array(X_list, dtype=np.float32)

    det = IsolationForestDetector(threshold_percentile=95.0, random_state=42)
    det.fit(X)

    bundle = {
        "slice_id": slice_id,
        "version": "v1.0.0-anchor-test",
        "scaler": scaler,
        "scaler_params": scaler.to_dict(),
        "detector": det,
        "isolation_forest": det,
        "detectors": {"isolation_forest": det},
        "threshold_params": {"threshold_percentile": 95.0, "cusum_threshold": 4.5},
        "feature_schema": {"features": FEATURE_NAMES},
        "training_windows": base_windows,
        "holdout_windows": base_windows[-15:],
        "composition_vector": {
            "registration_ratio": 0.0778,
            "session_setup_ratio": 0.9122,
            "failure_ratio": 0.0044,
            "other_signalling_ratio": 0.0056,
        },
    }
    return bundle


def test_ratio_only_budget_invariant_under_2x_scaling(base_anchor_bundle):
    """Verify that ratio-only drift budget is scale-invariant under 2x volume scaling."""
    anchor_bundle = base_anchor_bundle
    base_windows = anchor_bundle["training_windows"]

    # Generate 2x scaled windows where users and sessions scale proportionally
    scaled_windows = []
    for w in base_windows:
        w_scaled = deepcopy(w)
        raw = w_scaled.get("raw_counters", {})
        raw["total_bytes_uplink"] = int(raw.get("total_bytes_uplink", 0) * 2.0)
        raw["total_bytes_downlink"] = int(raw.get("total_bytes_downlink", 0) * 2.0)
        raw["total_packets"] = int(raw.get("total_packets", 0) * 2.0)
        raw["active_ue_count"] = int(raw.get("active_ue_count", 0) * 2.0)
        raw["pdu_sessions_established"] = int(raw.get("pdu_sessions_established", 0) * 2.0)
        # In proportional scaling, ratio features (failures, session rate per UE, reg per UE) remain identical
        scaled_windows.append(w_scaled)

    cand_scaler = RobustScaler(feature_names=FEATURE_NAMES)
    cand_scaler.fit(scaled_windows)

    cand_bundle = deepcopy(anchor_bundle)
    cand_bundle["version"] = "v1.1.0-scaled-2x"
    cand_bundle["scaler"] = cand_scaler
    cand_bundle["scaler_params"] = cand_scaler.to_dict()

    # 1. Evaluate with ratio-only drift budget check
    ratio_budget_check = DriftBudgetCheck(ratio_only=True)
    res_ratio = ratio_budget_check.evaluate(
        candidate_bundle=cand_bundle,
        active_bundle=anchor_bundle,
        anchor_bundle=anchor_bundle,
        context={"ratio_only_budget": True},
    )

    assert res_ratio.passed is True, f"Ratio-only budget failed under 2x scaling: {res_ratio.explanation}"
    assert res_ratio.metrics["d_rms_anchor"] <= DRIFT_BUDGET_CUMULATIVE_B_RMS
    assert res_ratio.metrics["d_max_anchor"] <= DRIFT_BUDGET_MAX_FEATURE_B_MAX
    # Under exact proportional scaling, distance on ratio-only features must be strictly zero
    assert res_ratio.metrics["d_rms_anchor"] == pytest.approx(0.0, abs=1e-5)
    assert res_ratio.metrics["d_max_anchor"] == pytest.approx(0.0, abs=1e-5)

    # 2. Contrast with fat-pipe scaling (where volume-denominated ratios are multiplied by 2x)
    fat_pipe_windows = []
    for w in base_windows:
        w_fp = deepcopy(w)
        ratios = w_fp.get("ratio_features", {})
        ratios["bytes_per_session"] = float(ratios.get("bytes_per_session", 1000.0)) * 2.0
        ratios["gtpu_volume_per_ue"] = float(ratios.get("gtpu_volume_per_ue", 1000.0)) * 2.0
        fat_pipe_windows.append(w_fp)

    fat_scaler = RobustScaler(feature_names=FEATURE_NAMES)
    fat_scaler.fit(fat_pipe_windows)
    fat_bundle = deepcopy(anchor_bundle)
    fat_bundle["scaler"] = fat_scaler
    fat_bundle["scaler_params"] = fat_scaler.to_dict()

    # All-features check on fat pipe shifts massively
    all_features_check = DriftBudgetCheck(ratio_only=False)
    res_all = all_features_check.evaluate(
        candidate_bundle=fat_bundle,
        active_bundle=anchor_bundle,
        anchor_bundle=anchor_bundle,
        context={"ratio_only_budget": False},
    )
    assert res_all.passed is False, "Expected all-features budget to detect fat-pipe volume shift"
    assert res_all.metrics["d_max_anchor"] > DRIFT_BUDGET_MAX_FEATURE_B_MAX


def test_canary_rescaled_equally_for_anchor_and_candidate(base_anchor_bundle):
    """Verify that canary windows are rescaled equally for both anchor and candidate."""
    anchor_bundle = base_anchor_bundle
    canaries = load_canary_dataset(slice_id=anchor_bundle["slice_id"], max_canaries=10)
    assert len(canaries) > 0, "Canary dataset must contain windows"

    # Candidate trained on benign data
    cand_bundle = deepcopy(anchor_bundle)
    cand_bundle["version"] = "v1.1.0-cand-equal-rescale"

    # Evaluate retention at 2.0x volume multiplier
    res = evaluate_canary_retention(
        active_bundle=anchor_bundle,
        candidate_bundle=cand_bundle,
        canary_windows=canaries,
        volume_multiplier=2.0,
        margin_delta=CANARY_RECALL_MARGIN_DELTA,
    )

    assert res["passed"] is True
    # When both bundles share identical detectors and score equally-rescaled canaries, recall must match
    assert res["active_recall"] == res["candidate_recall"]
    assert res["recall_delta"] == pytest.approx(0.0, abs=1e-4)

    # Verify that individual window rescaling produces valid invariant ratio values under proportional mode
    sample_canary = canaries[0]
    rescaled_1x = rescale_canary_window(sample_canary, volume_multiplier=1.0)
    rescaled_2x = rescale_canary_window(sample_canary, volume_multiplier=2.0)

    # Raw counts scaled by 2x
    assert rescaled_2x["raw_counters"]["total_bytes_uplink"] == 2 * rescaled_1x["raw_counters"]["total_bytes_uplink"]
    # Ratio features invariant in proportional mode
    assert rescaled_2x["ratio_features"]["pdu_session_rate_per_ue"] == pytest.approx(
        rescaled_1x["ratio_features"]["pdu_session_rate_per_ue"]
    )
    assert rescaled_2x["ratio_features"]["gtpu_volume_per_ue"] == pytest.approx(
        rescaled_1x["ratio_features"]["gtpu_volume_per_ue"]
    )


def test_poisoned_candidate_fails_at_least_one_gate(base_anchor_bundle):
    """Verify that a poisoned candidate trained on attack windows fails at least one mandatory gate."""
    anchor_bundle = base_anchor_bundle
    slice_id = anchor_bundle["slice_id"]

    # Synthesize poisoned adaptation windows with severe signaling attack characteristics
    poisoned_windows = [
        {
            "window_id": f"poison-unit-win-{i}",
            "slice_id": slice_id,
            "raw_counters": {
                "total_bytes_uplink": 800_000_000,
                "total_bytes_downlink": 4_000_000_000,
                "total_packets": 5_000_000,
                "active_ue_count": 600,
                "pdu_sessions_established": 10_000,
            },
            "ratio_features": {
                "registrations_per_active_ue": 0.60,       # severe anomaly
                "nas_failure_ratio": 0.35,                 # signaling flood / drop
                "pfcp_failure_ratio": 0.20,                # core failure
                "pdu_session_rate_per_ue": 16.67,          # abnormal session rate
                "bytes_per_session": 480000.0,
                "packets_per_session": 500.0,
                "gtpu_volume_per_ue": 8000000.0,
                "ue_hash_entropy": 2.1,
                "new_ue_rate": 0.40,
            },
            "composition_vector": {
                "registration_ratio": 0.55,
                "session_setup_ratio": 0.15,
                "failure_ratio": 0.25,
                "other_signalling_ratio": 0.05,
            },
            "attribution": {"verdict": "likely_benign"},   # attacker attempts to masquerade
        }
        for i in range(10)
    ]

    poisoned_bundle = naive_retrain_on_drift(
        slice_id=slice_id,
        recent_windows=poisoned_windows,
        active_baseline_bundle=anchor_bundle,
    )

    pipeline = build_default_governance_pipeline()
    eval_result = pipeline.evaluate(
        candidate_bundle=poisoned_bundle,
        active_bundle=anchor_bundle,
        anchor_bundle=anchor_bundle,
        context={
            "adaptation_windows": poisoned_windows,
            "normal_holdout_windows": anchor_bundle["holdout_windows"],
            "ratio_only_budget": True,
        },
    )

    assert eval_result.all_mandatory_passed is False, "Poisoned candidate must NOT pass all mandatory gates"
    assert eval_result.overall_passed is False

    failed_checks = [c.name for c in eval_result.check_results if not c.passed]
    assert len(failed_checks) >= 1, f"Expected at least one failed check, got: {failed_checks}"
