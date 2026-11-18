"""Attribution configuration and threshold parameters for CommShield.

All thresholds, limits, and tolerances are centralized here with documented rationales.
No attribution thresholds should be hard-coded inline.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List


class AbstainReason(str, Enum):
    """Fixed enumeration of named abstention reasons when attribution is uncertain."""
    VOLUME_COMPOSITION_DISAGREE = "volume_composition_disagree"
    INSUFFICIENT_WINDOWS = "insufficient_windows"
    INDICATOR_CONFLICT = "indicator_conflict"
    MIMICRY_SUSPECTED = "mimicry_suspected"
    DETECTORS_DISAGREE = "detectors_disagree"
    INCONCLUSIVE_GROWTH_PATTERN = "inconclusive_growth_pattern"
    UNCERTAIN_CONFIDENCE = "uncertain_confidence"


class AttributionVerdict(str, Enum):
    """Attribution classification outcome."""
    LIKELY_BENIGN = "likely_benign"
    LIKELY_ATTACK = "likely_attack"
    UNCERTAIN = "uncertain"


class RecommendedAction(str, Enum):
    """Operational action recommended by the attribution engine."""
    ADAPT_CANDIDATE = "adapt_candidate"
    ALERT = "alert"
    QUARANTINE = "quarantine"


@dataclass
class AttributionConfig:
    """Thresholds and parameters governing drift detection and attribution evidence tests."""

    # 1. ADWIN Drift Detection Parameters
    # Significance delta for Hoeffding cut in ADWIN drift detection on volume stream
    adwin_delta: float = 0.002
    # Minimum observations before ADWIN evaluates splits
    adwin_min_window_length: int = 5

    # 2. Volume Multiplier Thresholds
    # Minimum volume multiplier (k) above active baseline to qualify as traffic growth
    volume_growth_min_k: float = 1.15
    # Volume drop multiplier below which abnormal traffic contraction is flagged
    volume_drop_max_k: float = 0.70

    # 3. Proportional-Growth & Composition Test Thresholds
    # Maximum Jensen-Shannon Divergence allowed between current composition and baseline (99th percentile null)
    jsd_null_threshold_99th: float = 0.0350
    # Pseudo-count smoothing added to zero-probability categories prior to computing KL divergence
    jsd_pseudo_count: float = 1e-5
    # Relative tolerance on per-category volume scaling factors vs overall scaling factor k
    proportionality_tolerance: float = 0.35

    # 4. Per-UE Rate Comparison Thresholds
    # Allowed relative deviation of per-device rates (|rate/baseline_rate - 1.0|) to be considered stable growth
    per_ue_rate_stable_tolerance: float = 0.25
    # Jump ratio above baseline per-device rate indicating anomalous individual device activity rather than user growth
    per_ue_rate_jump_ratio: float = 1.50

    # 5. Threat Indicator Cutoffs
    # Maximum acceptable NAS signalling failure ratio before flagging signaling distress
    nas_failure_ratio_threshold: float = 0.010
    # Maximum acceptable PFCP session failure ratio
    pfcp_failure_ratio_threshold: float = 0.010
    # Negative shift in UE hash entropy indicating device concentration / flood
    ue_entropy_drop_threshold: float = -1.00
    # Elevated new-device arrival rate threshold
    new_ue_rate_threshold: float = 0.035

    # 6. Minimum History Requirement
    # Minimum number of recent observed windows required for confident attribution
    min_windows_required: int = 3

    # 7. Attributor Selection Flag ("rules" | "learned")
    attributor_type: str = "rules"


DEFAULT_ATTRIBUTION_CONFIG = AttributionConfig()

# Canonical ordered feature list matching attribution signals from docs/AI_FEASIBILITY.md
# No raw identifiers, no labels of any kind
LEARNED_ATTRIBUTION_FEATURES: List[str] = [
    "scaling_factor_k",
    "jsd_divergence",
    "ue_entropy_delta",
    "new_ue_rate",
    "nas_failure_ratio",
    "pfcp_failure_ratio",
    "detector_agreement_numeric",
    "control_slice_concordant",
    "per_ue_rate_deviation",
]


@dataclass
class LearnedAttributionConfig:
    """Pre-registered configuration for the learned attributor with sequential evidence accumulation.
    
    Documented Rationale:
    Model is regularized and intentionally small (linear/logistic, 9 weights + 1 intercept)
    because, as proven in docs/AI_FEASIBILITY.md, network drift telemetry provides very few
    distinct episodes of growth and stealth attacks. A high-parameter model would easily overfit
    to transient noise or diurnal patterns in the single synthetic growth episode. Fixed seed ensures determinism.
    """
    model_type: str = "logistic_regression"
    regularization_l2: float = 0.5
    random_seed: int = 42
    # Accumulate evidence over N windows chosen on tuning streams before issuing verdict
    sequential_window_length: int = 3
    # Calibrated decision cutoffs for binary classification (0 = benign_growth, 1 = attack)
    attack_decision_threshold: float = 0.60
    benign_decision_threshold: float = 0.40
    feature_names: List[str] = field(default_factory=lambda: list(LEARNED_ATTRIBUTION_FEATURES))


DEFAULT_LEARNED_ATTRIBUTION_CONFIG = LearnedAttributionConfig()

