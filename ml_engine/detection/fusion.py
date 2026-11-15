"""Percentile-based score fusion and detector agreement logic."""

from typing import Any, Dict, Optional, Tuple
from .config import DEFAULT_DETECTION_CONFIG


def compute_agreement(if_flagged: bool, ae_flagged: bool) -> str:
    """Determine agreement state from individual detector flags.
    
    Returns:
        One of 'both_fired', 'only_isolation_forest', 'only_autoencoder', 'neither'.
    """
    if if_flagged and ae_flagged:
        return "both_fired"
    elif if_flagged and not ae_flagged:
        return "only_isolation_forest"
    elif not if_flagged and ae_flagged:
        return "only_autoencoder"
    else:
        return "neither"


def to_contract_agreement(agreement: str) -> str:
    """Map agreement string to CONTRACTS.md uppercase enum representation."""
    mapping = {
        "both_fired": "BOTH_FIRE",
        "only_isolation_forest": "IF_ONLY",
        "only_autoencoder": "AE_ONLY",
        "neither": "NONE",
        "BOTH_FIRE": "BOTH_FIRE",
        "IF_ONLY": "IF_ONLY",
        "AE_ONLY": "AE_ONLY",
        "NONE": "NONE",
    }
    return mapping.get(agreement, "NONE")


def fuse_scores(
    if_percentile: float,
    ae_percentile: float,
    threshold_percentile: Optional[float] = None,
    primary_rule: Optional[str] = None,
) -> Dict[str, Any]:
    """Fuse Isolation Forest and Autoencoder percentile scores per spec.
    
    Args:
        if_percentile: Isolation Forest percentile score [0.0 - 100.0].
        ae_percentile: Autoencoder percentile score [0.0 - 100.0].
        threshold_percentile: Cutoff threshold for flagging anomalies.
        primary_rule: Fusion rule from config ('MAX_PERCENTILE' or 'MEAN').
        
    Returns:
        Dict containing:
            - primary_rule: str
            - fused_percentile: float
            - secondary_mean_percentile: float
            - agreement_state: str ('both_fired', 'only_isolation_forest', etc.)
            - contract_agreement: str ('BOTH_FIRE', 'IF_ONLY', etc.)
            - is_anomalous: bool
    """
    cfg = DEFAULT_DETECTION_CONFIG
    thresh = threshold_percentile if threshold_percentile is not None else cfg.threshold_percentile
    rule = primary_rule if primary_rule is not None else cfg.primary_fusion_rule

    # Ensure bounded percentiles
    if_pct = float(min(100.0, max(0.0, if_percentile)))
    ae_pct = float(min(100.0, max(0.0, ae_percentile)))

    # Secondary mean percentile
    secondary_mean = round((if_pct + ae_pct) / 2.0, 4)

    # Primary rule calculation
    if rule == "MEAN":
        fused = secondary_mean
    else:
        # Default MAX_PERCENTILE
        fused = round(max(if_pct, ae_pct), 4)

    if_flagged = bool(if_pct >= thresh)
    ae_flagged = bool(ae_pct >= thresh)
    agreement = compute_agreement(if_flagged, ae_flagged)
    contract_agreement = to_contract_agreement(agreement)

    is_anomalous = bool(fused >= thresh)

    return {
        "primary_rule": rule,
        "fused_percentile": fused,
        "secondary_mean_percentile": secondary_mean,
        "agreement_state": agreement,
        "contract_agreement": contract_agreement,
        "is_anomalous": is_anomalous,
        "if_flagged": if_flagged,
        "ae_flagged": ae_flagged,
    }
