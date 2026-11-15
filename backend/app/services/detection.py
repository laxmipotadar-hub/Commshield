"""Detection service executing real-time anomaly evaluation on 5G telemetry windows."""

from datetime import datetime, timezone
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
import uuid

import joblib
import numpy as np
from sqlalchemy.orm import Session

from ..database import SessionLocal
from ..models import AnomalyAlert, Baseline, BaselineRegistry, CanonicalWindow, DetectionResult
from ..schemas import (
    AutoencoderScore,
    CusumScore,
    DetectorOutput,
    FusionScore,
    IsolationForestScore,
)
from ml_engine.preprocessing.windowing import FEATURE_NAMES

logger = logging.getLogger("commshield.detection")

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
PROCESSED_BASELINES_DIR = PROJECT_ROOT / "data" / "processed" / "baselines"


class DetectionService:
    """Detection service orchestrating baseline retrieval, feature extraction, and scoring."""

    def __init__(self):
        self._loaded_baselines: Dict[str, Dict[str, Any]] = {}

    def get_baseline_bundle(self, slice_id: str, db: Optional[Session] = None) -> Optional[Dict[str, Any]]:
        """Retrieve baseline bundle for slice_id, from cache or disk."""
        if slice_id in self._loaded_baselines:
            return self._loaded_baselines[slice_id]

        owns_db = False
        if db is None:
            db = SessionLocal()
            owns_db = True

        try:
            # Query active baseline from Baseline table (referenced by detection_results.baseline_id FK)
            base_row = (
                db.query(Baseline)
                .filter(Baseline.slice_id == slice_id, Baseline.is_active == True)
                .first()
            )
            reg_row = (
                db.query(BaselineRegistry)
                .filter(BaselineRegistry.slice_id == slice_id, BaselineRegistry.is_active == True)
                .first()
            )
            artifact_path = None
            if reg_row and reg_row.model_artifact_path:
                artifact_path = Path(reg_row.model_artifact_path)
            elif base_row and base_row.model_artifact_path:
                artifact_path = Path(base_row.model_artifact_path)
            else:
                # Fallback to standard path
                candidates = list(PROCESSED_BASELINES_DIR.glob(f"{slice_id}_*.joblib"))
                if candidates:
                    artifact_path = candidates[0]

            if artifact_path and artifact_path.is_file():
                bundle = joblib.load(artifact_path)
                bundle["baseline_id"] = base_row.id if base_row else (reg_row.id if reg_row else str(uuid.uuid4()))
                self._loaded_baselines[slice_id] = bundle
                return bundle

            # If no baseline found, train baselines
            from ml_engine.baseline.trainer import train_all_baselines
            train_all_baselines(db=db)

            # Retry loading
            candidates = list(PROCESSED_BASELINES_DIR.glob(f"{slice_id}_*.joblib"))
            if candidates and candidates[0].is_file():
                bundle = joblib.load(candidates[0])
                base_ref = db.query(Baseline).filter(Baseline.slice_id == slice_id).first()
                reg_ref = db.query(BaselineRegistry).filter(BaselineRegistry.slice_id == slice_id).first()
                bundle["baseline_id"] = base_ref.id if base_ref else (reg_ref.id if reg_ref else str(uuid.uuid4()))
                self._loaded_baselines[slice_id] = bundle
                return bundle

            return None
        except Exception as e:
            logger.error("Failed to load baseline bundle for %s: %s", slice_id, e)
            return None
        finally:
            if owns_db:
                db.close()

    def analyze_window(
        self,
        window: Dict[str, Any],
        db: Optional[Session] = None,
    ) -> DetectorOutput:
        """Run anomaly detection on a single window dictionary and persist results."""
        slice_id = window.get("slice_id", "sst-1-sd-010203")
        nf_id = window.get("nf_id", "UPF-01")
        window_id = window.get("window_id") or str(uuid.uuid4())
        ratios = window.get("ratio_features", {})

        owns_db = False
        if db is None:
            db = SessionLocal()
            owns_db = True

        try:
            bundle = self.get_baseline_bundle(slice_id, db=db)
            if not bundle:
                # Fallback placeholder if no baseline can be trained or loaded
                return DetectorOutput(
                    window_id=window_id,
                    slice_id=slice_id,
                    nf_id=nf_id,
                    evaluated_at=datetime.now(timezone.utc),
                    baseline_version="v1.0.0-anchor",
                    isolation_forest=IsolationForestScore(
                        raw_score_negated=0.5,
                        benign_percentile=50.0,
                        threshold_percentile=95.0,
                        is_flagged=False,
                    ),
                    autoencoder=None,
                    fusion=FusionScore(
                        primary_rule="MAX_PERCENTILE",
                        fused_percentile=50.0,
                        secondary_mean_percentile=50.0,
                        agreement_state="NONE",
                        is_anomalous=False,
                    ),
                    cusum=None,
                    is_placeholder=True,
                )

            detector = bundle["detector"]
            scaler = bundle["scaler"]
            threshold_params = bundle.get("threshold_params", {})
            threshold_pct = float(threshold_params.get("threshold_percentile", 95.0))

            # Transform ratio features
            scaled_vector = scaler.transform_vector(ratios)
            x_row = np.array([[scaled_vector[f] for f in FEATURE_NAMES]], dtype=np.float32)

            # Evaluate sample
            raw_score, percentile, is_flagged = detector.evaluate_sample(x_row)

            # Fused score equals Isolation Forest score for now
            fused_score = percentile
            is_anomalous = is_flagged
            agreement_state = "IF_ONLY" if is_flagged else "NONE"

            output = DetectorOutput(
                window_id=window_id,
                slice_id=slice_id,
                nf_id=nf_id,
                evaluated_at=datetime.now(timezone.utc),
                baseline_version=bundle.get("version", "v1.0.0-anchor"),
                isolation_forest=IsolationForestScore(
                    raw_score_negated=round(raw_score, 4),
                    benign_percentile=round(percentile, 4),
                    threshold_percentile=round(threshold_pct, 4),
                    is_flagged=is_flagged,
                ),
                autoencoder=None,
                fusion=FusionScore(
                    primary_rule="MAX_PERCENTILE",
                    fused_percentile=round(fused_score, 4),
                    secondary_mean_percentile=round(fused_score, 4),
                    agreement_state=agreement_state,
                    is_anomalous=is_anomalous,
                ),
                cusum=None,
                is_placeholder=False,
            )

            # 1. Write to anomaly_alerts if anomalous per contract
            if is_anomalous:
                alert_row = AnomalyAlert(
                    id=str(uuid.uuid4()),
                    window_id=window_id,
                    slice_id=slice_id,
                    nf_id=nf_id,
                    detector_output=output.model_dump(mode="json"),
                    is_anomalous=True,
                    fused_score=round(fused_score, 4),
                    created_at=datetime.now(timezone.utc),
                )
                db.add(alert_row)

            # 2. Write to detection_results table if canonical window exists in DB
            win_exists = db.query(CanonicalWindow).filter(CanonicalWindow.id == window_id).first()
            if win_exists:
                b_row = db.query(Baseline).filter(Baseline.slice_id == slice_id, Baseline.is_active == True).first()
                if not b_row:
                    b_row = db.query(Baseline).filter(Baseline.slice_id == slice_id).first()
                if b_row:
                    det_row = DetectionResult(
                        id=str(uuid.uuid4()),
                        window_id=window_id,
                        slice_id=slice_id,
                        baseline_id=b_row.id,
                        if_score=round(raw_score, 4),
                        if_percentile=round(percentile, 4),
                        ae_recon_error=0.0,
                        ae_percentile=0.0,
                        fused_percentile=round(fused_score, 4),
                        cusum_score=0.0,
                        agreement_state=agreement_state,
                        is_anomalous=is_anomalous,
                        created_at=datetime.now(timezone.utc),
                    )
                    db.add(det_row)

            db.commit()
            return output
        except Exception as e:
            db.rollback()
            logger.error("Error analyzing window %s: %s", window_id, e)
            raise
        finally:
            if owns_db:
                db.close()


# Global detection service singleton
detection_service = DetectionService()
