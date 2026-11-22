"""API endpoints for CommShield drift attribution, drift events, and decision traces."""

from datetime import datetime
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


def parse_datetime(val: Optional[str]) -> Optional[datetime]:
    if not val:
        return None
    try:
        clean_val = val.replace("Z", "+00:00")
        return datetime.fromisoformat(clean_val)
    except Exception:
        return None


@router.get("/drift/events", response_model=List[DriftEventItem])
@router.get("/v1/drift/events", response_model=List[DriftEventItem])
def list_drift_events(
    slice_id: Optional[str] = None,
    slice: Optional[str] = None,
    start_time: Optional[str] = None,
    start: Optional[str] = None,
    end_time: Optional[str] = None,
    end: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
) -> List[DriftEventItem]:
    """Retrieve recorded ADWIN drift events with slice and time range filtering."""
    target_slice = slice_id or slice
    t_start = parse_datetime(start_time or start)
    t_end = parse_datetime(end_time or end)

    query = db.query(DriftEvent)
    if target_slice:
        query = query.filter(DriftEvent.slice_id == target_slice)
    if t_start:
        query = query.filter(DriftEvent.event_time >= t_start)
    if t_end:
        query = query.filter(DriftEvent.event_time <= t_end)

    safe_limit = int(limit) if isinstance(limit, (int, float, str)) else 50
    safe_offset = int(offset) if isinstance(offset, (int, float, str)) else 0
    rows = query.order_by(DriftEvent.event_time.desc()).offset(safe_offset).limit(safe_limit).all()
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


@router.get("/decision-traces", response_model=List[DecisionTraceResponse])
@router.get("/v1/decision-traces", response_model=List[DecisionTraceResponse])
def list_decision_traces(
    slice_id: Optional[str] = Query(None, alias="slice"),
    limit: int = 50,
    db: Session = Depends(get_db),
) -> List[DecisionTraceResponse]:
    """List recent decision traces across attribution and governance steps."""
    query = db.query(DecisionTrace)
    if slice_id:
        query = query.filter(DecisionTrace.slice_id == slice_id)
    rows = query.order_by(DecisionTrace.created_at.desc()).limit(limit).all()
    return [
        DecisionTraceResponse(
            id=r.id,
            window_id=r.window_id,
            slice_id=r.slice_id,
            alert_id=r.alert_id,
            drift_event_id=r.drift_event_id,
            verdict=r.verdict,
            action=r.action,
            steps=r.steps or [],
            created_at=r.created_at,
        )
        for r in rows
    ]


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
    slice_id: Optional[str] = None,
    limit: int = 100,
    db: Session = Depends(get_db),
) -> List[Dict[str, Any]]:
    """List isolated quarantine windows awaiting operator resolution or candidate retraining."""
    query = db.query(QuarantineWindow)
    if slice_id:
        query = query.filter(QuarantineWindow.slice_id == slice_id)

    safe_limit = int(limit) if isinstance(limit, (int, float, str)) else 100
    rows = query.order_by(QuarantineWindow.quarantined_at.desc()).limit(safe_limit).all()
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
# CommShield AI Core
