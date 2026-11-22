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
    CONFORMAL_GRAY_BAND = "conformal_gray_band"
    DETECTOR_PVALUE_DISAGREEMENT = "detector_pvalue_disagreement"
    GROWTH_EXCEEDS_APPROVED_BATCH = "growth_exceeds_approved_batch"
    DEVICE_BEHAVIOUR_UNCERTAIN = "device_behaviour_uncertain"
    PARTIAL_EVENT_MATCH = "partial_event_match"
    UNPROVISIONED_DEVICES_PRESENT = "unprovisioned_devices_present"


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
    adwin_delta: float = 0.002
    adwin_min_window_length: int = 5

    # 2. Volume Multiplier Thresholds
    volume_growth_min_k: float = 1.15
    volume_drop_max_k: float = 0.70

    # 3. Proportional-Growth & Composition Test Thresholds
    jsd_null_threshold_99th: float = 0.0350
    jsd_pseudo_count: float = 1e-5
    proportionality_tolerance: float = 0.35

    # 4. Per-UE Rate Comparison Thresholds
    per_ue_rate_stable_tolerance: float = 0.25
    per_ue_rate_jump_ratio: float = 1.50

    # 5. Threat Indicator Cutoffs
    nas_failure_ratio_threshold: float = 0.010
    pfcp_failure_ratio_threshold: float = 0.010
    ue_entropy_drop_threshold: float = -1.00
    new_ue_rate_threshold: float = 0.035

    # 6. Minimum History Requirement
    min_windows_required: int = 3

    # 7. Attributor Selection Flag ("rules" | "learned")
    attributor_type: str = "rules"

    # 8. Split Conformal Calibration Parameters
    conformal_enabled: bool = True
    conformal_alpha_low: float = 0.05
    conformal_alpha_high: float = 0.20
    conformal_detector_disagreement_margin: float = 0.35
    conformal_min_calibration_size: int = 30
    conformal_pooling_fallback: bool = True

    # 9. Device & Provisioning Evidence Parameters
    device_evidence_enabled: bool = False
    min_provisioned_share: float = 0.95
    max_anomalous_share: float = 0.10
    max_uncertain_share: float = 0.30
    volume_batch_tolerance: float = 1.25


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
    sequential_window_length: int = 3
    attack_decision_threshold: float = 0.60
    benign_decision_threshold: float = 0.40
    feature_names: List[str] = field(
        default_factory=lambda: list(LEARNED_ATTRIBUTION_FEATURES)
    )


DEFAULT_LEARNED_ATTRIBUTION_CONFIG = LearnedAttributionConfig()


@dataclass
class ConformalAttributionConfig:
    """Pre-registered, frozen parameters for split conformal calibration and abstention.

    Tuned on tuning streams and frozen:
    - alpha_low: 0.05 (rejection of null / benign hypothesis -> likely attack)
    - alpha_high: 0.20 (acceptance of null / benign hypothesis -> likely benign)
    - gray band: [alpha_low, alpha_high] -> abstain as uncertain
    - detector_disagreement_margin: 0.35 -> abstain if |p_IF - p_AE| > margin
    - min_calibration_size: 30 -> fallback to pooled calibration if per-slice count is less
    - pooling_fallback: True -> pool calibration scores across slices when slice count is deficient
    """
    enabled: bool = True
    alpha_low: float = 0.05
    alpha_high: float = 0.20
    detector_disagreement_margin: float = 0.35
    min_calibration_size: int = 30
    pooling_fallback: bool = True


DEFAULT_CONFORMAL_CONFIG = ConformalAttributionConfig()
# CommShield AI Core
