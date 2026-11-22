"""API endpoints for telemetry data validation and invariant checks."""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import CanonicalWindow
from ..validation import validate_telemetry_series, ValidationReport
from ..data_loader import load_5g_nidd_csv

router = APIRouter(prefix="/validation", tags=["Data Integrity & Validation"])


@router.get("/check", response_model=ValidationReport)
@router.get("/v1/check", response_model=ValidationReport)
def validate_canonical_windows(
    slice_id: Optional[str] = Query(default=None, description="Optional S-NSSAI slice filter"),
    limit: int = Query(default=300, ge=10, le=1000),
    db: Session = Depends(get_db),
) -> ValidationReport:
    """Validate canonical windows in the database for timestamp monotonicity, non-negative volumes, and non-finite values."""
    query = db.query(CanonicalWindow).order_by(CanonicalWindow.window_start.asc())
    if slice_id and slice_id.lower() != "all":
        query = query.filter(CanonicalWindow.slice_id == slice_id)
    windows = query.limit(limit).all()

    window_dicts: List[Dict[str, Any]] = [
        {
            "window_id": w.id,
            "slice_id": w.slice_id,
            "timestamp": w.window_start.isoformat(),
            "raw_counters": w.raw_counters or {},
            "ratio_features": w.ratio_features or {},
        }
        for w in windows
    ]

    return validate_telemetry_series(window_dicts)


@router.get("/real", response_model=ValidationReport)
def validate_real_dataset() -> ValidationReport:
    """Validate the loaded 5G-NIDD dataset directly for continuity and mathematical invariants."""
    windows = load_5g_nidd_csv()
    window_dicts: List[Dict[str, Any]] = [w.to_dict() for w in windows]
    return validate_telemetry_series(window_dicts)
# CommShield AI Core
