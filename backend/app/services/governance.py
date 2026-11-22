"""Governance service for CommShield.

Manages candidate evaluation pipelines, gate metric persistence,
analyst approval logging, atomic baseline promotion, and rollback transitions.
"""

from datetime import datetime, timezone
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
import uuid

import joblib
from fastapi import HTTPException
from sqlalchemy.orm import Session

from backend.app.database import SessionLocal
from backend.app.models import (
    ApprovalLog,
    AuditEvent,
    Baseline,
    BaselineRegistry,
    CanaryResult,
    CandidateBaseline,
    DecisionTrace,
    DriftBudget,
    QuarantineWindow,
)
from backend.app.schemas import (
    CandidateResponse,
    RollbackResponse,
)
from ml_engine.governance import (
    GovernanceEvaluationResult,
    GovernancePipeline,
    build_default_governance_pipeline,
    build_shadow_candidate,
)
from .detection import detection_service

logger = logging.getLogger("commshield.governance.service")

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
PROCESSED_BASELINES_DIR = PROJECT_ROOT / "data" / "processed" / "baselines"
CANDIDATES_DIR = PROJECT_ROOT / "data" / "processed" / "candidates"


class GovernanceService:
    """Coordinates shadow candidate lifecycle, gate checking, and atomic promotions."""

    def __init__(self, pipeline: Optional[GovernancePipeline] = None):
        self.pipeline: GovernancePipeline = pipeline or build_default_governance_pipeline()

    def create_candidate_for_slice(
        self,
        slice_id: str,
        adaptation_windows: List[Dict[str, Any]],
        quarantined_ids: Optional[Set[str]] = None,
        db: Optional[Session] = None,
        candidate_version: Optional[str] = None,
    ) -> Tuple[Dict[str, Any], CandidateBaseline]:
        """Build and persist an isolated shadow candidate baseline for a slice."""
        owns_db = False
        if db is None:
            db = SessionLocal()
            owns_db = True

        try:
            active_bundle = detection_service.get_baseline_bundle(slice_id, db=db)
            if not active_bundle:
                raise ValueError(f"No active baseline found for slice {slice_id}")

            anchor_row = (
                db.query(Baseline)
                .filter(Baseline.slice_id == slice_id, Baseline.is_anchor == True)
                .first()
            )
            anchor_bundle = active_bundle
            if anchor_row and anchor_row.model_artifact_path:
                anc_path = Path(anchor_row.model_artifact_path)
                if anc_path.is_file():
                    anchor_bundle = joblib.load(anc_path)

            cand_bundle, cand_row = build_shadow_candidate(
                slice_id=slice_id,
                active_bundle=active_bundle,
                anchor_bundle=anchor_bundle,
                adaptation_windows=adaptation_windows,
                quarantined_window_ids=quarantined_ids,
                candidate_version=candidate_version,
                db=db,
            )

            # Record candidate creation in decision_traces table
            trace_entry = DecisionTrace(
                window_id=f"candidate-create-{cand_row.id}",
                slice_id=slice_id,
                verdict="candidate_created",
                action="quarantine_checked",
                steps=[
                    {
                        "step_name": "candidate_creation",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "details": {
                            "candidate_id": cand_row.id,
                            "candidate_version": cand_row.candidate_version,
                            "parent_version": cand_row.parent_version,
                            "adaptation_windows_count": len(adaptation_windows),
                        },
                    }
                ],
            )
            db.add(trace_entry)
            db.commit()

            return cand_bundle, cand_row
        finally:
            if owns_db:
                db.close()

    def evaluate_candidate(
        self,
        candidate_id: str,
        db: Optional[Session] = None,
        volume_multiplier: float = 1.0,
        adaptation_windows: Optional[List[Dict[str, Any]]] = None,
        canary_windows: Optional[List[Dict[str, Any]]] = None,
        normal_holdout_windows: Optional[List[Dict[str, Any]]] = None,
    ) -> GovernanceEvaluationResult:
        """Run the governance pipeline against a candidate baseline and persist gate outcomes."""
        owns_db = False
        if db is None:
            db = SessionLocal()
            owns_db = True

        try:
            cand = db.query(CandidateBaseline).filter(CandidateBaseline.id == candidate_id).first()
            if not cand:
                raise HTTPException(status_code=404, detail=f"Candidate baseline {candidate_id} not found.")

            # Load candidate bundle artifact
            artifact_path = Path(cand.model_artifact_path) if cand.model_artifact_path else None
            if not artifact_path or not artifact_path.is_file():
                # Check candidate dir fallback
                candidate_files = list(CANDIDATES_DIR.glob(f"{cand.slice_id}_{cand.candidate_version}*.joblib"))
                if candidate_files:
                    artifact_path = candidate_files[0]
                else:
                    raise HTTPException(
                        status_code=404,
                        detail=f"Candidate model artifact for {cand.candidate_version} not found on disk.",
                    )

            cand_bundle = joblib.load(artifact_path)
            cand_bundle["candidate_id"] = cand.id
            cand_bundle["slice_id"] = cand.slice_id

            # Retrieve active and anchor bundles
            active_bundle = detection_service.get_baseline_bundle(cand.slice_id, db=db) or {}
            anchor_row = (
                db.query(Baseline)
                .filter(Baseline.slice_id == cand.slice_id, Baseline.is_anchor == True)
                .first()
            )
            anchor_bundle = active_bundle
            if anchor_row and anchor_row.model_artifact_path:
                anc_path = Path(anchor_row.model_artifact_path)
                if anc_path.is_file():
                    anchor_bundle = joblib.load(anc_path)

            context: Dict[str, Any] = {
                "db": db,
                "volume_multiplier": volume_multiplier,
                "adaptation_windows": adaptation_windows or [],
                "canary_windows": canary_windows,
                "normal_holdout_windows": normal_holdout_windows,
            }

            eval_result = self.pipeline.evaluate(
                candidate_bundle=cand_bundle,
                active_bundle=active_bundle,
                anchor_bundle=anchor_bundle,
                context=context,
            )

            # Update candidate_baselines table
            cand.gate_metrics = eval_result.gate_metrics
            cand_trace = list(cand.decision_trace or [])
            for r in eval_result.check_results:
                cand_trace.append(f"Gate check '{r.name}': {'PASSED' if r.passed else 'FAILED'} - {r.explanation}")
            cand.decision_trace = cand_trace

            # Append structured decision trace row
            trace_entry = DecisionTrace(
                window_id=f"gov-eval-{cand.id}",
                slice_id=cand.slice_id,
                verdict="governance_evaluated",
                action="gates_evaluated",
                steps=eval_result.decision_trace_steps,
            )
            db.add(trace_entry)
            db.commit()
            db.refresh(cand)

            return eval_result
        finally:
            if owns_db:
                db.close()

    def approve_and_promote(
        self,
        candidate_id: str,
        analyst_id: str,
        notes: str,
        db: Session,
    ) -> CandidateResponse:
        """Atomically approve and promote a candidate baseline to active serving."""
        cand = db.query(CandidateBaseline).filter(CandidateBaseline.id == candidate_id).first()
        if not cand:
            raise HTTPException(status_code=404, detail=f"Candidate baseline {candidate_id} not found.")

        # 1. Reject with 409 if mandatory checks failed
        gate_metrics = cand.gate_metrics or {}
        if gate_metrics.get("all_mandatory_passed") is False:
            failed_checks = [
                k for k, v in gate_metrics.items()
                if isinstance(v, dict) and v.get("mandatory") and not v.get("passed")
            ]
            reason = f"Mandatory governance checks failed: {', '.join(failed_checks)}"
            logger.warning("Rejected promotion for candidate %s: %s", candidate_id, reason)
            raise HTTPException(status_code=409, detail=reason)

        # 1b. Dwell time enforcement: verify minimum interval between promotions
        from ml_engine.governance.config import DWELL_TIME_MIN_SECONDS
        if DWELL_TIME_MIN_SECONDS > 0:
            last_approval = (
                db.query(ApprovalLog)
                .filter(ApprovalLog.slice_id == cand.slice_id, ApprovalLog.action == "APPROVED")
                .order_by(ApprovalLog.created_at.desc())
                .first()
            )
            if last_approval and last_approval.created_at:
                now_utc = datetime.now(timezone.utc)
                last_dt = last_approval.created_at
                if last_dt.tzinfo is None:
                    last_dt = last_dt.replace(tzinfo=timezone.utc)
                elapsed_sec = (now_utc - last_dt).total_seconds()
                if elapsed_sec < DWELL_TIME_MIN_SECONDS:
                    reason = (
                        f"Dwell time check: FAILED ({elapsed_sec:.1f}s elapsed < {DWELL_TIME_MIN_SECONDS}s "
                        f"minimum interval required between promotions)."
                    )
                    cand_trace = list(cand.decision_trace or [])
                    cand_trace.append(reason)
                    cand.decision_trace = cand_trace
                    db.commit()
                    logger.warning("Rejected promotion for candidate %s: %s", candidate_id, reason)
                    raise HTTPException(
                        status_code=409,
                        detail=f"Dwell time violation: {elapsed_sec:.1f}s elapsed since last promotion, minimum interval is {DWELL_TIME_MIN_SECONDS}s.",
                    )

        dwell_line = f"Dwell time check: PASSED (minimum interval of {DWELL_TIME_MIN_SECONDS}s satisfied)."

        # 2. Load candidate bundle
        artifact_path = Path(cand.model_artifact_path) if cand.model_artifact_path else None
        if not artifact_path or not artifact_path.is_file():
            candidate_files = list(CANDIDATES_DIR.glob(f"{cand.slice_id}_{cand.candidate_version}*.joblib"))
            if candidate_files:
                artifact_path = candidate_files[0]
            else:
                raise HTTPException(status_code=404, detail="Candidate model artifact not found on disk.")

        cand_bundle = joblib.load(artifact_path)

        # 3. ATOMIC DATABASE TRANSACTION: Deactivate existing baselines and activate candidate
        try:
            # Record explicit analyst approval log
            approval_log = ApprovalLog(
                candidate_id=cand.id,
                slice_id=cand.slice_id,
                action="APPROVED",
                analyst_id=analyst_id,
                notes=notes,
            )
            db.add(approval_log)

            # Deactivate previous active baseline for slice
            db.query(Baseline).filter(Baseline.slice_id == cand.slice_id).update({Baseline.is_active: False})
            db.query(BaselineRegistry).filter(BaselineRegistry.slice_id == cand.slice_id).update({BaselineRegistry.is_active: False})

            # Insert newly promoted Baseline
            promoted_baseline_id = str(uuid.uuid4())
            new_base = Baseline(
                id=promoted_baseline_id,
                slice_id=cand.slice_id,
                nf_id="UPF-01",
                version=cand.candidate_version,
                is_anchor=False,  # The anchor is immutable and never overwritten
                is_active=True,
                training_window_start=cand_bundle.get("training_window_start", datetime.now(timezone.utc)),
                training_window_end=cand_bundle.get("training_window_end", datetime.now(timezone.utc)),
                model_artifact_path=str(artifact_path),
                scaler_params=cand_bundle.get("scaler_params", {}),
                threshold_params=cand_bundle.get("threshold_params", {}),
                feature_schema=cand_bundle.get("feature_schema", {}),
            )
            db.add(new_base)

            # Update candidate status
            cand.status = "APPROVED"
            cand.reviewed_by = analyst_id
            cand.reviewed_at = datetime.now(timezone.utc)
            cand_trace = list(cand.decision_trace or [])
            cand_trace.append(dwell_line)
            cand_trace.append(f"Analyst promotion gate: APPROVED by {analyst_id}. Promoted to active baseline.")
            cand.decision_trace = cand_trace

            # Log audit event
            audit_ev = AuditEvent(
                event_type="PROMOTION",
                slice_id=cand.slice_id,
                actor=analyst_id,
                details={
                    "candidate_id": cand.id,
                    "promoted_version": cand.candidate_version,
                    "parent_version": cand.parent_version,
                    "notes": notes,
                },
            )
            db.add(audit_ev)

            # Append to decision traces
            trace_entry = DecisionTrace(
                window_id=f"approve-{cand.id}",
                slice_id=cand.slice_id,
                verdict="promoted",
                action="baseline_promoted",
                steps=[
                    {
                        "step_name": "analyst_approval",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "details": {"analyst_id": analyst_id, "notes": notes},
                    },
                    {
                        "step_name": "atomic_promotion",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "details": {"promoted_version": cand.candidate_version},
                    },
                ],
            )
            db.add(trace_entry)

            db.commit()
            db.refresh(cand)

            # 4. Atomically reload detection engine baseline cache
            cand_bundle["id"] = promoted_baseline_id
            cand_bundle["baseline_id"] = promoted_baseline_id
            cand_bundle["is_active"] = True
            cand_bundle["is_anchor"] = False
            detection_service.reload_baseline(cand.slice_id, cand_bundle)

            logger.info("Successfully promoted candidate %s to active serving baseline for slice %s.", cand.candidate_version, cand.slice_id)

            return CandidateResponse(
                id=cand.id,
                slice_id=cand.slice_id,
                candidate_version=cand.candidate_version,
                active_baseline_id=cand.active_baseline_id,
                anchor_baseline_id=cand.anchor_baseline_id,
                status=cand.status,
                gate_metrics=cand.gate_metrics,
                decision_trace=cand.decision_trace,
                reviewed_by=cand.reviewed_by,
                reviewed_at=cand.reviewed_at,
                created_at=cand.created_at,
            )
        except HTTPException:
            db.rollback()
            raise
        except Exception as e:
            db.rollback()
            logger.error("Error during atomic baseline promotion: %s", e)
            raise HTTPException(status_code=500, detail=f"Promotion failed: {e}")

    def reject_candidate(
        self,
        candidate_id: str,
        analyst_id: str,
        notes: str,
        db: Session,
    ) -> CandidateResponse:
        """Reject a candidate baseline, keeping active baseline unchanged."""
        cand = db.query(CandidateBaseline).filter(CandidateBaseline.id == candidate_id).first()
        if not cand:
            raise HTTPException(status_code=404, detail=f"Candidate baseline {candidate_id} not found.")

        # Log rejection
        approval_log = ApprovalLog(
            candidate_id=cand.id,
            slice_id=cand.slice_id,
            action="REJECTED",
            analyst_id=analyst_id,
            notes=notes,
        )
        db.add(approval_log)

        cand.status = "REJECTED"
        cand.reviewed_by = analyst_id
        cand.reviewed_at = datetime.now(timezone.utc)
        cand_trace = list(cand.decision_trace or [])
        cand_trace.append(f"Analyst promotion gate: REJECTED by {analyst_id}. Notes: {notes}")
        cand.decision_trace = cand_trace

        audit_ev = AuditEvent(
            event_type="REJECTION",
            slice_id=cand.slice_id,
            actor=analyst_id,
            details={"candidate_id": cand.id, "candidate_version": cand.candidate_version, "notes": notes},
        )
        db.add(audit_ev)

        trace_entry = DecisionTrace(
            window_id=f"reject-{cand.id}",
            slice_id=cand.slice_id,
            verdict="rejected",
            action="candidate_rejected",
            steps=[
                {
                    "step_name": "analyst_rejection",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "details": {"analyst_id": analyst_id, "notes": notes},
                }
            ],
        )
        db.add(trace_entry)

        db.commit()
        db.refresh(cand)

        return CandidateResponse(
            id=cand.id,
            slice_id=cand.slice_id,
            candidate_version=cand.candidate_version,
            active_baseline_id=cand.active_baseline_id,
            anchor_baseline_id=cand.anchor_baseline_id,
            status=cand.status,
            gate_metrics=cand.gate_metrics,
            decision_trace=cand.decision_trace,
            reviewed_by=cand.reviewed_by,
            reviewed_at=cand.reviewed_at,
            created_at=cand.created_at,
        )

    def rollback_baseline(
        self,
        slice_id: str,
        target_version: str,
        analyst_id: str,
        reason: str,
        db: Session,
    ) -> RollbackResponse:
        """Atomically rollback active baseline pointer to designated target baseline."""
        target_baseline = (
            db.query(Baseline)
            .filter(Baseline.slice_id == slice_id, Baseline.version == target_version)
            .first()
        )
        if not target_baseline:
            raise HTTPException(
                status_code=404,
                detail=f"Target baseline version '{target_version}' for slice '{slice_id}' not found.",
            )

        try:
            # 1. Atomically deactivate all baselines for this slice
            db.query(Baseline).filter(Baseline.slice_id == slice_id).update({Baseline.is_active: False})
            db.query(BaselineRegistry).filter(BaselineRegistry.slice_id == slice_id).update({BaselineRegistry.is_active: False})

            # 2. Activate target baseline (anchor status is strictly preserved!)
            target_baseline.is_active = True
            db.query(BaselineRegistry).filter(
                BaselineRegistry.slice_id == slice_id,
                BaselineRegistry.version == target_version,
            ).update({BaselineRegistry.is_active: True})

            # 3. Log audit event
            audit_ev = AuditEvent(
                event_type="ROLLBACK",
                slice_id=slice_id,
                actor=analyst_id,
                details={"target_version": target_version, "reason": reason},
            )
            db.add(audit_ev)

            # 4. Decision trace
            trace_entry = DecisionTrace(
                window_id=f"rollback-{slice_id}-{int(datetime.now(timezone.utc).timestamp())}",
                slice_id=slice_id,
                verdict="rollback_executed",
                action="atomic_rollback",
                steps=[
                    {
                        "step_name": "rollback",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "details": {
                            "target_version": target_version,
                            "analyst_id": analyst_id,
                            "reason": reason,
                            "anchor_preserved": target_baseline.is_anchor,
                        },
                    }
                ],
            )
            db.add(trace_entry)

            db.commit()

            # 5. Reload detection engine baseline cache to target version
            detection_service.reload_baseline(slice_id)

            logger.info("Successfully rolled back slice %s baseline to version %s.", slice_id, target_version)

            return RollbackResponse(
                status="COMPLETED",
                slice_id=slice_id,
                active_version=target_version,
                restored_artifacts=["model", "scaler", "thresholds", "schema"],
                timestamp=datetime.now(timezone.utc),
            )
        except Exception as e:
            db.rollback()
            logger.error("Error during baseline rollback: %s", e)
            raise HTTPException(status_code=500, detail=f"Rollback failed: {e}")

    def scripted_analyst_approval(
        self,
        candidate_id: str,
        db: Session,
        analyst_id: str = "scripted_eval_analyst",
        notes: str = "Scripted test evaluation approval",
    ) -> CandidateResponse:
        """Helper for automated tests to approve and promote a candidate programmatically."""
        return self.approve_and_promote(
            candidate_id=candidate_id,
            analyst_id=analyst_id,
            notes=notes,
            db=db,
        )


governance_service = GovernanceService()
# CommShield AI Core
