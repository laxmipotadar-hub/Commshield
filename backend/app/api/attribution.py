"""API endpoints for CommShield drift attribution, drift events, and decision traces."""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import (
    CanonicalWindow,
    DecisionTrace,
    DriftEvent,
    QuarantineWindow,
)
from ..schemas import (
    AttributionAnalyzeRequest,
    AttributionOutput,
    DecisionTraceResponse,
    DriftEventItem,
)
from ..services.attribution import attribution_service

router = APIRouter(tags=["Attribution & Drift"])


@router.post("/attribution/analyze", response_model=AttributionOutput)
@router.post("/v1/attribution/analyze", response_model=AttributionOutput)
def analyze_drift_and_attribution(
    payload: AttributionAnalyzeRequest,
    db: Session = Depends(get_db),
) -> AttributionOutput:
    """Analyze a telemetry window for statistical drift and perform evidence-based attribution."""
    window_data: Dict[str, Any] = {}

    if payload.window:
        window_data = dict(payload.window)
    elif payload.window_id:
        db_win = db.query(CanonicalWindow).filter(CanonicalWindow.id == payload.window_id).first()
        if not db_win:
            raise HTTPException(status_code=404, detail=f"Window {payload.window_id} not found.")
        window_data = {
            "window_id": db_win.id,
            "slice_id": db_win.slice_id,
            "nf_id": db_win.nf_id,
            "window_start": db_win.window_start.isoformat(),
            "window_end": db_win.window_end.isoformat(),
            "duration_sec": db_win.duration_sec,
            "raw_counters": db_win.raw_counters,
            "ratio_features": db_win.ratio_features,
            "composition_vector": db_win.composition_vector,
        }
    else:
        raise HTTPException(
            status_code=400,
            detail="Payload must include 'window' or 'window_id'.",
        )

    output = attribution_service.analyze_window(
        window=window_data,
        db=db,
        scenario=payload.scenario,
        force_drift=bool(payload.force_drift),
    )
    return output


@router.get("/drift/events", response_model=List[DriftEventItem])
@router.get("/v1/drift/events", response_model=List[DriftEventItem])
def list_drift_events(
    slice_id: Optional[str] = Query(default=None, description="Filter by slice ID"),
    limit: int = Query(default=50, ge=1, le=500, description="Page limit"),
    offset: int = Query(default=0, ge=0, description="Page offset"),
    db: Session = Depends(get_db),
) -> List[DriftEventItem]:
    """Retrieve recorded ADWIN drift events and their corresponding attributions."""
    query = db.query(DriftEvent)
    if slice_id:
        query = query.filter(DriftEvent.slice_id == slice_id)

    rows = query.order_by(DriftEvent.event_time.desc()).offset(offset).limit(limit).all()
    results: List[DriftEventItem] = []
    for r in rows:
        attr_data = r.attribution or {}
        results.append(
            DriftEventItem(
                id=r.id,
                window_id=r.window_id,
                slice_id=r.slice_id,
                event_time=r.event_time,
                volume_multiplier=r.volume_multiplier,
                drift_detected=r.drift_detected,
                verdict=attr_data.get("verdict", "uncertain"),
                abstain_reason=attr_data.get("abstain_reason"),
                action=attr_data.get("action", "quarantine"),
                decision_trace_id=r.decision_trace_id,
                attribution=attr_data,
            )
        )
    return results


@router.get("/decision-traces/{trace_id}", response_model=DecisionTraceResponse)
@router.get("/v1/decision-traces/{trace_id}", response_model=DecisionTraceResponse)
def get_decision_trace(
    trace_id: str,
    db: Session = Depends(get_db),
) -> DecisionTraceResponse:
    """Retrieve structured audit steps and evidence for a specific decision trace."""
    row = db.query(DecisionTrace).filter(DecisionTrace.id == trace_id).first()
    if not row:
        # Check by window_id as fallback
        row = db.query(DecisionTrace).filter(DecisionTrace.window_id == trace_id).first()

    if not row:
        raise HTTPException(status_code=404, detail=f"Decision trace {trace_id} not found.")

    return DecisionTraceResponse(
        id=row.id,
        window_id=row.window_id,
        slice_id=row.slice_id,
        alert_id=row.alert_id,
        drift_event_id=row.drift_event_id,
        verdict=row.verdict,
        action=row.action,
        steps=row.steps or [],
        created_at=row.created_at,
    )


@router.get("/quarantine/windows")
@router.get("/v1/quarantine/windows")
def list_quarantine_windows(
    slice_id: Optional[str] = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
) -> List[Dict[str, Any]]:
    """List isolated quarantine windows awaiting operator resolution or candidate retraining."""
    query = db.query(QuarantineWindow)
    if slice_id:
        query = query.filter(QuarantineWindow.slice_id == slice_id)

    rows = query.order_by(QuarantineWindow.quarantined_at.desc()).limit(limit).all()
    return [
        {
            "id": r.id,
            "window_id": r.window_id,
            "slice_id": r.slice_id,
            "reason": r.reason,
            "scenario": r.scenario,
            "quarantined_at": r.quarantined_at.isoformat(),
        }
        for r in rows
    ]
