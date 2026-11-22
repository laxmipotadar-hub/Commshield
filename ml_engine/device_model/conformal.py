"""Split Conformal Calibration and Principled Abstention for Per-Device Anomaly Detection."""

from typing import Any, Dict, List, Optional, Tuple, Union

# Frozen conformal thresholds pre-registered on tuning seeds
DEFAULT_ALPHA_LOW: float = 0.05
DEFAULT_ALPHA_HIGH: float = 0.20


def compute_conformal_pvalue(
    test_score: float,
    calibration_scores: List[float],
) -> float:
    """Compute split-conformal p-value using the standard rule with exact (n+1) correction.
    
    Formula:
        p = (1 + sum(I(s_i >= s_test))) / (n + 1)
        
    Under exchangeability between calibration set and test instance:
    - If s_test > max(s_i), p = 1 / (n + 1)
    - If s_test <= min(s_i), p = (n + 1) / (n + 1) = 1.0
    
    Args:
        test_score: Anomaly/nonconformity score of test device window.
        calibration_scores: Calibration scores on benign holdout windows.
        
    Returns:
        float: Conformal p-value in [0.0, 1.0].
    """
    n = len(calibration_scores)
    if n == 0:
        return 0.5

    # Count calibration instances at least as extreme as test_score
    extreme_count = sum(1 for s in calibration_scores if s >= test_score)
    p_val = float(1 + extreme_count) / float(n + 1)
    return round(max(0.0, min(1.0, p_val)), 6)


def evaluate_device_verdict(
    p_value: float,
    is_held_out: bool = False,
    alpha_low: float = DEFAULT_ALPHA_LOW,
    alpha_high: float = DEFAULT_ALPHA_HIGH,
) -> Tuple[str, Optional[str]]:
    """Determine verdict for a device window with frozen gray-band abstention.
    
    Returns:
        Tuple of (verdict, abstain_reason):
        - ("uncertain", "held_out_device_class") if device class was held out from training.
        - ("anomalous", None) if p_value < alpha_low (reject null H0 of normal behavior).
        - ("normal", None) if p_value > alpha_high (retain null H0).
        - ("uncertain", "conformal_gray_band") if alpha_low <= p_value <= alpha_high.
    """
    if is_held_out:
        return "uncertain", "held_out_device_class"

    if p_value < alpha_low:
        return "anomalous", None
    elif p_value > alpha_high:
        return "normal", None
    else:
        return "uncertain", "conformal_gray_band"
# CommShield AI Core
