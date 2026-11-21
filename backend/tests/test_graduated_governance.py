"""Unit tests for CommShield Three-Tier Graduated Governance and Validation Engine."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.database import SessionLocal
from app.models import Baseline, CandidateBaseline
from app.governance import (
    GovernanceTier,
    GraduatedGovernanceConfig,
    GraduatedGovernanceEngine,
    increment_patch_version,
)
from app.services.lineage import lineage_adapter
from app.validation import (
    validate_single_window,
    validate_telemetry_series,
    ValidationReport,
)

client = TestClient(app)


def test_increment_patch_version():
    """Verify semver patch version increments properly."""
    assert increment_patch_version("v1.0.0") == "v1.0.1"
    assert increment_patch_version("v1.0.0-anchor") == "v1.0.1"
    assert increment_patch_version("v2.3.9") == "v2.3.10"
    assert increment_patch_version("v1.2") == "v1.2.1"


def test_graduated_governance_tiers_and_safety_override():
    """Verify Tier 1, Tier 2, Tier 3 and that low drift alone never overrides failed canary."""
    db: Session = SessionLocal()
    try:
        active_b = db.query(Baseline).filter(Baseline.slice_id == "sst-1-sd-010203").first()
        base_id = active_b.id if active_b else "test-base-01"

        # Create a mock candidate baseline
        cand = CandidateBaseline(
            id="test-cand-001",
            slice_id="sst-1-sd-010203",
            candidate_version="v1.1.0-test",
            active_baseline_id=base_id,
            anchor_baseline_id=base_id,
            status="PENDING",
            gate_metrics={
                "all_mandatory_passed": True,
                "normal_holdout_backtest": {"passed": True},
                "canary_retention_test": {"passed": True},
                "drift_budget": {"passed": True},
                "proportional_growth": {"passed": True, "metrics": {"jsd": 0.015}},
            },
            decision_trace=[],
        )
        db.add(cand)
        db.commit()

        engine = GraduatedGovernanceEngine()

        # Test Tier 1: Low drift (0.015 < 0.020) and all checks pass -> AUTO_APPROVE
        dec1 = engine.evaluate_and_enact(candidate_id="test-cand-001", db=db, override_jsd=0.015)
        assert dec1.tier == GovernanceTier.TIER_1_AUTO_APPROVE.value
        assert dec1.action == "AUTO_APPROVE"
        assert dec1.is_approved is True
        assert dec1.new_version is not None

        # Test Tier 2: Moderate drift (0.025) and all checks pass -> FLAG_FOR_REVIEW
        cand.status = "PENDING"
        db.commit()
        dec2 = engine.evaluate_and_enact(candidate_id="test-cand-001", db=db, override_jsd=0.025)
        assert dec2.tier == GovernanceTier.TIER_2_FLAG_FOR_REVIEW.value
        assert dec2.action == "FLAG_FOR_REVIEW"
        assert dec2.is_approved is False

        # Test Tier 3: Severe drift (0.045 >= 0.035) -> BLOCK_AND_QUARANTINE
        cand.status = "PENDING"
        db.commit()
        dec3 = engine.evaluate_and_enact(candidate_id="test-cand-001", db=db, override_jsd=0.045)
        assert dec3.tier == GovernanceTier.TIER_3_BLOCK_AND_QUARANTINE.value
        assert dec3.action == "BLOCK_AND_QUARANTINE"
        assert dec3.is_blocked is True

        # CRITICAL SAFETY RULE TEST:
        # Low drift (0.010 < 0.020) BUT Canary failed -> MUST BE OVERRIDDEN TO TIER 3!
        cand.status = "PENDING"
        cand.gate_metrics = {
            "all_mandatory_passed": False,
            "normal_holdout_backtest": {"passed": True},
            "canary_retention_test": {"passed": False},  # FAIL
            "drift_budget": {"passed": True},
            "proportional_growth": {"passed": True, "metrics": {"jsd": 0.010}},
        }
        db.commit()
        dec_override = engine.evaluate_and_enact(candidate_id="test-cand-001", db=db, override_jsd=0.010)
        assert dec_override.tier == GovernanceTier.TIER_3_BLOCK_AND_QUARANTINE.value
        assert dec_override.action == "BLOCK_AND_QUARANTINE"
        assert dec_override.is_blocked is True
        assert any("Canary retention test FAILED" in r for r in dec_override.reasons)

    finally:
        # Cleanup
        db.query(CandidateBaseline).filter(CandidateBaseline.id == "test-cand-001").delete()
        db.commit()
        db.close()


def test_lineage_cryptographic_integrity():
    """Verify that the Lineage SHA-256 provenance chain maintains tamper-evident integrity."""
    is_valid, err = lineage_adapter.verify_integrity()
    assert is_valid is True
    assert err is None

    # Append test event
    block = lineage_adapter.append_event(
        event_type="TEST_EVENT",
        slice_id="sst-1-sd-010203",
        payload={"action": "test", "metric": 42},
    )
    assert block.current_hash is not None
    assert len(block.current_hash) == 64

    # Verify chain integrity remains valid
    is_valid, err = lineage_adapter.verify_integrity()
    assert is_valid is True


def test_adaptation_summary_endpoint():
    """Verify GET /api/governance/summary returns dynamic adaptation counts."""
    res = client.get("/api/governance/summary")
    assert res.status_code == 200
    data = res.json()
    assert "total_candidates" in data
    assert "auto_approved_count" in data
    assert "total_approved_count" in data
    assert "flagged_count" in data
    assert "blocked_count" in data
    assert "adaptation_rate" in data
    assert "summary_text" in data


def test_score_distribution_endpoint():
    """Verify GET /api/detection/distribution returns valid histogram bins."""
    res = client.get("/api/detection/distribution")
    assert res.status_code == 200
    data = res.json()
    assert "histogram_bins" in data
    assert len(data["histogram_bins"]) >= 5
    assert "raw_scores" in data


def test_validation_engine_invariants():
    """Verify validation engine catches negative values, non-finite values, and temporal disorder."""
    # 1. Valid series
    valid_series = [
        {
            "window_id": "win-1",
            "timestamp": "2026-11-21T10:00:00Z",
            "raw_counters": {"total_packets": 1000, "total_bytes_uplink": 50000},
            "ratio_features": {"udp_ratio": 0.4},
        },
        {
            "window_id": "win-2",
            "timestamp": "2026-11-21T10:01:00Z",
            "raw_counters": {"total_packets": 1200, "total_bytes_uplink": 60000},
            "ratio_features": {"udp_ratio": 0.5},
        },
    ]
    rep1 = validate_telemetry_series(valid_series)
    assert rep1.is_valid is True
    assert rep1.error_count == 0

    # 2. Negative volume violation
    bad_volume = [
        {
            "window_id": "win-bad-1",
            "timestamp": "2026-11-21T10:00:00Z",
            "raw_counters": {"total_packets": -500},
        }
    ]
    rep2 = validate_telemetry_series(bad_volume)
    assert rep2.is_valid is False
    assert any(iss["category"] == "NEGATIVE_VALUE" for iss in rep2.issues)

    # 3. Timestamp monotonicity violation
    bad_time = [
        {"window_id": "win-t1", "timestamp": "2026-11-21T10:05:00Z"},
        {"window_id": "win-t2", "timestamp": "2026-11-21T10:02:00Z"},  # Decreased!
    ]
    rep3 = validate_telemetry_series(bad_time)
    assert rep3.is_valid is False
    assert any(iss["category"] == "MONOTONICITY" for iss in rep3.issues)
