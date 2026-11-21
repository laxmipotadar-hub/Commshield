"""Per-Device Behavior Model and Split Conformal Abstention Package."""

from .isolation_forest import DeviceIsolationForest
from .conformal import (
    DEFAULT_ALPHA_LOW,
    DEFAULT_ALPHA_HIGH,
    compute_conformal_pvalue,
    evaluate_device_verdict,
)
from .trainer import (
    DeviceModelManager,
    extract_device_features,
    HELD_OUT_CLASS,
    TRAINED_CLASSES,
    FEATURE_NAMES,
)

__all__ = [
    "DeviceIsolationForest",
    "DEFAULT_ALPHA_LOW",
    "DEFAULT_ALPHA_HIGH",
    "compute_conformal_pvalue",
    "evaluate_device_verdict",
    "DeviceModelManager",
    "extract_device_features",
    "HELD_OUT_CLASS",
    "TRAINED_CLASSES",
    "FEATURE_NAMES",
]
