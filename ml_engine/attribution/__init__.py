"""Drift attribution package for CommShield."""

from .base import BaseAttributor, AttributionEngine
from .adwin import ADWIN, AdwinSliceTracker
from .config import (
    AbstainReason,
    AttributionConfig,
    AttributionVerdict,
    DEFAULT_ATTRIBUTION_CONFIG,
    RecommendedAction,
)
from .metrics import (
    compute_jsd,
    compute_volume_multiplier,
    evaluate_per_ue_rate,
    evaluate_proportional_growth,
    evaluate_threat_indicators,
)
from .rule_based import RuleBasedAttributor

__all__ = [
    "BaseAttributor",
    "AttributionEngine",
    "ADWIN",
    "AdwinSliceTracker",
    "AbstainReason",
    "AttributionConfig",
    "AttributionVerdict",
    "DEFAULT_ATTRIBUTION_CONFIG",
    "RecommendedAction",
    "compute_jsd",
    "compute_volume_multiplier",
    "evaluate_per_ue_rate",
    "evaluate_proportional_growth",
    "evaluate_threat_indicators",
    "RuleBasedAttributor",
]
