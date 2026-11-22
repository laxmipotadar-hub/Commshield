"""Unit tests for CommShield Drift Attribution:
- Pure proportional growth gives likely_benign
- Composition shift gives likely_attack
- Conflicting signals give uncertain with a named reason
- Uncertain windows land in quarantine_windows
- Every attribution has a complete decision trace
"""

from datetime import datetime, timezone
import json
from pathlib import Path
import pytest
from httpx import AsyncClient, ASGITransport

from backend.app.database import SessionLocal
from backend.app.main import app
from backend.app.models import (
    CanonicalWindow,
    DecisionTrace,
    DriftEvent,
    QuarantineWindow,
)
from backend.app.services.attribution import attribution_service
from ml_engine.attribution import (
    AbstainReason,
    AttributionVerdict,
    RecommendedAction,
    RuleBasedAttributor,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
SYNTHETIC_DATA_DIR = PROJECT_ROOT / "data" / "synthetic"


@pytest.fixture
def baseline_bundle():
    """Baseline bundle reference with training statistics."""
    return {
        "slice_id": "sst-1-sd-010203",
        "nf_id": "UPF-01",
        "version": "v1.0.0-anchor",
        "mean_volume_bytes": 1_000_000_000.0,
        "composition_vector": {
            "registration_ratio": 0.08,
            "session_setup_ratio": 0.90,
            "failure_ratio": 0.005,
            "other_signalling_ratio": 0.015,
        },
        "scaler_params": {
            "medians": {
                "pdu_session_rate_per_ue": 1.0,
                "ue_hash_entropy": 7.4,
                "nas_failure_ratio": 0.004,
                "pfcp_failure_ratio": 0.0,
            }
        },
    }


def test_pure_proportional_growth_gives_likely_benign(baseline_bundle):
    """Verify pure proportional volume growth with consistent composition attributes as likely_benign."""
    attributor = RuleBasedAttributor()

    # Window with 2.5x volume scaling, identical composition, stable per-UE rate, clean indicators
    window = {
        "window_id": "test-win-prop-growth",
        "slice_id": "sst-1-sd-010203",
        "raw_counters": {
            "total_bytes_uplink": 500_000_000,
            "total_bytes_downlink": 2_000_000_000,  # 2.5 GB total -> k = 2.5
            "active_ue_count": 2500,
        },
        "ratio_features": {
            "pdu_session_rate_per_ue": 1.0,
            "ue_hash_entropy": 7.42,
            "nas_failure_ratio": 0.003,
            "pfcp_failure_ratio": 0.0,
            "new_ue_rate": 0.02,
        },
        "composition_vector": {
            "registration_ratio": 0.08,
            "session_setup_ratio": 0.90,
            "failure_ratio": 0.005,
            "other_signalling_ratio": 0.015,
        },
    }

    recent_windows = [window] * 5
    res = attributor.attribute(
        window=window,
        baseline_bundle=baseline_bundle,
        recent_windows=recent_windows,
        drift_detected=True,
    )

    assert res["verdict"] == AttributionVerdict.LIKELY_BENIGN.value
    assert res["abstain_reason"] is None
    assert res["action"] == RecommendedAction.ADAPT_CANDIDATE.value
    assert res["proportional_growth_test"]["passed"] is True
    assert res["confidence_type"] == "evidence_category"


def test_composition_shift_gives_likely_attack(baseline_bundle):
    """Verify shifted composition accompanied by threat indicators attributes as likely_attack."""
    attributor = RuleBasedAttributor()

    # Window with shifted composition and elevated NAS failures
    window = {
        "window_id": "test-win-attack",
        "slice_id": "sst-1-sd-010203",
        "raw_counters": {
            "total_bytes_uplink": 300_000_000,
            "total_bytes_downlink": 900_000_000,
            "active_ue_count": 1400,
        },
        "ratio_features": {
            "pdu_session_rate_per_ue": 2.2,  # per-UE rate jumped!
            "ue_hash_entropy": 5.1,          # entropy dropped!
            "nas_failure_ratio": 0.085,      # elevated signalling failure!
            "pfcp_failure_ratio": 0.02,
            "new_ue_rate": 0.08,
        },
        "composition_vector": {
            "registration_ratio": 0.45,       # severely shifted mix
            "session_setup_ratio": 0.35,
            "failure_ratio": 0.15,
            "other_signalling_ratio": 0.05,
        },
    }

    recent_windows = [window] * 5
    res = attributor.attribute(
        window=window,
        baseline_bundle=baseline_bundle,
        recent_windows=recent_windows,
        drift_detected=True,
        detector_output={"fusion": {"agreement_state": "BOTH_FIRE"}},
    )

    assert res["verdict"] == AttributionVerdict.LIKELY_ATTACK.value
    assert res["abstain_reason"] is None
    assert res["action"] == RecommendedAction.ALERT.value
    assert res["proportional_growth_test"]["passed"] is False


def test_conflicting_signals_give_uncertain_with_named_reason(baseline_bundle):
    """Verify conflicting signals trigger principled abstention with a specific named reason."""
    attributor = RuleBasedAttributor()

    # Volume up (k=1.8), but composition shifted, yet no strong threat indicators
    window = {
        "window_id": "test-win-conflict",
        "slice_id": "sst-1-sd-010203",
        "raw_counters": {
            "total_bytes_uplink": 400_000_000,
            "total_bytes_downlink": 1_400_000_000,  # k = 1.8
            "active_ue_count": 1800,
        },
        "ratio_features": {
            "pdu_session_rate_per_ue": 1.0,
            "ue_hash_entropy": 7.4,
            "nas_failure_ratio": 0.002,             # nominal
            "pfcp_failure_ratio": 0.0,
            "new_ue_rate": 0.01,
        },
        "composition_vector": {
            "registration_ratio": 0.35,             # shifted composition without threat
            "session_setup_ratio": 0.60,
            "failure_ratio": 0.002,
            "other_signalling_ratio": 0.048,
        },
    }

    recent_windows = [window] * 5
    res = attributor.attribute(
        window=window,
        baseline_bundle=baseline_bundle,
        recent_windows=recent_windows,
        drift_detected=True,
    )

    assert res["verdict"] == AttributionVerdict.UNCERTAIN.value
    assert res["abstain_reason"] in [r.value for r in AbstainReason]
    assert res["abstain_reason"] == AbstainReason.VOLUME_COMPOSITION_DISAGREE.value
    assert res["action"] == RecommendedAction.QUARANTINE.value


def test_uncertain_window_lands_in_quarantine_and_decision_trace():
    """Verify that an uncertain window persists into quarantine_windows and decision_traces."""
    db = SessionLocal()
    window_id = f"test-quarantine-win-{int(datetime.now(timezone.utc).timestamp())}"
    try:
        # Insert a canonical window record
        db_win = CanonicalWindow(
            id=window_id,
            slice_id="sst-1-sd-010203",
            nf_id="UPF-01",
            window_start=datetime.now(timezone.utc),
            window_end=datetime.now(timezone.utc),
            duration_sec=60,
            raw_counters={"total_bytes_uplink": 400_000_000, "total_bytes_downlink": 1_400_000_000},
            ratio_features={"pdu_session_rate_per_ue": 1.0, "nas_failure_ratio": 0.002},
            composition_vector={"registration_ratio": 0.35, "session_setup_ratio": 0.60, "failure_ratio": 0.05},
        )
        db.add(db_win)
        db.commit()

        win_dict = {
            "window_id": window_id,
            "slice_id": "sst-1-sd-010203",
            "nf_id": "UPF-01",
            "raw_counters": db_win.raw_counters,
            "ratio_features": db_win.ratio_features,
            "composition_vector": db_win.composition_vector,
        }

        # Analyze window with force_drift to evaluate attribution
        res = attribution_service.analyze_window(
            window=win_dict,
            db=db,
            scenario="test_scenario",
            force_drift=True,
        )

        assert res.verdict == "uncertain"
        assert res.abstain_reason is not None

        # Verify entry in quarantine_windows table
        q_row = db.query(QuarantineWindow).filter(QuarantineWindow.window_id == window_id).first()
        assert q_row is not None
        assert q_row.reason == res.abstain_reason
        assert q_row.scenario == "test_scenario"

        # Verify decision_trace table entry
        trace_row = db.query(DecisionTrace).filter(DecisionTrace.window_id == window_id).first()
        assert trace_row is not None
        assert trace_row.verdict == "uncertain"
        assert trace_row.action == "quarantine"
        assert len(trace_row.steps) >= 6

        # Step names in decision trace
        step_names = [s["step_name"] for s in trace_row.steps]
        assert "window_received" in step_names
        assert "features_computed" in step_names
        assert "drift_detected" in step_names
        assert "evidence_evaluated" in step_names
        assert "attribution_verdict" in step_names
        assert "action_recommended" in step_names

        # Verify API endpoint functions
        from backend.app.api.attribution import get_decision_trace, list_drift_events
        trace_resp = get_decision_trace(trace_id=trace_row.id, db=db)
        assert trace_resp.id == trace_row.id
        assert trace_resp.window_id == window_id
        assert len(trace_resp.steps) == len(trace_row.steps)

        drift_resp = list_drift_events(db=db)
        assert isinstance(drift_resp, list)
        assert len(drift_resp) > 0
    finally:
        db.close()
# CommShield AI Core
