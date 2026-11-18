"""Drift attribution package for CommShield."""

from .base import BaseAttributor, AttributionEngine
from .adwin import ADWIN, AdwinSliceTracker
from .config import (
    AbstainReason,
    AttributionConfig,
    AttributionVerdict,
    DEFAULT_ATTRIBUTION_CONFIG,
    DEFAULT_LEARNED_ATTRIBUTION_CONFIG,
    LEARNED_ATTRIBUTION_FEATURES,
    LearnedAttributionConfig,
    RecommendedAction,
)
from .learned import (
    LearnedAttributor,
    SmallRegularizedAttributionModel,
    extract_attribution_features,
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
    "DEFAULT_LEARNED_ATTRIBUTION_CONFIG",
    "LEARNED_ATTRIBUTION_FEATURES",
    "LearnedAttributionConfig",
    "RecommendedAction",
    "LearnedAttributor",
    "SmallRegularizedAttributionModel",
    "extract_attribution_features",
    "compute_jsd",
    "compute_volume_multiplier",
    "evaluate_per_ue_rate",
    "evaluate_proportional_growth",
    "evaluate_threat_indicators",
    "RuleBasedAttributor",
]
