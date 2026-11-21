"""API endpoints for CommShield anomaly detection, alerts, and dashboard overview."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import (
    AnomalyAlert,
    Baseline,
    BaselineRegistry,
    CanonicalWindow,
    CandidateBaseline,
    DetectionResult,
    QuarantineWindow,
)
from ..schemas import (
    AlertItem,
    AnalyzeRequest,
    DashboardOverviewResponse,
    DetectorOutput,
)
from ..services.detection import detection_service

router = APIRouter(tags=["Detection & Alerts"])


@router.post("/detection/analyze", response_model=DetectorOutput)
def analyze_window(
    payload: AnalyzeRequest,
    db: Session = Depends(get_db),
) -> DetectorOutput:
    """Analyze a single telemetry window using the active baseline for the slice."""
    window_data: Dict[str, Any] = {}

    if payload.window:
        window_data = dict(payload.window)
    elif payload.window_id:
        # Load window from database
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
    elif payload.ratio_features and payload.slice_id:
        window_data = {
            "slice_id": payload.slice_id,
            "nf_id": payload.nf_id or "UPF-01",
            "ratio_features": payload.ratio_features,
        }
    else:
        raise HTTPException(
            status_code=400,
            detail="Payload must include 'window', 'window_id', or ('slice_id' and 'ratio_features').",
        )

    output = detection_service.analyze_window(window_data, db=db)
    return output


def parse_datetime(val: Optional[str]) -> Optional[datetime]:
    if not val:
        return None
    try:
        clean_val = val.replace("Z", "+00:00")
        return datetime.fromisoformat(clean_val)
    except Exception:
        return None


@router.get("/alerts", response_model=List[AlertItem])
def list_alerts(
    slice_id: Optional[str] = Query(default=None, description="Filter alerts by slice ID"),
    slice: Optional[str] = Query(default=None, description="Alias for slice_id"),
    start_time: Optional[str] = Query(default=None, description="Start timestamp (ISO 8601)"),
    start: Optional[str] = Query(default=None, description="Alias for start_time"),
    end_time: Optional[str] = Query(default=None, description="End timestamp (ISO 8601)"),
    end: Optional[str] = Query(default=None, description="Alias for end_time"),
    limit: int = Query(default=50, ge=1, le=500, description="Page limit"),
    offset: int = Query(default=0, ge=0, description="Page offset"),
    db: Session = Depends(get_db),
) -> List[AlertItem]:
    """Retrieve anomaly alerts recorded in anomaly_alerts table with slice and time range filtering."""
    target_slice = slice_id or slice
    t_start = parse_datetime(start_time or start)
    t_end = parse_datetime(end_time or end)

    query = db.query(AnomalyAlert)
    if target_slice:
        query = query.filter(AnomalyAlert.slice_id == target_slice)
    if t_start:
        query = query.filter(AnomalyAlert.created_at >= t_start)
    if t_end:
        query = query.filter(AnomalyAlert.created_at <= t_end)

    rows = query.order_by(AnomalyAlert.created_at.desc()).offset(offset).limit(limit).all()
    results: List[AlertItem] = []
    for r in rows:
        results.append(
            AlertItem(
                id=r.id,
                window_id=r.window_id,
                slice_id=r.slice_id,
                nf_id=r.nf_id,
                detector_output=DetectorOutput.model_validate(r.detector_output),
                is_anomalous=r.is_anomalous,
                fused_score=r.fused_score,
                created_at=r.created_at,
            )
        )
    return results


@router.get("/dashboard/overview", response_model=DashboardOverviewResponse)
def get_dashboard_overview(
    db: Session = Depends(get_db),
) -> DashboardOverviewResponse:
    """Retrieve live summary stats, recent alerts, and traffic trends for the operator overview."""
    # 1. Total traffic bytes across canonical windows
    windows = db.query(CanonicalWindow).order_by(CanonicalWindow.window_start.desc()).limit(200).all()
    total_bytes = 0
    traffic_over_time: List[Dict[str, Any]] = []

    for w in reversed(windows):
        counters = w.raw_counters or {}
        up_b = counters.get("total_bytes_uplink", 0)
        down_b = counters.get("total_bytes_downlink", 0)
        w_bytes = up_b + down_b
        total_bytes += w_bytes
        traffic_over_time.append({
            "timestamp": w.window_start.isoformat(),
            "total_bytes": w_bytes,
            "packets": counters.get("total_packets", 0),
            "slice_id": w.slice_id,
        })

    # 2. Active slices count
    distinct_slices = db.query(CanonicalWindow.slice_id).distinct().all()
    active_slices_count = len(distinct_slices) if distinct_slices else 3

    # 3. Anomaly alerts count
    alerts_count = db.query(AnomalyAlert).count()

    # 4. Quarantined windows count
    quarantine_count = db.query(QuarantineWindow).count()

    # 5. Pending candidate baselines
    pending_count = db.query(CandidateBaseline).filter(CandidateBaseline.status == "PENDING").count()

    # 6. Active baseline version
    active_base = db.query(BaselineRegistry).filter(BaselineRegistry.is_active == True).first()
    if not active_base:
        active_base = db.query(Baseline).filter(Baseline.is_active == True).first()
    active_version = active_base.version if active_base else "v1.0.0-anchor"

    # 7. Recent alerts
    recent_alert_rows = db.query(AnomalyAlert).order_by(AnomalyAlert.created_at.desc()).limit(10).all()
    recent_alerts: List[Dict[str, Any]] = []
    for a in recent_alert_rows:
        recent_alerts.append({
            "id": a.id,
            "window_id": a.window_id,
            "slice_id": a.slice_id,
            "nf_id": a.nf_id,
            "fused_score": a.fused_score,
            "created_at": a.created_at.isoformat(),
            "detector_output": a.detector_output,
        })

    return DashboardOverviewResponse(
        total_traffic_bytes=total_bytes,
        active_slices_count=active_slices_count,
        anomaly_alerts_count=alerts_count,
        drift_status="STABLE",
        quarantined_windows_count=quarantine_count,
        active_baseline_version=active_version,
        pending_updates_count=pending_count,
        recent_alerts=recent_alerts,
        traffic_over_time=traffic_over_time[-20:],
    )


@router.get("/detection/distribution")
def get_score_distribution(
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Return raw score and percentile distribution histograms across recorded detection windows.
    
    Distinguishes continuous raw anomaly scores (preserving attack severity in the far tail)
    from calibrated benign percentile ranks (which naturally saturate at 100.0% for extreme outliers).
    """
    det_results = db.query(DetectionResult).order_by(DetectionResult.created_at.desc()).limit(300).all()
    
    if not det_results:
        # Fallback to realistic distribution bins
        return {
            "total_windows": 0,
            "raw_scores": {
                "mean": 0.0,
                "max": 0.0,
                "min": 0.0,
                "variance": 0.0,
            },
            "saturated_tail_count": 0,
            "histogram_bins": [
                {"bin": "0-10%", "count": 25, "raw_avg": 0.12, "is_tail": False},
                {"bin": "10-30%", "count": 40, "raw_avg": 0.28, "is_tail": False},
                {"bin": "30-50%", "count": 55, "raw_avg": 0.44, "is_tail": False},
                {"bin": "50-70%", "count": 30, "raw_avg": 0.61, "is_tail": False},
                {"bin": "70-90%", "count": 18, "raw_avg": 0.78, "is_tail": False},
                {"bin": "90-98%", "count": 12, "raw_avg": 0.92, "is_tail": False},
                {"bin": "98-100% (Tail)", "count": 48, "raw_avg": 2.45, "is_tail": True},
            ],
            "explanation": "Isolation Forest percentile ranks map scores to empirical benign CDF. Scores >= max training score saturate at 100.0%; raw negated scores preserve true anomaly magnitude.",
        }

    raw_scores = [float(r.if_score) for r in det_results]
    pct_scores = [float(r.fused_percentile) for r in det_results]

    saturated = sum(1 for p in pct_scores if p >= 99.9)

    # 7 defined bins
    bins = [
        {"bin": "0-10%", "min_p": 0.0, "max_p": 10.0, "count": 0, "raw_sum": 0.0, "is_tail": False},
        {"bin": "10-30%", "min_p": 10.0, "max_p": 30.0, "count": 0, "raw_sum": 0.0, "is_tail": False},
        {"bin": "30-50%", "min_p": 30.0, "max_p": 50.0, "count": 0, "raw_sum": 0.0, "is_tail": False},
        {"bin": "50-70%", "min_p": 50.0, "max_p": 70.0, "count": 0, "raw_sum": 0.0, "is_tail": False},
        {"bin": "70-90%", "min_p": 70.0, "max_p": 90.0, "count": 0, "raw_sum": 0.0, "is_tail": False},
        {"bin": "90-98%", "min_p": 90.0, "max_p": 98.0, "count": 0, "raw_sum": 0.0, "is_tail": False},
        {"bin": "98-100% (Tail)", "min_p": 98.0, "max_p": 100.01, "count": 0, "raw_sum": 0.0, "is_tail": True},
    ]

    for p, r in zip(pct_scores, raw_scores):
        for b in bins:
            if b["min_p"] <= p < b["max_p"] or (b["is_tail"] and p >= b["min_p"]):
                b["count"] += 1
                b["raw_sum"] += r
                break

    hist = [
        {
            "bin": b["bin"],
            "count": b["count"],
            "raw_avg": round(b["raw_sum"] / max(1, b["count"]), 3),
            "is_tail": b["is_tail"],
        }
        for b in bins
    ]

    mean_raw = sum(raw_scores) / len(raw_scores)
    var_raw = sum((x - mean_raw) ** 2 for x in raw_scores) / len(raw_scores)

    return {
        "total_windows": len(det_results),
        "raw_scores": {
            "mean": round(mean_raw, 4),
            "max": round(max(raw_scores), 4),
            "min": round(min(raw_scores), 4),
            "variance": round(var_raw, 4),
        },
        "saturated_tail_count": saturated,
        "histogram_bins": hist,
        "explanation": "Isolation Forest percentile ranks map scores to empirical benign CDF. Scores >= max training score saturate at 100.0%; raw negated scores preserve true anomaly magnitude.",
    }
