"""System utility service for runtime state management, database resets, and demo isolation."""

import logging
from typing import Any, Dict
from sqlalchemy.orm import Session

from backend.app.models import (
    AnomalyAlert,
    ApprovalLog,
    AttributionResult,
    AuditEvent,
    Baseline,
    CanaryResult,
    CandidateBaseline,
    CanonicalWindow,
    DecisionTrace,
    DetectionResult,
    DriftBudget,
    DriftEvent,
    QuarantineWindow,
)
from backend.app.services.detection import detection_service
from backend.app.services.replay import replay_service

logger = logging.getLogger("commshield.system")


def reset_runtime_database(db: Session) -> Dict[str, Any]:
    """Clear runtime telemetry and evaluation data while strictly preserving trained anchor baselines."""
    # 1. Stop replay if running
    try:
        replay_service.stop()
        replay_service.current_window_index = 0
        replay_service.total_windows = 0
        replay_service._windows.clear()
        replay_service._legitimate_windows_by_slice.clear()
        replay_service._candidate_created_by_slice.clear()
    except Exception as e:
        logger.warning("Error stopping replay service: %s", e)

    # 2. Reset attribution trackers & detection caches
    try:
        from backend.app.services.attribution import attribution_service
        attribution_service.reset_trackers()
        detection_service.clear_cache()
    except Exception as e:
        logger.warning("Error resetting trackers/caches: %s", e)

    # 3. Clear all runtime evaluation and telemetry tables
    deleted_counts = {}
    try:
        # Delete dependent child tables first
        deleted_counts["quarantine_windows"] = db.query(QuarantineWindow).delete()
        deleted_counts["detection_results"] = db.query(DetectionResult).delete()
        deleted_counts["attribution_results"] = db.query(AttributionResult).delete()
        deleted_counts["anomaly_alerts"] = db.query(AnomalyAlert).delete()
        deleted_counts["drift_events"] = db.query(DriftEvent).delete()
        deleted_counts["decision_traces"] = db.query(DecisionTrace).delete()
        deleted_counts["canonical_windows"] = db.query(CanonicalWindow).delete()

        # Delete governance evaluation records
        deleted_counts["drift_budgets"] = db.query(DriftBudget).delete()
        deleted_counts["canary_results"] = db.query(CanaryResult).delete()
        deleted_counts["approval_logs"] = db.query(ApprovalLog).delete()
        deleted_counts["audit_events"] = db.query(AuditEvent).delete()
        deleted_counts["candidate_baselines"] = db.query(CandidateBaseline).delete()

        # Clean baselines: delete any non-anchor candidates, restore anchor baselines to active
        deleted_counts["promoted_baselines"] = (
            db.query(Baseline).filter(Baseline.is_anchor == False).delete()
        )
        db.query(Baseline).filter(Baseline.is_anchor == True).update({Baseline.is_active: True})

        db.commit()
    except Exception as e:
        db.rollback()
        logger.error("Failed to reset database: %s", e)
        raise e

    logger.info("Runtime database successfully cleared. Anchor baselines preserved: %s", deleted_counts)
    return {
        "status": "CLEARED",
        "message": "Runtime database tables reset successfully. Trained anchor baselines preserved.",
        "cleared_records": deleted_counts,
    }
# CommShield AI Core
