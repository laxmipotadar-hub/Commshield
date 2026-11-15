from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Baseline, CandidateBaseline
from ..schemas import (
    ApprovalActionRequest,
    BaselineSummaryResponse,
    CandidateResponse,
    RollbackRequest,
    RollbackResponse,
    ThreeArmComparisonResponse,
)
from ..services.sample_data import (
    get_sample_baselines,
    get_sample_candidate_decision,
    get_sample_candidates,
    get_sample_rollback,
    get_sample_three_arm,
)

router = APIRouter(tags=["Governance & Baselines"])


@router.get("/baselines", response_model=List[BaselineSummaryResponse])
def list_baselines(
    slice_id: Optional[str] = Query(default=None, description="Filter by S-NSSAI slice identifier"),
    db: Session = Depends(get_db),
) -> List[BaselineSummaryResponse]:
    """List active & anchor baselines."""
    query = db.query(Baseline)
    if slice_id:
        query = query.filter(Baseline.slice_id == slice_id)

    rows = query.all()
    if rows:
        return [
            BaselineSummaryResponse(
                id=r.id,
                slice_id=r.slice_id,
                nf_id=r.nf_id,
                version=r.version,
                is_anchor=r.is_anchor,
                is_active=r.is_active,
                training_window_start=r.training_window_start,
                training_window_end=r.training_window_end,
                model_artifact_path=r.model_artifact_path,
                scaler_params=r.scaler_params,
                threshold_params=r.threshold_params,
                feature_schema=r.feature_schema,
                created_at=r.created_at,
                is_placeholder=False,
            )
            for r in rows
        ]

    return get_sample_baselines(slice_id=slice_id or "sst-1-sd-010203")


@router.get("/candidates", response_model=List[CandidateResponse])
def list_candidates(
    status: Optional[str] = Query(default=None, description="Filter by status: PENDING, APPROVED, REJECTED, ROLLED_BACK"),
    db: Session = Depends(get_db),
) -> List[CandidateResponse]:
    """List pending shadow candidate baselines."""
    query = db.query(CandidateBaseline)
    if status:
        query = query.filter(CandidateBaseline.status == status)

    rows = query.all()
    if rows:
        return [
            CandidateResponse(
                id=r.id,
                slice_id=r.slice_id,
                candidate_version=r.candidate_version,
                active_baseline_id=r.active_baseline_id,
                anchor_baseline_id=r.anchor_baseline_id,
                status=r.status,
                gate_metrics=r.gate_metrics,
                decision_trace=r.decision_trace,
                reviewed_by=r.reviewed_by,
                reviewed_at=r.reviewed_at,
                created_at=r.created_at,
                is_placeholder=False,
            )
            for r in rows
        ]

    return get_sample_candidates(status=status or "PENDING")


@router.post("/candidates/{id}/approve", response_model=CandidateResponse)
def approve_candidate(
    id: str,
    payload: ApprovalActionRequest,
    db: Session = Depends(get_db),
) -> CandidateResponse:
    """Operator approves candidate baseline promotion."""
    # TODO: Invoke GovernanceEngine (ml_engine/governance/adaptation.py) to promote candidate to active baseline and record audit log
    cand = db.query(CandidateBaseline).filter(CandidateBaseline.id == id).first()
    if cand:
        cand.status = "APPROVED"
        cand.reviewed_by = payload.analyst_id
        cand.reviewed_at = datetime.now(timezone.utc)
        if isinstance(cand.decision_trace, list):
            cand.decision_trace = cand.decision_trace + [f"Analyst promotion gate: APPROVED by {payload.analyst_id}"]
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
            is_placeholder=False,
        )

    return get_sample_candidate_decision(candidate_id=id, status="APPROVED", analyst_id=payload.analyst_id)


@router.post("/candidates/{id}/reject", response_model=CandidateResponse)
def reject_candidate(
    id: str,
    payload: ApprovalActionRequest,
    db: Session = Depends(get_db),
) -> CandidateResponse:
    """Operator rejects candidate baseline."""
    # TODO: Invoke GovernanceEngine to reject shadow candidate and retain active baseline
    cand = db.query(CandidateBaseline).filter(CandidateBaseline.id == id).first()
    if cand:
        cand.status = "REJECTED"
        cand.reviewed_by = payload.analyst_id
        cand.reviewed_at = datetime.now(timezone.utc)
        if isinstance(cand.decision_trace, list):
            cand.decision_trace = cand.decision_trace + [f"Analyst promotion gate: REJECTED by {payload.analyst_id}"]
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
            is_placeholder=False,
        )

    return get_sample_candidate_decision(candidate_id=id, status="REJECTED", analyst_id=payload.analyst_id)


@router.post("/baselines/rollback", response_model=RollbackResponse)
def rollback_baseline(
    payload: RollbackRequest,
    db: Session = Depends(get_db),
) -> RollbackResponse:
    """Atomic rollback to designated baseline."""
    # TODO: Invoke GovernanceEngine (ml_engine/governance/adaptation.py) to atomically restore baseline artifacts and update baseline active status
    target_baseline = (
        db.query(Baseline)
        .filter(Baseline.version == payload.target_baseline_version, Baseline.slice_id == payload.slice_id)
        .first()
    )
    if target_baseline:
        db.query(Baseline).filter(Baseline.slice_id == payload.slice_id).update({Baseline.is_active: False})
        target_baseline.is_active = True
        db.commit()
        return RollbackResponse(
            status="COMPLETED",
            slice_id=payload.slice_id,
            active_version=payload.target_baseline_version,
            restored_artifacts=["model", "scaler", "thresholds", "schema"],
            timestamp=datetime.now(timezone.utc),
            is_placeholder=False,
        )

    return get_sample_rollback(slice_id=payload.slice_id, target_version=payload.target_baseline_version)


@router.get("/experiments/three-arm", response_model=ThreeArmComparisonResponse)
def get_three_arm_comparison(
    dataset_id: Optional[str] = Query(default="5g_nidd_portscan_growth", description="Dataset identifier"),
    db: Session = Depends(get_db),
) -> ThreeArmComparisonResponse:
    """Compare metrics across arms A/B/C."""
    # TODO: Invoke EvaluationEngine (ml_engine/evaluation/benchmark.py) to benchmark metric comparisons across Arms A/B/C
    return get_sample_three_arm(dataset_id=dataset_id or "5g_nidd_portscan_growth")
