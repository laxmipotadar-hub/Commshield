from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import CanonicalWindow
from ..schemas import (
    CanonicalTrafficWindow,
    ExplainabilityResponse,
    PaginatedWindowsResponse,
)
from ..services.sample_data import (
    get_sample_explainability,
    get_sample_paginated_windows,
)

router = APIRouter(prefix="/windows", tags=["Windows & Detection"])


@router.get("", response_model=PaginatedWindowsResponse)
def list_windows(
    slice_id: Optional[str] = Query(default=None, description="Filter by S-NSSAI slice identifier"),
    limit: int = Query(default=50, ge=1, le=500, description="Page limit"),
    offset: int = Query(default=0, ge=0, description="Page offset"),
    db: Session = Depends(get_db),
) -> PaginatedWindowsResponse:
    """Paginated canonical windows."""
    query = db.query(CanonicalWindow)
    if slice_id:
        query = query.filter(CanonicalWindow.slice_id == slice_id)

    total = query.count()
    if total > 0:
        rows = query.order_by(CanonicalWindow.window_start.desc()).offset(offset).limit(limit).all()
        items = [
            CanonicalTrafficWindow(
                window_id=r.id,
                slice_id=r.slice_id,
                nf_id=r.nf_id,
                window_start=r.window_start,
                window_end=r.window_end,
                duration_sec=r.duration_sec,
                raw_counters=r.raw_counters,
                ratio_features=r.ratio_features,
                composition_vector=r.composition_vector,
                is_placeholder=False,
            )
            for r in rows
        ]
        return PaginatedWindowsResponse(
            items=items,
            total=total,
            limit=limit,
            offset=offset,
            is_placeholder=False,
        )

    # Return sample data when DB has no rows
    return get_sample_paginated_windows(
        slice_id=slice_id or "sst-1-sd-010203",
        limit=limit,
        offset=offset,
    )


@router.get("/{window_id}/explain", response_model=ExplainabilityResponse)
def explain_window(
    window_id: str,
    db: Session = Depends(get_db),
) -> ExplainabilityResponse:
    """SHAP feature attributions for window."""
    # TODO: Invoke SHAP / ExplainabilityEngine (ml_engine/detection/explainability.py) to compute feature contributions
    db_window = db.query(CanonicalWindow).filter(CanonicalWindow.id == window_id).first()
    if db_window:
        sample = get_sample_explainability(
            window_id=db_window.id,
            slice_id=db_window.slice_id,
            nf_id=db_window.nf_id,
        )
        return sample

    return get_sample_explainability(window_id=window_id)
