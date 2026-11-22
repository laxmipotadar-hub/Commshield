"""Unit tests for CommShield Governance Engine:
1. Quarantined windows never reach training (enforced via strict assertion).
2. The active baseline file is unchanged after candidate creation.
3. Approval is refused while a mandatory check fails (HTTP 409 Conflict).
4. Promotion and rollback leave exactly one active baseline.
5. The trusted anchor survives a rollback.
6. The poisoned candidate fails governance evaluation.
"""

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import pytest
from fastapi import HTTPException

from backend.app.database import SessionLocal
from backend.app.models import ApprovalLog, Baseline, BaselineRegistry, CandidateBaseline, QuarantineWindow
from backend.app.services.detection import detection_service
from backend.app.services.governance import governance_service
from ml_engine.governance import (
    build_default_governance_pipeline,
    build_shadow_candidate,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
SYNTHETIC_DIR = PROJECT_ROOT / "data" / "synthetic"
PROCESSED_BASELINES_DIR = PROJECT_ROOT / "data" / "processed" / "baselines"


@pytest.fixture
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def embb_baseline_bundles(db_session):
    slice_id = "sst-1-sd-010203"
    act_bundle = detection_service.get_baseline_bundle(slice_id, db=db_session)
    anc_row = db_session.query(Baseline).filter(Baseline.slice_id == slice_id, Baseline.is_anchor == True).first()
    anc_bundle = act_bundle
    if anc_row and anc_row.model_artifact_path and Path(anc_row.model_artifact_path).is_file():
        import joblib
        anc_bundle = joblib.load(anc_row.model_artifact_path)
    return act_bundle, anc_bundle


def test_quarantined_windows_never_reach_training(db_session, embb_baseline_bundles):
    """Verify that quarantined or uncertain windows are strictly forbidden from candidate training."""
    act_bundle, anc_bundle = embb_baseline_bundles
    slice_id = "sst-1-sd-010203"

    quarantined_win = {
        "window_id": "test-quarantine-blocked-001",
        "slice_id": slice_id,
        "raw_counters": {"total_bytes_uplink": 100_000, "total_bytes_downlink": 500_000},
        "ratio_features": {"pdu_session_rate_per_ue": 1.0},
        "composition_vector": {"registration_ratio": 0.08, "session_setup_ratio": 0.90, "failure_ratio": 0.02},
        "attribution": {"verdict": "uncertain", "abstain_reason": "volume_composition_disagree"},
    }

    # 1. Blocked via quarantined_window_ids set
    with pytest.raises(AssertionError, match="Quarantined window"):
        build_shadow_candidate(
            slice_id=slice_id,
            active_bundle=act_bundle,
            anchor_bundle=anc_bundle,
            adaptation_windows=[quarantined_win],
            quarantined_window_ids={"test-quarantine-blocked-001"},
            db=db_session,
        )

    # 2. Blocked via uncertain verdict in attribution
    with pytest.raises(AssertionError, match="SECURITY VIOLATION"):
        build_shadow_candidate(
            slice_id=slice_id,
            active_bundle=act_bundle,
            anchor_bundle=anc_bundle,
            adaptation_windows=[quarantined_win],
            db=db_session,
        )

    # 3. Blocked via ground truth attack label
    attack_win = deepcopy(quarantined_win)
    attack_win["window_id"] = "test-attack-blocked-002"
    attack_win["attribution"] = {"verdict": "likely_benign"}
    attack_win["ground_truth"] = {"is_attack": True, "attack_type": "slow_attack_ramp"}

    with pytest.raises(AssertionError, match="Ground truth attack window"):
        build_shadow_candidate(
            slice_id=slice_id,
            active_bundle=act_bundle,
            anchor_bundle=anc_bundle,
            adaptation_windows=[attack_win],
            db=db_session,
        )


def test_active_baseline_file_unchanged_after_candidate_creation(db_session, embb_baseline_bundles):
    """Verify that creating a shadow candidate never modifies the active baseline artifact."""
    act_bundle, anc_bundle = embb_baseline_bundles
    slice_id = "sst-1-sd-010203"

    act_row = db_session.query(Baseline).filter(Baseline.slice_id == slice_id, Baseline.is_active == True).first()
    assert act_row is not None
    active_path = Path(act_row.model_artifact_path)
    assert active_path.is_file()

    # Hash active baseline file before
    with open(active_path, "rb") as f:
        hash_before = hashlib.sha256(f.read()).hexdigest()

    legit_win = {
        "window_id": "test-legit-adaptation-001",
        "slice_id": slice_id,
        "raw_counters": {"total_bytes_uplink": 200_000_000, "total_bytes_downlink": 1_200_000_000},
        "ratio_features": {
            "registrations_per_active_ue": 0.025,
            "nas_failure_ratio": 0.002,
            "pfcp_failure_ratio": 0.0,
            "pdu_session_rate_per_ue": 1.0,
            "bytes_per_session": 750000.0,
            "packets_per_session": 550.0,
            "gtpu_volume_per_ue": 750000.0,
            "ue_hash_entropy": 7.4,
            "new_ue_rate": 0.015,
        },
        "composition_vector": {
            "registration_ratio": 0.0778,
            "session_setup_ratio": 0.9122,
            "failure_ratio": 0.0044,
            "other_signalling_ratio": 0.0056,
        },
        "attribution": {"verdict": "likely_benign"},
    }

    # Build shadow candidate
    cand_bundle, cand_row = build_shadow_candidate(
        slice_id=slice_id,
        active_bundle=act_bundle,
        anchor_bundle=anc_bundle,
        adaptation_windows=[legit_win],
        db=db_session,
    )

    # Candidate artifact is saved separately
    cand_path = Path(cand_row.model_artifact_path)
    assert cand_path.is_file()
    assert cand_path != active_path

    # Active baseline file must be bitwise identical
    with open(active_path, "rb") as f:
        hash_after = hashlib.sha256(f.read()).hexdigest()

    assert hash_before == hash_after, "Active baseline file was modified during candidate creation!"


def test_approval_refused_while_mandatory_check_fails(db_session):
    """Verify that candidate promotion is refused with HTTP 409 Conflict if mandatory checks fail."""
    slice_id = "sst-1-sd-010203"
    act_row = db_session.query(Baseline).filter(Baseline.slice_id == slice_id, Baseline.is_active == True).first()
    anc_row = db_session.query(Baseline).filter(Baseline.slice_id == slice_id, Baseline.is_anchor == True).first()

    # Create candidate with failed gate_metrics
    failed_cand = CandidateBaseline(
        slice_id=slice_id,
        candidate_version="v1.1.0-failed-gates",
        active_baseline_id=act_row.id,
        anchor_baseline_id=anc_row.id,
        status="PENDING",
        gate_metrics={
            "all_mandatory_passed": False,
            "canary_retention_test": {"passed": False, "mandatory": True},
            "drift_budget": {"passed": False, "mandatory": True},
        },
        decision_trace=["Gate checks failed"],
        model_artifact_path=act_row.model_artifact_path,
    )
    db_session.add(failed_cand)
    db_session.commit()
    db_session.refresh(failed_cand)

    # Attempt to approve
    with pytest.raises(HTTPException) as exc_info:
        governance_service.approve_and_promote(
            candidate_id=failed_cand.id,
            analyst_id="analyst_test",
            notes="Attempting approval despite failed checks",
            db=db_session,
        )

    assert exc_info.value.status_code == 409
    assert "Mandatory governance checks failed" in exc_info.value.detail


def test_promotion_and_rollback_leave_exactly_one_active_baseline(db_session, embb_baseline_bundles):
    """Verify that promotion and rollback atomically maintain exactly one active baseline."""
    act_bundle, anc_bundle = embb_baseline_bundles
    slice_id = "sst-1-sd-010203"

    # Verify initial state: exactly one active baseline
    initial_active_count = db_session.query(Baseline).filter(
        Baseline.slice_id == slice_id, Baseline.is_active == True
    ).count()
    assert initial_active_count == 1

    initial_active = db_session.query(Baseline).filter(
        Baseline.slice_id == slice_id, Baseline.is_active == True
    ).first()
    initial_version = initial_active.version

    # 1. Create a passing candidate
    legit_win = {
        "window_id": f"win-legit-{int(datetime.now(timezone.utc).timestamp())}",
        "slice_id": slice_id,
        "raw_counters": {"total_bytes_uplink": 200_000_000, "total_bytes_downlink": 1_200_000_000},
        "ratio_features": {f: 0.0 for f in ["registrations_per_active_ue", "nas_failure_ratio", "pfcp_failure_ratio", "pdu_session_rate_per_ue", "bytes_per_session", "packets_per_session", "gtpu_volume_per_ue", "ue_hash_entropy", "new_ue_rate"]},
        "composition_vector": {"registration_ratio": 0.0778, "session_setup_ratio": 0.9122, "failure_ratio": 0.0044, "other_signalling_ratio": 0.0056},
        "attribution": {"verdict": "likely_benign"},
    }
    cand_bundle, cand_row = build_shadow_candidate(
        slice_id=slice_id,
        active_bundle=act_bundle,
        anchor_bundle=anc_bundle,
        adaptation_windows=[legit_win],
        db=db_session,
    )
    # Set gate metrics to passed
    cand_row.gate_metrics = {"all_mandatory_passed": True, "overall_passed": True}
    db_session.commit()

    # 2. Promote candidate (clear previous approval log to test promotion in isolation)
    db_session.query(ApprovalLog).filter(ApprovalLog.slice_id == slice_id).delete()
    db_session.commit()
    governance_service.approve_and_promote(
        candidate_id=cand_row.id,
        analyst_id="analyst_verifier",
        notes="Promoting verified test candidate",
        db=db_session,
    )

    # Exactly one active baseline after promotion
    post_promote_active = db_session.query(Baseline).filter(
        Baseline.slice_id == slice_id, Baseline.is_active == True
    ).all()
    assert len(post_promote_active) == 1
    assert post_promote_active[0].version == cand_row.candidate_version

    # 3. Rollback to original baseline
    governance_service.rollback_baseline(
        slice_id=slice_id,
        target_version=initial_version,
        analyst_id="analyst_verifier",
        reason="Test rollback verification",
        db=db_session,
    )

    # Exactly one active baseline after rollback
    post_rollback_active = db_session.query(Baseline).filter(
        Baseline.slice_id == slice_id, Baseline.is_active == True
    ).all()
    assert len(post_rollback_active) == 1
    assert post_rollback_active[0].version == initial_version


def test_anchor_survives_rollback(db_session):
    """Verify that the immutable trusted anchor baseline is preserved through promotion and rollback."""
    slice_id = "sst-1-sd-010203"

    anchor = db_session.query(Baseline).filter(
        Baseline.slice_id == slice_id, Baseline.is_anchor == True
    ).first()
    assert anchor is not None
    anchor_id = anchor.id
    anchor_version = anchor.version

    # Trigger rollback targeting anchor
    res = governance_service.rollback_baseline(
        slice_id=slice_id,
        target_version=anchor_version,
        analyst_id="analyst_anchor_test",
        reason="Testing anchor survival",
        db=db_session,
    )
    assert res.status == "COMPLETED"

    # Query anchor again
    reloaded_anchor = db_session.query(Baseline).filter(Baseline.id == anchor_id).first()
    assert reloaded_anchor is not None
    assert reloaded_anchor.is_anchor is True
    assert reloaded_anchor.is_active is True
    assert reloaded_anchor.version == anchor_version


def test_poisoned_candidate_fails_governance(db_session, embb_baseline_bundles):
    """Verify that a poisoned candidate (trained on attack traffic) is rejected by canary/drift budget."""
    act_bundle, anc_bundle = embb_baseline_bundles
    slice_id = "sst-1-sd-010203"

    # Create severely shifted / poisoned adaptation windows simulating attack contamination
    poisoned_windows = [
        {
            "window_id": f"poison-win-{i}",
            "slice_id": slice_id,
            "raw_counters": {
                "total_bytes_uplink": 900_000_000,
                "total_bytes_downlink": 4_500_000_000,
                "active_ue_count": 500,
            },
            "ratio_features": {
                "registrations_per_active_ue": 0.55,       # severely shifted
                "nas_failure_ratio": 0.25,                 # massive signalling failure
                "pfcp_failure_ratio": 0.15,
                "pdu_session_rate_per_ue": 4.5,            # rate jumped
                "bytes_per_session": 15000000.0,
                "packets_per_session": 9500.0,
                "gtpu_volume_per_ue": 15000000.0,
                "ue_hash_entropy": 2.5,                    # collapsed entropy
                "new_ue_rate": 0.35,
            },
            "composition_vector": {
                "registration_ratio": 0.50,                # abnormal composition
                "session_setup_ratio": 0.20,
                "failure_ratio": 0.25,
                "other_signalling_ratio": 0.05,
            },
            "attribution": {"verdict": "likely_benign"},   # masquerading
        }
        for i in range(10)
    ]

    cand_bundle, cand_row = build_shadow_candidate(
        slice_id=slice_id,
        active_bundle=act_bundle,
        anchor_bundle=anc_bundle,
        adaptation_windows=poisoned_windows,
        candidate_version=f"v1.1.0-poisoned-{int(datetime.now(timezone.utc).timestamp())}",
        db=db_session,
    )

    # Evaluate candidate through governance pipeline
    pipeline = build_default_governance_pipeline()
    eval_result = pipeline.evaluate(
        candidate_bundle=cand_bundle,
        active_bundle=act_bundle,
        anchor_bundle=anc_bundle,
        context={
            "db": db_session,
            "adaptation_windows": poisoned_windows,
            "volume_multiplier": 3.0,
        },
    )

    # Assert poisoned candidate fails governance
    assert eval_result.overall_passed is False, "Expected poisoned candidate to fail governance checks"
    assert eval_result.all_mandatory_passed is False, "Expected mandatory checks to fail on poisoned candidate"

    # Specifically check that drift budget or proportional growth failed
    drift_budget_res = next(r for r in eval_result.check_results if r.name == "drift_budget")
    prop_growth_res = next(r for r in eval_result.check_results if r.name == "proportional_growth")
    assert (not drift_budget_res.passed) or (not prop_growth_res.passed), "Expected drift budget or proportional growth to reject poisoned candidate"
# CommShield AI Core
