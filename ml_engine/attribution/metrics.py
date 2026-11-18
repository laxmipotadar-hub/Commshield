"""Attribution evidence metrics: volume scaling, JSD composition divergence, per-UE rates, and threat signals."""

import math
from typing import Any, Dict, List, Optional, Tuple
import numpy as np

from .config import DEFAULT_ATTRIBUTION_CONFIG


def compute_jsd(
    p_dict: Dict[str, float],
    q_dict: Dict[str, float],
    pseudo_count: float = 1e-5,
) -> float:
    """Compute Jensen-Shannon Divergence between two normalized composition dictionaries.
    
    Applies pseudo-count smoothing and normalizes distributions.
    
    Returns:
        JSD score in [0.0, 1.0].
    """
    keys = sorted(set(p_dict.keys()) | set(q_dict.keys()))
    if not keys:
        return 0.0

    p_raw = np.array([max(0.0, float(p_dict.get(k, 0.0))) + pseudo_count for k in keys], dtype=np.float64)
    q_raw = np.array([max(0.0, float(q_dict.get(k, 0.0))) + pseudo_count for k in keys], dtype=np.float64)

    p = p_raw / np.sum(p_raw)
    q = q_raw / np.sum(q_raw)
    m = 0.5 * (p + q)

    # KL divergences with base e
    kl_pm = np.sum(p * np.log(p / m))
    kl_qm = np.sum(q * np.log(q / m))
    jsd = 0.5 * (kl_pm + kl_qm)

    return float(np.clip(round(jsd, 5), 0.0, 1.0))


def compute_volume_multiplier(
    current_counters: Dict[str, Any],
    baseline_bundle: Dict[str, Any],
) -> float:
    """Calculate volume scaling factor k vs baseline training reference."""
    cur_up = current_counters.get("total_bytes_uplink", 0)
    cur_down = current_counters.get("total_bytes_downlink", 0)
    cur_vol = float(cur_up + cur_down)

    # Retrieve baseline reference volume from scaler params or training stats
    scaler_params = baseline_bundle.get("scaler_params", {})
    feature_schema = baseline_bundle.get("feature_schema", {})
    medians = scaler_params.get("medians", {})

    base_vol = float(baseline_bundle.get("mean_volume_bytes", 0.0))
    if base_vol <= 0.0:
        # Default benign reference ~1.03 GB per 60s window (approx 1,036,558,000 bytes)
        base_vol = 1_036_558_000.0

    k = cur_vol / max(1.0, base_vol)
    return float(round(k, 3))


def evaluate_proportional_growth(
    current_composition: Dict[str, float],
    baseline_composition: Dict[str, float],
    scaling_factor_k: float,
    jsd_null_threshold: Optional[float] = None,
    pseudo_count: Optional[float] = None,
) -> Dict[str, Any]:
    """Execute proportional-growth test comparing composition against benign reference."""
    cfg = DEFAULT_ATTRIBUTION_CONFIG
    thresh = jsd_null_threshold or cfg.jsd_null_threshold_99th
    pseudo = pseudo_count or cfg.jsd_pseudo_count

    jsd = compute_jsd(current_composition, baseline_composition, pseudo_count=pseudo)
    passed = bool(jsd <= thresh)

    return {
        "scaling_factor_k": scaling_factor_k,
        "jsd_divergence": round(jsd, 4),
        "jsd_null_threshold_99th": round(thresh, 4),
        "passed": passed,
    }


def evaluate_per_ue_rate(
    current_ratios: Dict[str, float],
    baseline_bundle: Dict[str, Any],
) -> Dict[str, Any]:
    """Compare per-device rate distributions to differentiate organic growth from device flood."""
    cfg = DEFAULT_ATTRIBUTION_CONFIG
    cur_pdu_rate = float(current_ratios.get("pdu_session_rate_per_ue", 1.0))
    scaler_params = baseline_bundle.get("scaler_params", {})
    medians = scaler_params.get("medians", {})
    base_pdu_rate = float(medians.get("pdu_session_rate_per_ue", 1.0))

    ratio_dev = abs(cur_pdu_rate / max(0.001, base_pdu_rate) - 1.0)
    is_stable = bool(ratio_dev <= cfg.per_ue_rate_stable_tolerance)
    is_jumped = bool(cur_pdu_rate / max(0.001, base_pdu_rate) >= cfg.per_ue_rate_jump_ratio)

    return {
        "current_rate": round(cur_pdu_rate, 4),
        "baseline_rate": round(base_pdu_rate, 4),
        "deviation_ratio": round(ratio_dev, 4),
        "is_stable": is_stable,
        "is_jumped": is_jumped,
    }


def compute_control_slice_concordance(
    slice1_window: Dict[str, Any],
    slice2_window: Optional[Dict[str, Any]],
    jsd_threshold: float = 0.05,
    rate_tolerance: float = 0.35,
) -> Optional[bool]:
    """Compute concordance between slice 1 and control slice 2 using proportional growth measure.
    
    Returns:
        True: Slice 2 composition and volume move together with slice 1 (network-wide shift).
        False: Localized shift in slice 1, slice 2 composition or scaling deviates.
        None: Second-slice data is unavailable for this scenario/window.
    """
    if not slice2_window:
        return None

    c1 = slice1_window.get("composition_vector", {})
    c2 = slice2_window.get("composition_vector", {})
    if not c1 or not c2:
        return None

    # 1. Compare composition divergence between slices
    jsd = compute_jsd(c1, c2)

    # 2. Compare per-UE session rate deviation between slices
    r1 = float(slice1_window.get("ratio_features", {}).get("pdu_session_rate_per_ue", 1.0))
    r2 = float(slice2_window.get("ratio_features", {}).get("pdu_session_rate_per_ue", 1.0))
    rate_dev = abs(r1 - r2) / max(0.1, r1)

    # Both slices moving together in composition and session rate
    is_concordant = bool(jsd <= jsd_threshold and rate_dev <= rate_tolerance)
    return is_concordant


def evaluate_threat_indicators(
    current_ratios: Dict[str, float],
    baseline_bundle: Dict[str, Any],
    detector_output: Optional[Dict[str, Any]] = None,
    control_slice_concordant: Optional[bool] = None,
    change_log_match: bool = False,
) -> Dict[str, Any]:
    """Evaluate supporting threat indicators defined in COMMSHIELD_SPEC_v9.md."""
    cfg = DEFAULT_ATTRIBUTION_CONFIG

    cur_nas_fail = float(current_ratios.get("nas_failure_ratio", 0.0))
    cur_pfcp_fail = float(current_ratios.get("pfcp_failure_ratio", 0.0))
    cur_new_ue = float(current_ratios.get("new_ue_rate", 0.0))
    cur_entropy = float(current_ratios.get("ue_hash_entropy", 7.4))

    scaler_params = baseline_bundle.get("scaler_params", {})
    medians = scaler_params.get("medians", {})
    base_entropy = float(medians.get("ue_hash_entropy", 7.4))
    entropy_delta = cur_entropy - base_entropy

    nas_triggered = bool(cur_nas_fail > cfg.nas_failure_ratio_threshold)
    pfcp_triggered = bool(cur_pfcp_fail > cfg.pfcp_failure_ratio_threshold)
    entropy_triggered = bool(entropy_delta < cfg.ue_entropy_drop_threshold)
    new_ue_triggered = bool(cur_new_ue > cfg.new_ue_rate_threshold)

    agreement_state = "NONE"
    if detector_output and "fusion" in detector_output:
        agreement_state = detector_output["fusion"].get("agreement_state", "NONE")

    concordance_label = (
        None
        if control_slice_concordant is None
        else ("NETWORK_WIDE_EXPANSION" if control_slice_concordant else "LOCALIZED_TO_SLICE_1")
    )

    # Independent domain threat indicators (failure signals and entropy collapse)
    has_threat = bool(
        nas_triggered
        or pfcp_triggered
        or entropy_triggered
    )

    return {
        "ue_entropy_delta": round(entropy_delta, 3),
        "new_ue_rate": round(cur_new_ue, 4),
        "nas_failure_ratio": round(cur_nas_fail, 4),
        "pfcp_failure_ratio": round(cur_pfcp_fail, 4),
        "control_slice_concordance": concordance_label,
        "change_log_match": change_log_match,
        "detector_agreement_state": agreement_state,
        "nas_failure_triggered": nas_triggered,
        "pfcp_failure_triggered": pfcp_triggered,
        "entropy_drop_triggered": entropy_triggered,
        "new_ue_triggered": new_ue_triggered,
        "has_threat_indicators": has_threat,
    }
