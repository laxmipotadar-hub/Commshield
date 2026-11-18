import logging
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
import numpy as np
from sqlalchemy.orm import Session

try:
    import shap
    HAS_SHAP = True
except ImportError:
    shap = None
    HAS_SHAP = False

from ml_engine.preprocessing.windowing import FEATURE_NAMES
from ..services.detection import detection_service
from ..database import get_db

logger = logging.getLogger("commshield.windows")
from ..models import (
    AttributionResult,
    Baseline,
    CanonicalWindow,
    DetectionResult,
)
from ..schemas import (
    CanonicalTrafficWindow,
    ExplainabilityResponse,
    PaginatedWindowsResponse,
)

router = APIRouter(prefix="/windows", tags=["Windows & Detection"])


def parse_datetime(val: Optional[str]) -> Optional[datetime]:
    if not val:
        return None
    try:
        # Handle ISO with Z or offset
        clean_val = val.replace("Z", "+00:00")
        return datetime.fromisoformat(clean_val)
    except Exception:
        return None


@router.get("", response_model=PaginatedWindowsResponse)
def list_windows(
    slice_id: Optional[str] = Query(default=None, description="Filter by S-NSSAI slice identifier"),
    slice: Optional[str] = Query(default=None, description="Alias for slice_id"),
    start_time: Optional[str] = Query(default=None, description="Start timestamp (ISO 8601)"),
    start: Optional[str] = Query(default=None, description="Alias for start_time"),
    end_time: Optional[str] = Query(default=None, description="End timestamp (ISO 8601)"),
    end: Optional[str] = Query(default=None, description="Alias for end_time"),
    limit: int = Query(default=50, ge=1, le=500, description="Page limit"),
    offset: int = Query(default=0, ge=0, description="Page offset"),
    db: Session = Depends(get_db),
) -> PaginatedWindowsResponse:
    """Paginated canonical windows with slice and time range filtering."""
    target_slice = slice_id or slice
    t_start = parse_datetime(start_time or start)
    t_end = parse_datetime(end_time or end)

    query = db.query(CanonicalWindow)
    if target_slice:
        query = query.filter(CanonicalWindow.slice_id == target_slice)
    if t_start:
        query = query.filter(CanonicalWindow.window_start >= t_start)
    if t_end:
        query = query.filter(CanonicalWindow.window_end <= t_end)

    total = query.count()
    if total == 0:
        return PaginatedWindowsResponse(
            items=[],
            total=0,
            limit=limit,
            offset=offset,
        )

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
        )
        for r in rows
    ]

    return PaginatedWindowsResponse(
        items=items,
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{window_id}/explain", response_model=ExplainabilityResponse)
def explain_window(
    window_id: str,
    db: Session = Depends(get_db),
) -> ExplainabilityResponse:
    """Explainability and feature contributions for a specific canonical window."""
    db_window = db.query(CanonicalWindow).filter(CanonicalWindow.id == window_id).first()
    if not db_window:
        raise HTTPException(status_code=404, detail=f"Canonical window '{window_id}' not found.")

    # 1. Fetch active baseline for feature deviation reference
    active_base = (
        db.query(Baseline)
        .filter(Baseline.slice_id == db_window.slice_id, Baseline.is_active == True)
        .first()
    )

    # 2. Query detection and attribution outcomes
    det = db.query(DetectionResult).filter(DetectionResult.window_id == window_id).first()
    attr = db.query(AttributionResult).filter(AttributionResult.window_id == window_id).first()

    is_anom = det.is_anomalous if det else False
    fused_p = float(det.fused_percentile) if det else 0.5
    verdict = attr.verdict if attr else ("likely_attack" if is_anom else "likely_benign")
    abstain = attr.abstain_reason if attr else None

    # 3. For flagged windows only: compute real SHAP values for Isolation Forest with TreeExplainer
    shap_values = {}
    top_contributors = []
    ratio_features = db_window.ratio_features or {}

    if is_anom:
        computed = False
        if HAS_SHAP:
            try:
                bundle = detection_service.get_baseline_bundle(db_window.slice_id, db=db)
                if bundle and "isolation_forest" in bundle:
                    if_det = bundle["isolation_forest"]
                    scaler = bundle.get("scaler")
                    if scaler and hasattr(scaler, "transform_vector"):
                        scaled_vec = scaler.transform_vector(ratio_features)
                        x_vals = [float(scaled_vec.get(f, 0.0)) for f in FEATURE_NAMES]
                    else:
                        scaler_params = active_base.scaler_params if active_base and active_base.scaler_params else {}
                        meds = scaler_params.get("medians", {})
                        iqrs = scaler_params.get("iqrs", {})
                        x_vals = [
                            (float(ratio_features.get(f, 0.0)) - float(meds.get(f, 0.0))) / max(1e-4, float(iqrs.get(f, 1.0)))
                            for f in FEATURE_NAMES
                        ]

                    X = np.array([x_vals], dtype=float)
                    explainer = shap.TreeExplainer(if_det.model)
                    sv = explainer.shap_values(X)
                    if isinstance(sv, list):
                        sv = sv[0]
                    if sv.ndim > 1:
                        sv = sv[0]
                    shap_values = {f: round(float(val), 4) for f, val in zip(FEATURE_NAMES, sv)}
                    computed = True
            except Exception as e:
                logger.warning("Failed computing SHAP with TreeExplainer: %s", e)

        if not computed:
            # Fallback to per-feature robust z-scores if SHAP cannot run
            scaler_params = active_base.scaler_params if active_base and active_base.scaler_params else {}
            medians = scaler_params.get("medians", {})
            iqrs = scaler_params.get("iqrs", {})
            for k, v in ratio_features.items():
                med = float(medians.get(k, 0.0))
                iqr = float(max(0.0001, iqrs.get(k, 1.0)))
                dev = round((float(v) - med) / iqr, 4)
                shap_values[k] = dev

        top_contributors = sorted(shap_values.items(), key=lambda x: abs(x[1]), reverse=True)

    # 4. Formulate hypothesis
    if is_anom:
        if top_contributors:
            main_feat, dev_val = top_contributors[0]
            hypothesis = (
                f"Elevated risk: feature '{main_feat}' contributed {dev_val:+.4f} (SHAP) "
                f"towards anomaly threshold against active baseline {active_base.version if active_base else 'v1.0.0-anchor'}."
            )
        else:
            hypothesis = "Multi-detector anomaly triggered across combined traffic indicators."
    else:
        hypothesis = "Traffic distribution adheres to calibrated baseline nominal boundaries."

    return ExplainabilityResponse(
        window_id=db_window.id,
        slice_id=db_window.slice_id,
        nf_id=db_window.nf_id,
        is_anomalous=is_anom,
        fused_percentile=fused_p,
        shap_values=shap_values,
        hypothesis=hypothesis,
        attribution_summary={
            "verdict": verdict,
            "abstain_reason": abstain,
        },
    )
