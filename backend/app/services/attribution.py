"""Attribution service managing drift detection (ADWIN), rule attribution, decision traces, and quarantine."""

from datetime import datetime, timezone
import json
import logging
from typing import Any, Dict, List, Optional
import uuid

from sqlalchemy.orm import Session

from ..database import SessionLocal
from ..models import (
    AnomalyAlert,
    AttributionResult,
    CanonicalWindow,
    DecisionTrace,
    DriftEvent,
    QuarantineWindow,
)
from ..schemas import AttributionOutput, ProportionalGrowthTest
from .detection import detection_service
from ml_engine.attribution import (
    AdwinSliceTracker,
    AttributionEngine,
    RuleBasedAttributor,
)

logger = logging.getLogger("commshield.attribution")


class AttributionService:
    """Manages drift detection and evidence-based attribution workflows."""

    def __init__(self):
        self.adwin_tracker = AdwinSliceTracker()
        self.engine = AttributionEngine(default_attributor=RuleBasedAttributor())
        self.recent_windows_by_slice: Dict[str, List[Dict[str, Any]]] = {}

    def reset_trackers(self) -> None:
        """Reset internal ADWIN windows and history caches."""
        self.adwin_tracker.reset()
        self.recent_windows_by_slice.clear()

    def analyze_window(
        self,
        window: Dict[str, Any],
        db: Optional[Session] = None,
        scenario: Optional[str] = None,
        force_drift: bool = False,
    ) -> AttributionOutput:
        """Analyze a canonical window for distribution drift and perform attribution."""
        owns_db = False
        if db is None:
            db = SessionLocal()
            owns_db = True

        window_id = window.get("window_id") or str(uuid.uuid4())
        slice_id = window.get("slice_id", "sst-1-sd-010203")
        raw_counters = window.get("raw_counters", {})
        ratio_features = window.get("ratio_features", {})

        try:
            # 1. Retrieve baseline bundle
            bundle = detection_service.get_baseline_bundle(slice_id, db=db) or {}

            # 2. Maintain recent window history per slice
            if slice_id not in self.recent_windows_by_slice:
                self.recent_windows_by_slice[slice_id] = []
            self.recent_windows_by_slice[slice_id].append(window)
            if len(self.recent_windows_by_slice[slice_id]) > 50:
                self.recent_windows_by_slice[slice_id].pop(0)

            recent_history = self.recent_windows_by_slice[slice_id]

            # 3. ADWIN Drift Detection on total traffic volume
            total_bytes = float(
                raw_counters.get("total_bytes_uplink", 0) + raw_counters.get("total_bytes_downlink", 0)
            )
            drift_detected, _ = self.adwin_tracker.update(slice_id, total_bytes, window_id)
            if force_drift:
                drift_detected = True

            # 4. Fetch latest detector output for this window
            detector_output = None
            alert_row = db.query(AnomalyAlert).filter(AnomalyAlert.window_id == window_id).first()
            if alert_row:
                detector_output = alert_row.detector_output

            # 5. Execute Attribution
            attribution_dict = self.engine.attribute(
                window=window,
                baseline_bundle=bundle,
                recent_windows=recent_history,
                drift_detected=drift_detected,
                detector_output=detector_output,
            )

            verdict = attribution_dict["verdict"]
            abstain_reason = attribution_dict.get("abstain_reason")
            action = attribution_dict.get("action", "quarantine")
            action_desc = attribution_dict.get("action_recommendation", "")
            prop_test_data = attribution_dict["proportional_growth_test"]

            # 6. Generate Structured Decision Trace Steps
            now_dt = datetime.now(timezone.utc)
            trace_id = str(uuid.uuid4())
            attr_result_id = str(uuid.uuid4())
            drift_event_id = str(uuid.uuid4()) if drift_detected else None

            steps = [
                {
                    "step_name": "window_received",
                    "description": f"Telemetry window {window_id[:8]}... received for slice {slice_id}",
                    "timestamp": now_dt.isoformat(),
                    "details": {
                        "window_id": window_id,
                        "slice_id": slice_id,
                        "duration_sec": window.get("duration_sec", 60),
                    },
                },
                {
                    "step_name": "features_computed",
                    "description": "Computed canonical ratios, scaling factor, and category compositions",
                    "timestamp": now_dt.isoformat(),
                    "details": {
                        "total_bytes": total_bytes,
                        "active_ue_count": raw_counters.get("active_ue_count", 0),
                        "composition": window.get("composition_vector", {}),
                    },
                },
                {
                    "step_name": "detectors_scored",
                    "description": "Scored Isolation Forest, Dense Autoencoder, and CUSUM tracking",
                    "timestamp": now_dt.isoformat(),
                    "details": detector_output or {"status": "Nominal or evaluated prior to drift"},
                },
                {
                    "step_name": "drift_detected",
                    "description": f"ADWIN statistical drift evaluation: {'DRIFT DETECTED' if drift_detected else 'STABLE'}",
                    "timestamp": now_dt.isoformat(),
                    "details": {
                        "adwin_status": "drift_detected" if drift_detected else "stable",
                        "volume_multiplier_k": prop_test_data.get("scaling_factor_k", 1.0),
                    },
                },
                {
                    "step_name": "evidence_evaluated",
                    "description": "Evaluated Jensen-Shannon divergence, per-UE rates, and threat indicators",
                    "timestamp": now_dt.isoformat(),
                    "details": {
                        "jsd_divergence": prop_test_data.get("jsd_divergence", 0.0),
                        "jsd_threshold": prop_test_data.get("jsd_null_threshold_99th", 0.035),
                        "proportional_passed": prop_test_data.get("passed", False),
                        "supporting_signals": attribution_dict.get("supporting_signals", {}),
                    },
                },
                {
                    "step_name": "attribution_verdict",
                    "description": f"Assigned evidence-based classification: {verdict.upper()}",
                    "timestamp": now_dt.isoformat(),
                    "details": {
                        "verdict": verdict,
                        "abstain_reason": abstain_reason,
                        "confidence_type": "evidence_category",
                    },
                },
                {
                    "step_name": "action_recommended",
                    "description": f"Selected operational action: {action.upper()}",
                    "timestamp": now_dt.isoformat(),
                    "details": {
                        "action": action,
                        "recommendation": action_desc,
                    },
                },
            ]

            # 7. Persist Decision Trace
            db_trace = DecisionTrace(
                id=trace_id,
                window_id=window_id,
                slice_id=slice_id,
                alert_id=alert_row.id if alert_row else None,
                drift_event_id=drift_event_id,
                steps=steps,
                verdict=verdict,
                action=action,
                created_at=now_dt,
            )
            db.add(db_trace)

            # 8. Persist AttributionResult if canonical window exists
            win_exists = db.query(CanonicalWindow).filter(CanonicalWindow.id == window_id).first()
            if win_exists:
                db_attr = AttributionResult(
                    id=attr_result_id,
                    window_id=window_id,
                    slice_id=slice_id,
                    drift_detected=drift_detected,
                    verdict=verdict,
                    abstain_reason=abstain_reason,
                    jsd_divergence=prop_test_data.get("jsd_divergence", 0.0),
                    scaling_factor_k=prop_test_data.get("scaling_factor_k", 1.0),
                    evidence_signals=attribution_dict.get("supporting_signals", {}),
                    created_at=now_dt,
                )
                db.add(db_attr)

            # 9. If drift was detected, persist DriftEvent
            if drift_detected and drift_event_id:
                db_drift = DriftEvent(
                    id=drift_event_id,
                    window_id=window_id,
                    slice_id=slice_id,
                    event_time=now_dt,
                    volume_multiplier=prop_test_data.get("scaling_factor_k", 1.0),
                    drift_detected=True,
                    attribution_id=attr_result_id,
                    decision_trace_id=trace_id,
                    attribution={
                        "verdict": verdict,
                        "abstain_reason": abstain_reason,
                        "action": action,
                        "action_recommendation": action_desc,
                        "proportional_growth_test": prop_test_data,
                        "supporting_signals": attribution_dict.get("supporting_signals", {}),
                    },
                    created_at=now_dt,
                )
                db.add(db_drift)

            # 10. If uncertain, write to QuarantineWindow
            if verdict == "uncertain":
                db_quarantine = QuarantineWindow(
                    id=str(uuid.uuid4()),
                    window_id=window_id,
                    slice_id=slice_id,
                    reason=abstain_reason or "uncertain_attribution",
                    scenario=scenario,
                    quarantined_at=now_dt,
                )
                db.add(db_quarantine)

            db.commit()

            return AttributionOutput(
                window_id=window_id,
                slice_id=slice_id,
                drift_detected=drift_detected,
                verdict=verdict,
                abstain_reason=abstain_reason,
                confidence_type="evidence_category",
                proportional_growth_test=ProportionalGrowthTest(**prop_test_data),
                supporting_signals=attribution_dict.get("supporting_signals", {}),
                action=action,
                action_recommendation=action_desc,
                decision_trace_id=trace_id,
            )
        except Exception as e:
            db.rollback()
            logger.error("Error performing attribution on window %s: %s", window_id, e)
            raise
        finally:
            if owns_db:
                db.close()


attribution_service = AttributionService()
