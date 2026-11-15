"""Rule-based drift attributor with principled abstention."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import numpy as np

from .base import BaseAttributor
from .config import (
    AbstainReason,
    AttributionVerdict,
    DEFAULT_ATTRIBUTION_CONFIG,
    RecommendedAction,
)
from .metrics import (
    compute_volume_multiplier,
    evaluate_per_ue_rate,
    evaluate_proportional_growth,
    evaluate_threat_indicators,
)


class RuleBasedAttributor(BaseAttributor):
    """Rule-based Attributor applying policy table with principled abstention."""

    def __init__(self, config=None):
        self.config = config or DEFAULT_ATTRIBUTION_CONFIG

    def attribute(
        self,
        window: Dict[str, Any],
        baseline_bundle: Dict[str, Any],
        recent_windows: Optional[List[Dict[str, Any]]] = None,
        drift_detected: bool = False,
        detector_output: Optional[Dict[str, Any]] = None,
        control_slice_concordant: bool = True,
        change_log_match: bool = False,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Apply strict attribution rules in sequential order."""
        window_id = window.get("window_id", "")
        slice_id = window.get("slice_id", "sst-1-sd-010203")
        raw_counters = window.get("raw_counters", {})
        ratio_features = window.get("ratio_features", {})
        current_comp = window.get("composition_vector", {})

        # Baseline reference composition
        baseline_comp = baseline_bundle.get("composition_vector", {
            "registration_ratio": 0.0778,
            "session_setup_ratio": 0.9122,
            "failure_ratio": 0.0044,
            "other_signalling_ratio": 0.0056,
        })

        # 1. Compute evidence
        k = compute_volume_multiplier(raw_counters, baseline_bundle)
        prop_growth = evaluate_proportional_growth(
            current_composition=current_comp,
            baseline_composition=baseline_comp,
            scaling_factor_k=k,
            jsd_null_threshold=self.config.jsd_null_threshold_99th,
            pseudo_count=self.config.jsd_pseudo_count,
        )
        per_ue_eval = evaluate_per_ue_rate(ratio_features, baseline_bundle)
        threat_eval = evaluate_threat_indicators(
            current_ratios=ratio_features,
            baseline_bundle=baseline_bundle,
            detector_output=detector_output,
            control_slice_concordant=control_slice_concordant,
            change_log_match=change_log_match,
        )

        n_recent = len(recent_windows) if recent_windows else 1

        # 2. Check rule sequence in strict order:
        # Insufficient windows check
        if n_recent < self.config.min_windows_required and drift_detected:
            verdict = AttributionVerdict.UNCERTAIN.value
            abstain_reason = AbstainReason.INSUFFICIENT_WINDOWS.value
            action = RecommendedAction.QUARANTINE.value
            action_desc = "Abstain from adaptation; quarantine window; insufficient baseline history"

        # Check 1: likely_benign
        # Volume up, composition consistent, per-UE rate stable, no threat indicators
        elif (
            k >= self.config.volume_growth_min_k
            and prop_growth["passed"]
            and per_ue_eval["is_stable"]
            and not threat_eval["has_threat_indicators"]
        ):
            verdict = AttributionVerdict.LIKELY_BENIGN.value
            abstain_reason = None
            action = RecommendedAction.ADAPT_CANDIDATE.value
            action_desc = "Quarantine clear; queue windows for shadow candidate training"

        # Check 2: likely_attack
        # Composition shifted or per-UE rate jumped, with threat indicators triggered
        elif (
            (not prop_growth["passed"] or per_ue_eval["is_jumped"])
            and (
                threat_eval["has_threat_indicators"]
                or threat_eval["detector_agreement_state"] in ("both_fired", "BOTH_FIRE", "only_autoencoder", "AE_ONLY")
            )
        ):
            verdict = AttributionVerdict.LIKELY_ATTACK.value
            abstain_reason = None
            action = RecommendedAction.ALERT.value
            action_desc = "Trigger security alert; suppress candidate adaptation; quarantine window"

        # Check 3: uncertain (abstention with named reason)
        else:
            verdict = AttributionVerdict.UNCERTAIN.value
            action = RecommendedAction.QUARANTINE.value
            action_desc = "Abstain from adaptation; quarantine window; notify analyst"

            # Diagnose specific abstention reason
            if k >= self.config.volume_growth_min_k and not prop_growth["passed"] and not threat_eval["has_threat_indicators"]:
                abstain_reason = AbstainReason.VOLUME_COMPOSITION_DISAGREE.value
            elif prop_growth["passed"] and threat_eval["has_threat_indicators"]:
                abstain_reason = AbstainReason.MIMICRY_SUSPECTED.value
            elif (threat_eval["nas_failure_triggered"] or threat_eval["entropy_drop_triggered"]) and not (threat_eval["nas_failure_triggered"] and threat_eval["entropy_drop_triggered"]):
                abstain_reason = AbstainReason.INDICATOR_CONFLICT.value
            elif threat_eval["detector_agreement_state"] in ("only_isolation_forest", "IF_ONLY", "only_autoencoder", "AE_ONLY"):
                abstain_reason = AbstainReason.DETECTORS_DISAGREE.value
            else:
                abstain_reason = AbstainReason.INCONCLUSIVE_GROWTH_PATTERN.value

        return {
            "window_id": window_id,
            "slice_id": slice_id,
            "drift_detected": bool(drift_detected),
            "verdict": verdict,
            "abstain_reason": abstain_reason,
            "confidence_type": "evidence_category",
            "proportional_growth_test": prop_growth,
            "per_ue_rate_evaluation": per_ue_eval,
            "supporting_signals": {
                "ue_entropy_delta": threat_eval["ue_entropy_delta"],
                "new_ue_rate": threat_eval["new_ue_rate"],
                "nas_failure_ratio": threat_eval["nas_failure_ratio"],
                "pfcp_failure_ratio": threat_eval["pfcp_failure_ratio"],
                "control_slice_concordance": threat_eval["control_slice_concordance"],
                "change_log_match": threat_eval["change_log_match"],
                "detector_agreement_state": threat_eval["detector_agreement_state"],
            },
            "action": action,
            "action_recommendation": action_desc,
        }
