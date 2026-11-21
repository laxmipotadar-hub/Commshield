"""Rule-based drift attributor with principled abstention."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .base import BaseAttributor
from .config import (
    AbstainReason,
    AttributionVerdict,
    DEFAULT_ATTRIBUTION_CONFIG,
    RecommendedAction,
)
from .metrics import (
    compute_control_slice_concordance,
    compute_device_model_evidence,
    compute_device_provisioning_evidence,
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
        control_slice_concordant: Optional[bool] = None,
        change_log_match: bool = False,
        control_slice_window: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Apply strict attribution rules in sequential order."""
        if control_slice_concordant is None and control_slice_window is not None:
            control_slice_concordant = compute_control_slice_concordance(window, control_slice_window)
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

        # Check if device evidence is enabled
        device_evidence_enabled = getattr(self.config, "device_evidence_enabled", False) or kwargs.get("device_evidence_enabled", False)

        provisioned_share = kwargs.get("provisioned_share")
        event_match = kwargs.get("event_match")
        volume_vs_batch_size = kwargs.get("volume_vs_batch_size")
        device_anomalous_share = kwargs.get("device_anomalous_share")
        device_uncertain_share = kwargs.get("device_uncertain_share")

        device_windows = kwargs.get("device_windows")
        device_predictions = kwargs.get("device_predictions")
        loader = kwargs.get("provisioning_loader")

        if device_evidence_enabled:
            # If signals not provided directly, compute them from device windows / predictions
            if provisioned_share is None or event_match is None or volume_vs_batch_size is None:
                if device_windows is not None:
                    prov_ev = compute_device_provisioning_evidence(
                        device_windows=device_windows,
                        loader=loader,
                        window_start=window.get("window_start"),
                        slice_id=slice_id,
                        baseline_active_ues=baseline_bundle.get("active_ue_count_by_slice", {}).get(slice_id),
                        tolerance=getattr(self.config, "volume_batch_tolerance", 1.25),
                    )
                    provisioned_share = prov_ev["provisioned_share"]
                    event_match = prov_ev["event_match"]
                    volume_vs_batch_size = prov_ev["volume_vs_batch_size"]
                else:
                    provisioned_share = 1.0
                    event_match = False
                    volume_vs_batch_size = {"fitting_volume": False, "batch_id": None, "added_devices": 0, "ratio": 0.0}

            if device_anomalous_share is None or device_uncertain_share is None:
                if device_predictions is not None:
                    dev_mod_ev = compute_device_model_evidence(device_predictions)
                    device_anomalous_share = dev_mod_ev["device_anomalous_share"]
                    device_uncertain_share = dev_mod_ev["device_uncertain_share"]
                else:
                    device_anomalous_share = 0.0
                    device_uncertain_share = 0.0

            fitting_volume = volume_vs_batch_size.get("fitting_volume", False) if isinstance(volume_vs_batch_size, dict) else bool(volume_vs_batch_size)
            min_prov = getattr(self.config, "min_provisioned_share", 0.95)
            max_anom = getattr(self.config, "max_anomalous_share", 0.10)
            max_unc = getattr(self.config, "max_uncertain_share", 0.30)

            # Rule 1: Unprovisioned IDs present -> LIKELY_ATTACK & QUARANTINE
            if provisioned_share < min_prov:
                verdict = AttributionVerdict.LIKELY_ATTACK.value
                abstain_reason = AbstainReason.UNPROVISIONED_DEVICES_PRESENT.value
                action = RecommendedAction.QUARANTINE.value
                action_desc = "Trigger security alert; quarantine window; unprovisioned rogue device IDs detected"

            # Rule 2: Provisioned AND matched event AND fitting volume AND low anomalous share -> LIKELY_BENIGN
            elif (
                provisioned_share >= min_prov
                and event_match is True
                and fitting_volume is True
                and device_anomalous_share <= max_anom
                and device_uncertain_share <= max_unc
            ):
                verdict = AttributionVerdict.LIKELY_BENIGN.value
                abstain_reason = None
                action = RecommendedAction.ADAPT_CANDIDATE.value
                action_desc = "Quarantine clear; approved onboarding verified by provisioning catalog and device models"

            # Rule 3: Uncertain or unapproved anomalous conditions
            else:
                action = RecommendedAction.QUARANTINE.value
                action_desc = "Abstain from adaptation; quarantine window; notify analyst"

                if event_match and not fitting_volume:
                    verdict = AttributionVerdict.UNCERTAIN.value
                    abstain_reason = AbstainReason.GROWTH_EXCEEDS_APPROVED_BATCH.value
                    action_desc = "Abstain from adaptation; quarantine window; traffic growth exceeds approved batch count"
                elif device_uncertain_share > max_unc:
                    verdict = AttributionVerdict.UNCERTAIN.value
                    abstain_reason = AbstainReason.DEVICE_BEHAVIOUR_UNCERTAIN.value
                    action_desc = "Abstain from adaptation; quarantine window; elevated device uncertainty in conformal band"
                elif device_anomalous_share > max_anom:
                    verdict = AttributionVerdict.LIKELY_ATTACK.value
                    abstain_reason = None
                    action = RecommendedAction.ALERT.value
                    action_desc = "Trigger security alert; anomalous device behavior detected"
                elif not event_match and k >= self.config.volume_growth_min_k:
                    verdict = AttributionVerdict.LIKELY_ATTACK.value
                    abstain_reason = None
                    action = RecommendedAction.ALERT.value
                    action_desc = "Trigger security alert; burst from provisioned SIMs with no approved change event"
                elif not event_match and volume_vs_batch_size.get("added_devices", 0) > 0:
                    verdict = AttributionVerdict.UNCERTAIN.value
                    abstain_reason = AbstainReason.PARTIAL_EVENT_MATCH.value
                    action_desc = "Abstain from adaptation; quarantine window; partial or unverified change event match"
                else:
                    verdict = AttributionVerdict.LIKELY_BENIGN.value
                    abstain_reason = None
                    action = RecommendedAction.ADAPT_CANDIDATE.value
                    action_desc = "Normal baseline operations; within nominal limits"

        else:
            # 2. Check original rule sequence in strict order:
            # Insufficient windows check
            if n_recent < self.config.min_windows_required and drift_detected:
                verdict = AttributionVerdict.UNCERTAIN.value
                abstain_reason = AbstainReason.INSUFFICIENT_WINDOWS.value
                action = RecommendedAction.QUARANTINE.value
                action_desc = "Abstain from adaptation; quarantine window; insufficient baseline history"

            # Check 1: likely_benign
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
                "provisioned_share": provisioned_share,
                "event_match": event_match,
                "volume_vs_batch_size": volume_vs_batch_size,
                "device_anomalous_share": device_anomalous_share,
                "device_uncertain_share": device_uncertain_share,
            },
            "action": action,
            "action_recommendation": action_desc,
        }
