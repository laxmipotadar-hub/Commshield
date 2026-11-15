"""Detection engine package for CommShield."""

from .base import BaseDetector
from .config import DEFAULT_DETECTION_CONFIG, DetectionConfig
from .isolation_forest import IsolationForestDetector
from .autoencoder import AutoencoderDetector
from .cusum import CusumDetector
from .fusion import compute_agreement, fuse_scores, to_contract_agreement
from .engine import DetectionEngine

__all__ = [
    "BaseDetector",
    "DEFAULT_DETECTION_CONFIG",
    "DetectionConfig",
    "IsolationForestDetector",
    "AutoencoderDetector",
    "CusumDetector",
    "compute_agreement",
    "fuse_scores",
    "to_contract_agreement",
    "DetectionEngine",
]
