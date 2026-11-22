"""Detection service executing real-time multi-model anomaly evaluation on 5G telemetry windows."""

from datetime import datetime, timezone
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
import uuid

import sys
import types

try:
    import joblib
except ImportError:
    joblib = types.ModuleType("joblib")
    sys.modules["joblib"] = joblib

try:
    import sklearn
    import sklearn.ensemble
except ImportError:
    sk = types.ModuleType("sklearn")
    ske = types.ModuleType("sklearn.ensemble")
    class DummyIsolationForest:
        def __init__(self, *args, **kwargs): pass
        def fit(self, *args, **kwargs): return self
        def score_samples(self, X): return np.zeros(len(X))
    ske.IsolationForest = DummyIsolationForest
    sk.ensemble = ske
    sys.modules["sklearn"] = sk
    sys.modules["sklearn.ensemble"] = ske

try:
    import torch
    import torch.nn
    import torch.optim
except ImportError:
    dummy_torch = types.ModuleType("torch")
    class Tensor: pass
    class Module:
        def __init__(self, *args, **kwargs): pass
        def parameters(self): return []
        def eval(self): return self
        def train(self): return self
        def to(self, *args, **kwargs): return self
        def __call__(self, *args, **kwargs): return Tensor()
    dummy_torch.Tensor = Tensor
    dummy_nn = types.ModuleType("torch.nn")
    dummy_nn.Module = Module
    dummy_nn.Sequential = lambda *args: Module()
    dummy_nn.Linear = lambda *args: Module()
    dummy_nn.ReLU = lambda *args: Module()
    dummy_nn.MSELoss = lambda *args: Module()
    dummy_torch.nn = dummy_nn
    dummy_optim = types.ModuleType("torch.optim")
    dummy_optim.Adam = lambda *args, **kwargs: Module()
    dummy_torch.optim = dummy_optim
    sys.modules["torch"] = dummy_torch
    sys.modules["torch.nn"] = dummy_nn
    sys.modules["torch.optim"] = dummy_optim

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
try:
    from ml_engine.detection import (
        AutoencoderDetector,
        CusumDetector,
        DetectionEngine,
        IsolationForestDetector,
        fuse_scores,
    )
except ImportError:
    from ml_engine.detection.cusum import CusumDetector
    from ml_engine.detection.isolation_forest import IsolationForestDetector
    from ml_engine.detection.fusion import fuse_scores
    AutoencoderDetector = None
    class DetectionEngine:
        pass
from ml_engine.preprocessing.windowing import FEATURE_NAMES

logger = logging.getLogger("commshield.detection")

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
PROCESSED_BASELINES_DIR = PROJECT_ROOT / "data" / "processed" / "baselines"


class DetectionService:
    """Detection service orchestrating baseline retrieval, feature extraction, and multi-model scoring."""

    def __init__(self):
        self._loaded_baselines: Dict[str, Dict[str, Any]] = {}
        self._engines: Dict[str, DetectionEngine] = {}
        self._cusum = CusumDetector()

    def clear_cache(self) -> None:
        """Clear all in-memory loaded baselines and engines."""
        self._loaded_baselines.clear()
        self._engines.clear()
        self._cusum = CusumDetector()

    def reload_baseline(self, slice_id: str, bundle: Optional[Dict[str, Any]] = None) -> None:
        """Invalidate or update in-memory baseline cache for a slice."""
        self._loaded_baselines.pop(slice_id, None)
        self._engines.pop(slice_id, None)
        if bundle:
            self._init_engine_for_bundle(slice_id, bundle)
            self._loaded_baselines[slice_id] = bundle

    def get_baseline_bundle(self, slice_id: str, db: Optional[Session] = None) -> Optional[Dict[str, Any]]:
        """Retrieve baseline bundle for slice_id, from cache or disk."""
        if slice_id in self._loaded_baselines:
            return self._loaded_baselines[slice_id]

        owns_db = False
        if db is None:
            db = SessionLocal()
            owns_db = True

        try:
            # Query active baseline from Baseline table
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
                candidates = list(PROCESSED_BASELINES_DIR.glob(f"{slice_id}_*.joblib"))
                if candidates:
                    artifact_path = candidates[0]

            if artifact_path and artifact_path.is_file():
                bundle = joblib.load(artifact_path)
                bundle["baseline_id"] = base_row.id if base_row else (reg_row.id if reg_row else str(uuid.uuid4()))
                self._init_engine_for_bundle(slice_id, bundle)
                self._loaded_baselines[slice_id] = bundle
                return bundle

            # If no baseline found, train baselines
            from ml_engine.baseline.trainer import train_all_baselines
            train_all_baselines(db=db)

            candidates = list(PROCESSED_BASELINES_DIR.glob(f"{slice_id}_*.joblib"))
            if candidates and candidates[0].is_file():
                bundle = joblib.load(candidates[0])
                base_ref = db.query(Baseline).filter(Baseline.slice_id == slice_id).first()
                reg_ref = db.query(BaselineRegistry).filter(BaselineRegistry.slice_id == slice_id).first()
                bundle["baseline_id"] = base_ref.id if base_ref else (reg_ref.id if reg_ref else str(uuid.uuid4()))
                self._init_engine_for_bundle(slice_id, bundle)
                self._loaded_baselines[slice_id] = bundle
                return bundle

            return None
        except Exception as e:
            logger.error("Failed to load baseline bundle for %s: %s", slice_id, e)
            return None
        finally:
            if owns_db:
                db.close()

    def _init_engine_for_bundle(self, slice_id: str, bundle: Dict[str, Any]) -> DetectionEngine:
        """Initialize and cache DetectionEngine instance for a baseline bundle."""
        engine = DetectionEngine(cusum_detector=self._cusum)

        # Register detectors from bundle
        if "detectors" in bundle:
            for name, det in bundle["detectors"].items():
                engine.register_detector(name, det)
        else:
            if "isolation_forest" in bundle:
                engine.register_detector("isolation_forest", bundle["isolation_forest"])
            elif "detector" in bundle:
                engine.register_detector("isolation_forest", bundle["detector"])

            if "autoencoder" in bundle:
                engine.register_detector("autoencoder", bundle["autoencoder"])

        self._engines[slice_id] = engine
        return engine

    def get_engine(self, slice_id: str, bundle: Dict[str, Any]) -> DetectionEngine:
        """Get or create DetectionEngine for slice."""
        if slice_id in self._engines:
            return self._engines[slice_id]
        return self._init_engine_for_bundle(slice_id, bundle)

    def analyze_window(
        self,
        window: Dict[str, Any],
        db: Optional[Session] = None,
    ) -> DetectorOutput:
        """Run multi-model anomaly detection on a single window dictionary and persist results."""
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
                bundle = self._get_anchor_bundle(slice_id)
                if not bundle:
                    raise RuntimeError(f"No active or anchor baseline bundle found for slice '{slice_id}'. Run baseline training first.")

            scaler = bundle["scaler"]
            threshold_params = bundle.get("threshold_params", {})
            threshold_pct = float(threshold_params.get("threshold_percentile", 95.0))

            engine = self.get_engine(slice_id, bundle)

            # Transform ratio features
            scaled_vector = scaler.transform_vector(ratios)
            x_row = np.array([[scaled_vector[f] for f in FEATURE_NAMES]], dtype=np.float32)

            # Multi-model evaluation via DetectionEngine
            eval_result = engine.evaluate_vector(
                x=x_row,
                slice_id=slice_id,
                threshold_percentile=threshold_pct,
            )

            if_data = eval_result["isolation_forest"]
            ae_data = eval_result["autoencoder"]
            fusion_data = eval_result["fusion"]
            cusum_data = eval_result["cusum"]

            fused_score = fusion_data["fused_percentile"]
            is_anomalous = fusion_data["is_anomalous"]
            cusum_is_alarm = cusum_data["is_alarm"]

            # Alert fires when fused score crosses threshold OR CUSUM triggers
            should_alert = bool(is_anomalous or cusum_is_alarm)

            output = DetectorOutput(
                window_id=window_id,
                slice_id=slice_id,
                nf_id=nf_id,
                evaluated_at=datetime.now(timezone.utc),
                baseline_version=bundle.get("version", "v1.0.0-anchor"),
                isolation_forest=IsolationForestScore(
                    raw_score_negated=if_data["raw_score_negated"],
                    benign_percentile=if_data["benign_percentile"],
                    threshold_percentile=if_data["threshold_percentile"],
                    is_flagged=if_data["is_flagged"],
                ),
                autoencoder=AutoencoderScore(
                    reconstruction_mse=ae_data["reconstruction_mse"],
                    benign_percentile=ae_data["benign_percentile"],
                    threshold_percentile=ae_data["threshold_percentile"],
                    is_flagged=ae_data["is_flagged"],
                ),
                fusion=FusionScore(
                    primary_rule=fusion_data["primary_rule"],
                    fused_percentile=fused_score,
                    secondary_mean_percentile=fusion_data["secondary_mean_percentile"],
                    agreement_state=fusion_data["agreement_state"],
                    is_anomalous=is_anomalous,
                ),
                cusum=CusumScore(
                    accumulated_statistic=cusum_data["accumulated_statistic"],
                    alarm_threshold=cusum_data["alarm_threshold"],
                    is_alarm=cusum_is_alarm,
                    status=cusum_data["status"],
                ),
            )

            # 1. Write to anomaly_alerts if should_alert
            if should_alert:
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
                        if_score=round(if_data["raw_score_negated"], 4),
                        if_percentile=round(if_data["benign_percentile"], 4),
                        ae_recon_error=round(ae_data["reconstruction_mse"], 4),
                        ae_percentile=round(ae_data["benign_percentile"], 4),
                        fused_percentile=round(fused_score, 4),
                        cusum_score=round(cusum_data["accumulated_statistic"], 4),
                        agreement_state=fusion_data["agreement_state"],
                        is_anomalous=should_alert,
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
# CommShield AI Core
