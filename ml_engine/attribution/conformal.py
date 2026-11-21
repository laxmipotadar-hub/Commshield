"""Split Conformal Calibration and Principled Abstention for Drift Attribution.

Implements:
1. Standard split-conformal p-value computation with the exact (n+1) correction.
2. Per-slice calibration scoring for Isolation Forest, Autoencoder, and Learned Attributor.
3. Pooled slice fallback when per-slice benign calibration sample size < min_calibration_size (30).
4. Frozen dual-condition abstention rule:
   - Conformal gray band: p-value falls in [alpha_low, alpha_high] ([0.05, 0.20]).
   - Detector p-value disagreement: |p_IF - p_AE| > margin (0.35).
5. Audit verification guaranteeing calibration windows are strictly disjoint from training
   and threshold-setting windows.
"""

from dataclasses import dataclass, field
import logging
from typing import Any, Dict, List, Optional, Set, Tuple, Union
import numpy as np

from ml_engine.attribution.config import (
    DEFAULT_CONFORMAL_CONFIG,
    AbstainReason,
    ConformalAttributionConfig,
)

logger = logging.getLogger("commshield.conformal")


def compute_conformal_pvalue(
    test_score: float,
    calibration_scores: Union[List[float], np.ndarray],
) -> float:
    """Compute conformal p-value using the standard split-conformal rule with (n+1) correction.

    Formula:
        p = (1 + sum(I(s_i >= s_test))) / (n + 1)

    Under the null hypothesis H0 (test instance belongs to the benign reference distribution):
    - Higher scores s indicate greater divergence / anomaly.
    - If s_test > max(s_i), p = 1 / (n + 1).
    - If s_test <= min(s_i), p = (n + 1) / (n + 1) = 1.0.
    - Under exchangeability, p is sub-uniformly distributed on [0, 1].

    Args:
        test_score: Nonconformity score of the test instance.
        calibration_scores: 1D array or list of benign calibration nonconformity scores.

    Returns:
        float: Conformal p-value rounded to 6 decimal places.
    """
    scores = np.asarray(calibration_scores, dtype=np.float64)
    n = len(scores)
    if n == 0:
        logger.warning("Empty calibration scores passed to compute_conformal_pvalue; returning fallback 0.5")
        return 0.5

    # Count calibration scores greater than or equal to test_score
    extreme_count = np.sum(scores >= float(test_score))
    p_value = float(1.0 + extreme_count) / float(n + 1)
    return float(np.clip(round(p_value, 6), 0.0, 1.0))


def evaluate_conformal_abstention(
    p_if: float,
    p_ae: float,
    p_attr: float,
    config: Optional[ConformalAttributionConfig] = None,
) -> Tuple[bool, Optional[str], Dict[str, Any]]:
    """Evaluate conformal abstention rules against frozen thresholds.

    Abstains when:
    1. Attributor p-value falls in the gray band [alpha_low, alpha_high] (e.g. [0.05, 0.20]).
    2. Detector p-values disagree by more than detector_disagreement_margin (e.g. |p_IF - p_AE| > 0.35).

    Returns:
        Tuple of:
        - should_abstain (bool)
        - abstain_reason (str or None)
        - diagnostic_details (dict)
    """
    cfg = config or DEFAULT_CONFORMAL_CONFIG

    # Check 1: Conformal gray band
    in_gray_band = bool(cfg.alpha_low <= p_attr <= cfg.alpha_high)

    # Check 2: Detector p-value disagreement
    detector_diff = float(abs(p_if - p_ae))
    detector_disagreed = bool(detector_diff > cfg.detector_disagreement_margin)

    should_abstain = in_gray_band or detector_disagreed

    # Prioritize reasons: gray band takes precedence if both fire, otherwise disagreement
    abstain_reason: Optional[str] = None
    if in_gray_band:
        abstain_reason = AbstainReason.CONFORMAL_GRAY_BAND.value
    elif detector_disagreed:
        abstain_reason = AbstainReason.DETECTOR_PVALUE_DISAGREEMENT.value

    details = {
        "p_value_isolation_forest": round(p_if, 4),
        "p_value_autoencoder": round(p_ae, 4),
        "p_value_attributor": round(p_attr, 4),
        "detector_pvalue_diff": round(detector_diff, 4),
        "gray_band": [cfg.alpha_low, cfg.alpha_high],
        "gray_band_triggered": in_gray_band,
        "detector_disagreement_margin": cfg.detector_disagreement_margin,
        "detector_disagreement_triggered": detector_disagreed,
        "conformal_abstain_triggered": should_abstain,
    }

    return should_abstain, abstain_reason, details


@dataclass
class CalibrationSliceBundle:
    """Stores calibration nonconformity scores and provenance metadata for a slice."""
    slice_id: str
    window_ids: List[str]
    if_scores: np.ndarray
    ae_scores: np.ndarray
    attr_scores: np.ndarray
    size: int
    is_pooled: bool = False
    fallback_reason: Optional[str] = None

    def smallest_achievable_pvalue(self) -> float:
        """Returns the minimum achievable p-value: 1 / (n + 1)."""
        return 1.0 / float(self.size + 1) if self.size > 0 else 1.0


class ConformalCalibrationManager:
    """Manages per-slice benign calibration bundles and coordinates split-conformal scoring."""

    def __init__(self, config: Optional[ConformalAttributionConfig] = None):
        self.config = config or DEFAULT_CONFORMAL_CONFIG
        self.slice_bundles: Dict[str, CalibrationSliceBundle] = {}
        self.global_pooled_bundle: Optional[CalibrationSliceBundle] = None
        self._training_window_ids: Set[str] = set()
        self._threshold_window_ids: Set[str] = set()

    def register_known_partition_ids(
        self,
        training_ids: Set[str],
        threshold_ids: Set[str],
    ) -> None:
        """Register IDs of windows used for training and threshold-setting to ensure disjointness."""
        self._training_window_ids.update(training_ids)
        self._threshold_window_ids.update(threshold_ids)

    def register_calibration_bundle(
        self,
        slice_id: str,
        calibration_window_ids: List[str],
        if_scores: np.ndarray,
        ae_scores: np.ndarray,
        attr_scores: np.ndarray,
        allow_pooling: bool = True,
    ) -> CalibrationSliceBundle:
        """Register calibration nonconformity scores for a network slice.

        Validates disjointness against training and threshold-setting windows.
        """
        cal_id_set = set(calibration_window_ids)
        # Verify strict disjointness
        overlap_train = cal_id_set.intersection(self._training_window_ids)
        if overlap_train:
            raise ValueError(f"Calibration windows overlap with training windows: {len(overlap_train)} overlapping IDs")
        overlap_thresh = cal_id_set.intersection(self._threshold_window_ids)
        if overlap_thresh:
            raise ValueError(f"Calibration windows overlap with threshold-setting windows: {len(overlap_thresh)} overlapping IDs")

        n = len(calibration_window_ids)
        is_pooled = False
        fallback_msg = None

        if n < self.config.min_calibration_size and allow_pooling:
            is_pooled = True
            fallback_msg = (
                f"Slice '{slice_id}' contains {n} calibration windows (< {self.config.min_calibration_size}); "
                "pooled global calibration fallback applied."
            )
            logger.info(fallback_msg)

        bundle = CalibrationSliceBundle(
            slice_id=slice_id,
            window_ids=list(calibration_window_ids),
            if_scores=np.asarray(if_scores, dtype=np.float64),
            ae_scores=np.asarray(ae_scores, dtype=np.float64),
            attr_scores=np.asarray(attr_scores, dtype=np.float64),
            size=n,
            is_pooled=is_pooled,
            fallback_reason=fallback_msg,
        )

        self.slice_bundles[slice_id] = bundle
        return bundle

    def set_global_pooled_fallback(
        self,
        window_ids: List[str],
        if_scores: np.ndarray,
        ae_scores: np.ndarray,
        attr_scores: np.ndarray,
    ) -> CalibrationSliceBundle:
        """Configure pooled global calibration bundle used when slice-specific calibration is deficient."""
        self.global_pooled_bundle = CalibrationSliceBundle(
            slice_id="GLOBAL_POOLED",
            window_ids=list(window_ids),
            if_scores=np.asarray(if_scores, dtype=np.float64),
            ae_scores=np.asarray(ae_scores, dtype=np.float64),
            attr_scores=np.asarray(attr_scores, dtype=np.float64),
            size=len(window_ids),
            is_pooled=True,
            fallback_reason="Pooled across multiple slices to satisfy minimum calibration size requirement.",
        )
        return self.global_pooled_bundle

    def get_bundle_for_slice(self, slice_id: str) -> CalibrationSliceBundle:
        """Retrieve calibration bundle for slice_id, falling back to pooled bundle if deficient."""
        bundle = self.slice_bundles.get(slice_id)
        if bundle is not None and not bundle.is_pooled:
            return bundle

        # Fallback to pooled if available
        if self.global_pooled_bundle is not None:
            return self.global_pooled_bundle

        if bundle is not None:
            return bundle

        # Synthesize fallback if no calibration registered
        logger.warning("No calibration bundle found for slice %s; creating empty fallback", slice_id)
        return CalibrationSliceBundle(
            slice_id=slice_id,
            window_ids=[],
            if_scores=np.array([0.5], dtype=np.float64),
            ae_scores=np.array([0.5], dtype=np.float64),
            attr_scores=np.array([0.5], dtype=np.float64),
            size=1,
            is_pooled=True,
            fallback_reason="Uncalibrated slice: synthetic fallback calibration used.",
        )

    def evaluate_scores(
        self,
        slice_id: str,
        test_if_score: float,
        test_ae_score: float,
        test_attr_score: float,
        config: Optional[ConformalAttributionConfig] = None,
    ) -> Dict[str, Any]:
        """Compute conformal p-values and evaluate abstention for given test scores."""
        cfg = config or self.config
        bundle = self.get_bundle_for_slice(slice_id)

        p_if = compute_conformal_pvalue(test_if_score, bundle.if_scores)
        p_ae = compute_conformal_pvalue(test_ae_score, bundle.ae_scores)
        p_attr = compute_conformal_pvalue(test_attr_score, bundle.attr_scores)

        should_abstain, abstain_reason, details = evaluate_conformal_abstention(
            p_if=p_if,
            p_ae=p_ae,
            p_attr=p_attr,
            config=cfg,
        )

        details.update({
            "slice_id": slice_id,
            "calibration_size": bundle.size,
            "smallest_possible_pvalue": round(bundle.smallest_achievable_pvalue(), 6),
            "is_pooled_calibration": bundle.is_pooled,
            "calibration_fallback_reason": bundle.fallback_reason,
        })

        return {
            "p_value_isolation_forest": p_if,
            "p_value_autoencoder": p_ae,
            "p_value_attributor": p_attr,
            "should_abstain": should_abstain,
            "abstain_reason": abstain_reason,
            "details": details,
        }

