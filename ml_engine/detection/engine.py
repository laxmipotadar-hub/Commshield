"""Extensible DetectionEngine orchestrating multi-model execution, fusion, and CUSUM tracking."""

from typing import Any, Dict, List, Optional
import numpy as np

from .base import BaseDetector
from .config import DEFAULT_DETECTION_CONFIG
from .cusum import CusumDetector
from .fusion import fuse_scores


class DetectionEngine:
    """Orchestrates registered anomaly detectors without requiring callers to change."""

    def __init__(
        self,
        detectors: Optional[Dict[str, BaseDetector]] = None,
        cusum_detector: Optional[CusumDetector] = None,
    ):
        self.detectors: Dict[str, BaseDetector] = detectors or {}
        self.cusum: CusumDetector = cusum_detector or CusumDetector()

    def register_detector(self, name: str, detector: BaseDetector) -> None:
        """Register a new detector under a given name (e.g. 'isolation_forest', 'autoencoder')."""
        self.detectors[name] = detector

    def get_detector(self, name: str) -> Optional[BaseDetector]:
        """Retrieve a registered detector by name."""
        return self.detectors.get(name)

    def evaluate_vector(
        self,
        x: np.ndarray,
        slice_id: str = "sst-1-sd-010203",
        threshold_percentile: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Evaluate a scaled feature sample against all registered detectors.
        
        Args:
            x: 2D numpy array of shape (1, n_features) or 1D array of shape (n_features,).
            slice_id: S-NSSAI slice identifier for per-slice CUSUM accumulation.
            threshold_percentile: Optional threshold override.
            
        Returns:
            Dict containing individual detector scores, fused scores, agreement, and CUSUM.
        """
        if x.ndim == 1:
            x = x.reshape(1, -1)

        cfg = DEFAULT_DETECTION_CONFIG
        thresh = threshold_percentile if threshold_percentile is not None else cfg.threshold_percentile

        detector_results: Dict[str, Dict[str, Any]] = {}

        for name, det in self.detectors.items():
            if hasattr(det, "evaluate_sample"):
                raw, pct, flagged = det.evaluate_sample(x)
            else:
                raw = float(det.score(x)[0])
                pct = det.score_percentile(raw)
                flagged = bool(pct >= thresh)
            detector_results[name] = {
                "raw_score": raw,
                "percentile": pct,
                "is_flagged": flagged,
            }

        # Extract Isolation Forest scores
        if_res = detector_results.get("isolation_forest", {"raw_score": 0.0, "percentile": 50.0, "is_flagged": False})
        # Extract Autoencoder scores
        ae_res = detector_results.get("autoencoder", {"raw_score": 0.0, "percentile": 50.0, "is_flagged": False})

        # Fusion
        fusion_res = fuse_scores(
            if_percentile=if_res["percentile"],
            ae_percentile=ae_res["percentile"],
            threshold_percentile=thresh,
            primary_rule=cfg.primary_fusion_rule,
        )

        # CUSUM accumulation per slice
        cusum_stat, cusum_alarm, cusum_status = self.cusum.update(
            slice_id=slice_id,
            fused_score=fusion_res["fused_percentile"],
        )

        return {
            "isolation_forest": {
                "raw_score_negated": round(if_res["raw_score"], 4),
                "benign_percentile": round(if_res["percentile"], 4),
                "threshold_percentile": round(thresh, 4),
                "is_flagged": if_res["is_flagged"],
            },
            "autoencoder": {
                "reconstruction_mse": round(ae_res["raw_score"], 4),
                "benign_percentile": round(ae_res["percentile"], 4),
                "threshold_percentile": round(thresh, 4),
                "is_flagged": ae_res["is_flagged"],
            },
            "fusion": fusion_res,
            "cusum": {
                "accumulated_statistic": cusum_stat,
                "alarm_threshold": self.cusum.alarm_threshold,
                "is_alarm": cusum_alarm,
                "status": cusum_status,
            },
            "all_detectors": detector_results,
        }
