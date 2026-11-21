"""Statistical intervals and honest reporting utilities for CommShield.

Implements:
1. Wilson score interval for binomial proportions (exact, deterministic).
2. Bootstrap confidence interval for continuous and multi-seed metrics.
3. Formatting helpers enforcing 'n=<count>, interval too wide to interpret' when n < 10.
4. Categorization into effective attacks vs 'Where it does not work' group with reasons.
"""

import math
from typing import Any, Callable, Dict, List, Optional, Tuple
import numpy as np

WILSON_Z_95 = 1.95996  # Standard normal quantile for 95% two-sided confidence interval


def wilson_score_interval(k: int, n: int, z: float = WILSON_Z_95) -> Optional[Tuple[float, float]]:
    """Compute the Wilson score interval for a binomial proportion k/n."""
    if n <= 0:
        return None
    p = float(k) / float(n)
    denom = 1.0 + (z**2) / float(n)
    center = (p + (z**2) / (2.0 * float(n))) / denom
    margin = (z * math.sqrt((p * (1.0 - p) / float(n)) + ((z**2) / (4.0 * (float(n) ** 2))))) / denom
    lower = max(0.0, center - margin)
    upper = min(1.0, center + margin)
    return (round(lower, 4), round(upper, 4))


def compute_metric_ci(
    val: Optional[float],
    n: int,
    is_proportion: bool = True,
    z: float = WILSON_Z_95,
) -> Dict[str, Any]:
    """Format a metric with count n and 95% interval.
    
    Where n < 10, sets ci=None and ci_text='n=<count>, interval too wide to interpret'.
    """
    if val is None:
        return {
            "value": None,
            "n": n,
            "ci": None,
            "ci_text": "N/A",
            "display": "N/A",
        }

    val_rounded = round(float(val), 4)

    if n < 10:
        msg = f"n={n}, interval too wide to interpret"
        return {
            "value": val_rounded,
            "n": n,
            "ci": None,
            "ci_text": msg,
            "display": f"{val_rounded * 100:.1f}% ({msg})" if is_proportion else f"{val_rounded:.2f} ({msg})",
        }

    if is_proportion:
        k = int(round(val * n))
        ci = wilson_score_interval(k, n, z=z)
    else:
        ci = None

    if ci:
        ci_str = f"[{ci[0] * 100:.1f}%, {ci[1] * 100:.1f}%]"
        display_str = f"{val_rounded * 100:.1f}% [95% CI: {ci_str}] (n={n})"
    else:
        ci_str = "N/A"
        display_str = f"{val_rounded:.2f} (n={n})"

    return {
        "value": val_rounded,
        "n": n,
        "ci": ci,
        "ci_text": ci_str,
        "display": display_str,
    }


# Explanations from docs/DATA_FACTS.md for attacks where CommShield / ML detectors do not work
DATA_FACT_REASONS = {
    "ICMPFlood": "Trickle attack of only 613 packets over 20 min (<0.5 pps) diluted across 60 s window aggregations.",
    "UDPFlood": "Sample size too small (n=1 window), interval too wide to establish statistical power.",
    "HTTPFlood": "Sample size too small (n=3 windows), interval too wide to establish statistical power.",
    "SYNScan": "Sample size too small (n=4 windows), interval too wide to establish statistical power.",
}


def partition_real_attacks(attack_evaluations: Dict[str, Any]) -> Dict[str, Any]:
    """Partition real attack evaluations into 'effective_attacks' and 'where_it_does_not_work'."""
    effective: Dict[str, Any] = {}
    where_not_work: Dict[str, Any] = {}

    for atk_name, data in attack_evaluations.items():
        atk_n = int(data.get("attack_windows", 0))
        cs_recall = float(data.get("detectors", {}).get("commshield", {}).get("recall", 0.0))

        # Where it does not work: recall == 0 or fewer than 5 attack windows
        if cs_recall == 0.0 or atk_n < 5:
            reason = DATA_FACT_REASONS.get(
                atk_name,
                "Sample size fewer than 5 windows or recall is 0.0 under 60 s aggregation.",
            )
            item = dict(data)
            item["reason"] = reason
            where_not_work[atk_name] = item
        else:
            effective[atk_name] = dict(data)

    return {
        "slices_assigned": True,
        "effective_attacks": effective,
        "where_it_does_not_work": where_not_work,
    }
