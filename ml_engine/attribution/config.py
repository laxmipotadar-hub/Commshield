"""Attribution configuration and threshold parameters for CommShield.

All thresholds, limits, and tolerances are centralized here with documented rationales.
No attribution thresholds should be hard-coded inline.
"""

from dataclasses import dataclass
from enum import Enum


class AbstainReason(str, Enum):
    """Fixed enumeration of named abstention reasons when attribution is uncertain."""
    VOLUME_COMPOSITION_DISAGREE = "volume_composition_disagree"
    INSUFFICIENT_WINDOWS = "insufficient_windows"
    INDICATOR_CONFLICT = "indicator_conflict"
    MIMICRY_SUSPECTED = "mimicry_suspected"
    DETECTORS_DISAGREE = "detectors_disagree"
    INCONCLUSIVE_GROWTH_PATTERN = "inconclusive_growth_pattern"


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


DEFAULT_ATTRIBUTION_CONFIG = AttributionConfig()
