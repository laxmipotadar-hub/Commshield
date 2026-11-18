"""Learned drift attributor with sequential evidence accumulation and fallback to rules.

Applies a small regularized statistical model over canonical attribution signals,
accumulating evidence over a window horizon N before issuing verdicts to dampen noise.
"""

from copy import deepcopy
from datetime import datetime, timezone
import json
import logging
import math
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
import numpy as np
from scipy.optimize import minimize

from .base import BaseAttributor
from .config import (
    AbstainReason,
    AttributionVerdict,
    DEFAULT_ATTRIBUTION_CONFIG,
    DEFAULT_LEARNED_ATTRIBUTION_CONFIG,
    LEARNED_ATTRIBUTION_FEATURES,
    LearnedAttributionConfig,
    RecommendedAction,
)
from .metrics import (
    compute_control_slice_concordance,
    compute_volume_multiplier,
    evaluate_per_ue_rate,
    evaluate_proportional_growth,
    evaluate_threat_indicators,
)
from .rule_based import RuleBasedAttributor

logger = logging.getLogger("commshield.learned_attribution")

MODEL_ARTIFACT_DEFAULT_PATH = Path(__file__).resolve().parent / "learned_model.json"


def extract_attribution_features(
    window: Dict[str, Any],
    baseline_bundle: Dict[str, Any],
    detector_output: Optional[Dict[str, Any]] = None,
    control_slice_concordant: Optional[bool] = None,
    control_slice_window: Optional[Dict[str, Any]] = None,
) -> Tuple[np.ndarray, Dict[str, float]]:
    """Extract canonical numerical attribution signals from a window.

    Guarantees:
    1. Only the existing signals documented in docs/AI_FEASIBILITY.md are extracted.
    2. Zero labels, ground truth fields, or raw identifiers enter the feature vector.
    3. Output vector matches LEARNED_ATTRIBUTION_FEATURES in exact ordered sequence.
    """
    raw_counters = window.get("raw_counters", {})
    ratio_features = window.get("ratio_features", {})
    current_comp = window.get("composition_vector", {})

    # Reference composition from baseline bundle
    baseline_comp = baseline_bundle.get("composition_vector", {
        "registration_ratio": 0.0778,
        "session_setup_ratio": 0.9122,
        "failure_ratio": 0.0044,
        "other_signalling_ratio": 0.0056,
    })

    # Evaluate dynamic second-slice concordance if control window is supplied
    if control_slice_concordant is None and control_slice_window is not None:
        control_slice_concordant = compute_control_slice_concordance(window, control_slice_window)

    # 1. Growth multiplier k
    k = compute_volume_multiplier(raw_counters, baseline_bundle)

    # 2. JSD Divergence
    prop_growth = evaluate_proportional_growth(
        current_composition=current_comp,
        baseline_composition=baseline_comp,
        scaling_factor_k=k,
    )
    jsd_div = float(prop_growth.get("jsd_divergence", 0.0))

    # 3. Per-UE session rate deviation
    per_ue_eval = evaluate_per_ue_rate(ratio_features, baseline_bundle)
    rate_dev = float(per_ue_eval.get("deviation_ratio", 0.0))

    # 4. Threat indicators
    threat_eval = evaluate_threat_indicators(
        current_ratios=ratio_features,
        baseline_bundle=baseline_bundle,
        detector_output=detector_output,
        control_slice_concordant=control_slice_concordant,
    )

    entropy_delta = float(threat_eval.get("ue_entropy_delta", 0.0))
    new_ue_rate = float(threat_eval.get("new_ue_rate", 0.0))
    nas_fail = float(threat_eval.get("nas_failure_ratio", 0.0))
    pfcp_fail = float(threat_eval.get("pfcp_failure_ratio", 0.0))

    # 5. Detector agreement numeric encoding
    agreement_state = str(threat_eval.get("detector_agreement_state", "NONE")).upper()
    agreement_map = {
        "BOTH_FIRE": 3.0,
        "BOTH_FIRED": 3.0,
        "AE_ONLY": 2.0,
        "ONLY_AUTOENCODER": 2.0,
        "IF_ONLY": 1.0,
        "ONLY_ISOLATION_FOREST": 1.0,
        "NONE": 0.0,
    }
    detector_agreement_num = agreement_map.get(agreement_state, 0.0)

    # 6. Control slice concordance numeric encoding
    if control_slice_concordant is True:
        concordant_num = 1.0
    elif control_slice_concordant is False:
        concordant_num = 0.0
    else:
        concordant_num = 0.5  # Neutral / missing control-slice evidence

    features_dict: Dict[str, float] = {
        "scaling_factor_k": round(float(k), 4),
        "jsd_divergence": round(float(jsd_div), 4),
        "ue_entropy_delta": round(float(entropy_delta), 4),
        "new_ue_rate": round(float(new_ue_rate), 4),
        "nas_failure_ratio": round(float(nas_fail), 4),
        "pfcp_failure_ratio": round(float(pfcp_fail), 4),
        "detector_agreement_numeric": round(float(detector_agreement_num), 2),
        "control_slice_concordant": round(float(concordant_num), 2),
        "per_ue_rate_deviation": round(float(rate_dev), 4),
    }

    # Strict check: ensure exact match with schema
    vector = np.array([features_dict[fn] for fn in LEARNED_ATTRIBUTION_FEATURES], dtype=np.float32)
    return vector, features_dict


class SmallRegularizedAttributionModel:
    """Small regularized linear model for drift attribution.

    Why small?
    As audited in docs/AI_FEASIBILITY.md, network drift telemetry provides very few
    distinct episodes of growth and attacks in tuning streams. A high-parameter neural network
    or deep ensemble would easily overfit to transient noise or diurnal patterns in the single
    synthetic growth episode. This model uses an L2-regularized linear decision boundary
    (9 weights + 1 intercept) with fixed random seed (42). This guarantees monotonic
    regularization, bounded complexity, full interpretability, and numerical stability.
    """

    def __init__(
        self,
        regularization_l2: float = 0.5,
        random_seed: int = 42,
        feature_names: Optional[List[str]] = None,
    ):
        self.regularization_l2 = regularization_l2
        self.random_seed = random_seed
        self.feature_names = feature_names or list(LEARNED_ATTRIBUTION_FEATURES)
        self.weights: Optional[np.ndarray] = None
        self.bias: float = 0.0
        self.means: Optional[np.ndarray] = None
        self.stds: Optional[np.ndarray] = None
        self.is_fitted: bool = False

    def _sigmoid(self, z: np.ndarray) -> np.ndarray:
        return 1.0 / (1.0 + np.exp(-np.clip(z, -25.0, 25.0)))

    def fit(self, X: np.ndarray, y: np.ndarray) -> "SmallRegularizedAttributionModel":
        """Fit L2-regularized logistic regression via L-BFGS-B with fixed random seed."""
        np.random.seed(self.random_seed)
        n_samples, n_features = X.shape
        if n_features != len(self.feature_names):
            raise ValueError(f"Feature count mismatch: expected {len(self.feature_names)}, got {n_features}")

        # Compute scaling parameters on training data
        self.means = np.mean(X, axis=0)
        self.stds = np.maximum(np.std(X, axis=0), 0.05)

        X_scaled = (X - self.means) / self.stds

        # Initial parameters (weights + bias)
        init_params = np.zeros(n_features + 1, dtype=np.float64)

        l2_lambda = self.regularization_l2

        def loss_and_grad(params):
            w = params[:n_features]
            b = params[n_features]

            logits = np.dot(X_scaled, w) + b
            p = self._sigmoid(logits)

            # Binary cross-entropy with L2 penalty on weights
            eps = 1e-12
            bce = -np.mean(y * np.log(p + eps) + (1.0 - y) * np.log(1.0 - p + eps))
            reg = 0.5 * l2_lambda * np.sum(w ** 2)
            total_loss = bce + reg

            # Gradients
            err = p - y
            grad_w = np.dot(X_scaled.T, err) / n_samples + l2_lambda * w
            grad_b = np.mean(err)

            grad = np.concatenate([grad_w, [grad_b]])
            return total_loss, grad

        res = minimize(
            loss_and_grad,
            init_params,
            jac=True,
            method="L-BFGS-B",
            options={"maxiter": 200, "ftol": 1e-7},
        )

        opt_params = res.x
        self.weights = opt_params[:n_features]
        self.bias = float(opt_params[n_features])
        self.is_fitted = True
        return self

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        """Compute predicted probability of attack P(y=1|x)."""
        if not self.is_fitted or self.weights is None:
            raise RuntimeError("Model must be fitted before predict_proba.")
        if X.ndim == 1:
            X = X.reshape(1, -1)

        X_scaled = (X - self.means) / self.stds
        logits = np.dot(X_scaled, self.weights) + self.bias
        return self._sigmoid(logits)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize model weights and metadata to dictionary."""
        return {
            "model_type": "logistic_regression",
            "regularization_l2": self.regularization_l2,
            "random_seed": self.random_seed,
            "feature_names": self.feature_names,
            "weights": self.weights.tolist() if self.weights is not None else [],
            "bias": self.bias,
            "means": self.means.tolist() if self.means is not None else [],
            "stds": self.stds.tolist() if self.stds is not None else [],
            "is_fitted": self.is_fitted,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SmallRegularizedAttributionModel":
        """Instantiate model from dictionary."""
        model = cls(
            regularization_l2=data.get("regularization_l2", 0.5),
            random_seed=data.get("random_seed", 42),
            feature_names=data.get("feature_names", list(LEARNED_ATTRIBUTION_FEATURES)),
        )
        if data.get("is_fitted", False):
            model.weights = np.array(data["weights"], dtype=np.float64)
            model.bias = float(data["bias"])
            model.means = np.array(data["means"], dtype=np.float64)
            model.stds = np.array(data["stds"], dtype=np.float64)
            model.is_fitted = True
        return model

    def save(self, path: Union[str, Path]) -> None:
        """Save model to JSON file."""
        fp = Path(path)
        fp.parent.mkdir(parents=True, exist_ok=True)
        with open(fp, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def load(cls, path: Union[str, Path]) -> "SmallRegularizedAttributionModel":
        """Load model from JSON file."""
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return cls.from_dict(data)


class LearnedAttributor(BaseAttributor):
    """Learned attributor with sequential evidence accumulation and rule fallback.
    
    Accumulates evidence over N windows (from config) before issuing an evidence verdict,
    preventing single noisy or bursty windows from flipping decisions. Keeps the rule-based
    attributor as the baseline and reliable fallback.
    """

    def __init__(
        self,
        config: Optional[LearnedAttributionConfig] = None,
        model: Optional[SmallRegularizedAttributionModel] = None,
        fallback_attributor: Optional[BaseAttributor] = None,
    ):
        self.config = config or DEFAULT_LEARNED_ATTRIBUTION_CONFIG
        self.fallback_attributor = fallback_attributor or RuleBasedAttributor()
        self.model = model or self._load_or_create_default_model()
        # Per-slice rolling history of predicted attack scores for sequential decisions
        self._score_history_by_slice: Dict[str, List[float]] = {}

    def _load_or_create_default_model(self) -> SmallRegularizedAttributionModel:
        """Load persisted model artifact if present, otherwise initialize pre-calibrated model."""
        if MODEL_ARTIFACT_DEFAULT_PATH.is_file():
            try:
                return SmallRegularizedAttributionModel.load(MODEL_ARTIFACT_DEFAULT_PATH)
            except Exception as e:
                logger.warning("Could not load model from %s: %s; using initialized model.", MODEL_ARTIFACT_DEFAULT_PATH, e)

        # Pre-calibrated default coefficients derived on synthetic tuning streams
        # Positive weights on threat signals (JSD, failure ratios, detector agreement)
        # Negative weights on growth signals (volume multiplier with stable rate, concordant slice)
        default_model = SmallRegularizedAttributionModel(
            regularization_l2=self.config.regularization_l2,
            random_seed=self.config.random_seed,
            feature_names=self.config.feature_names,
        )
        # Default parameter weights: [k, jsd, entropy_delta, new_ue_rate, nas_fail, pfcp_fail, det_agree, control_slice, rate_dev]
        default_model.weights = np.array([
            -0.85,  # scaling_factor_k: benign growth lowers attack probability when other signals stable
            2.10,   # jsd_divergence: high composition shift strongly indicates attack
            -1.45,  # ue_entropy_delta: negative shift (entropy collapse) increases attack probability
            0.60,   # new_ue_rate: elevated new arrival rate mildly elevates attack risk
            3.20,   # nas_failure_ratio: signalling failure strongly indicates signaling attack
            2.80,   # pfcp_failure_ratio: UPF association failure strongly indicates attack
            1.80,   # detector_agreement_numeric: higher consensus elevates attack risk
            -1.20,  # control_slice_concordant: concordance decreases attack probability
            1.40,   # per_ue_rate_deviation: jumping per-device rate indicates bot flood
        ], dtype=np.float64)
        default_model.bias = -0.40
        default_model.means = np.array([1.20, 0.02, 0.0, 0.02, 0.005, 0.001, 1.0, 0.8, 0.1], dtype=np.float64)
        default_model.stds = np.array([0.50, 0.05, 0.5, 0.03, 0.010, 0.005, 1.2, 0.3, 0.3], dtype=np.float64)
        default_model.is_fitted = True
        return default_model

    def reset_history(self, slice_id: Optional[str] = None) -> None:
        """Clear sequential window scores history."""
        if slice_id:
            self._score_history_by_slice.pop(slice_id, None)
        else:
            self._score_history_by_slice.clear()

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
        """Perform learned sequential attribution with principled abstention."""
        window_id = window.get("window_id", "")
        slice_id = window.get("slice_id", "sst-1-sd-010203")

        try:
            # 1. Feature Extraction (No label leakage, fixed schema)
            feat_vec, feat_dict = extract_attribution_features(
                window=window,
                baseline_bundle=baseline_bundle,
                detector_output=detector_output,
                control_slice_concordant=control_slice_concordant,
                control_slice_window=control_slice_window,
            )

            # 2. Model Scoring
            raw_attack_prob = float(self.model.predict_proba(feat_vec)[0])

            # 3. Sequential Evidence Accumulation
            # Maintain per-slice rolling window score history
            if slice_id not in self._score_history_by_slice:
                self._score_history_by_slice[slice_id] = []
            self._score_history_by_slice[slice_id].append(raw_attack_prob)

            # Bound history buffer length
            max_buf = max(20, self.config.sequential_window_length * 3)
            if len(self._score_history_by_slice[slice_id]) > max_buf:
                self._score_history_by_slice[slice_id].pop(0)

            history = self._score_history_by_slice[slice_id]
            n_history = len(history)
            n_target = self.config.sequential_window_length

            # Check Check 0: Insufficient accumulated windows
            if n_history < n_target and drift_detected:
                verdict = AttributionVerdict.UNCERTAIN.value
                abstain_reason = AbstainReason.INSUFFICIENT_WINDOWS.value
                action = RecommendedAction.QUARANTINE.value
                action_desc = f"Abstain from adaptation; accumulated {n_history}/{n_target} windows; insufficient history"
            else:
                # Compute sequential moving average over N windows
                recent_n = history[-n_target:]
                accumulated_score = float(np.mean(recent_n))
                score_range = float(np.max(recent_n) - np.min(recent_n))

                # If single windows oscillate violently inside the horizon, abstain on indicator conflict
                if score_range >= 0.50:
                    verdict = AttributionVerdict.UNCERTAIN.value
                    abstain_reason = AbstainReason.INDICATOR_CONFLICT.value
                    action = RecommendedAction.QUARANTINE.value
                    action_desc = "Abstain from adaptation; high variance across sequential horizon; notify analyst"
                elif accumulated_score >= self.config.attack_decision_threshold:
                    verdict = AttributionVerdict.LIKELY_ATTACK.value
                    abstain_reason = None
                    action = RecommendedAction.ALERT.value
                    action_desc = "Sequential evidence indicates malicious attack; quarantine window and alert"
                elif accumulated_score <= self.config.benign_decision_threshold:
                    verdict = AttributionVerdict.LIKELY_BENIGN.value
                    abstain_reason = None
                    action = RecommendedAction.ADAPT_CANDIDATE.value
                    action_desc = "Sequential evidence confirms legitimate proportional volume growth; queue for adaptation"
                else:
                    verdict = AttributionVerdict.UNCERTAIN.value
                    abstain_reason = AbstainReason.INCONCLUSIVE_GROWTH_PATTERN.value
                    action = RecommendedAction.QUARANTINE.value
                    action_desc = "Abstain from adaptation; ambiguous evidence score; notify analyst"

            # Compute standard proportional growth metadata for contract compatibility
            raw_counters = window.get("raw_counters", {})
            k = feat_dict.get("scaling_factor_k", 1.0)
            baseline_comp = baseline_bundle.get("composition_vector", {})
            current_comp = window.get("composition_vector", {})
            prop_growth = evaluate_proportional_growth(
                current_composition=current_comp,
                baseline_composition=baseline_comp,
                scaling_factor_k=k,
            )

            concordance_label = (
                "NETWORK_WIDE_EXPANSION"
                if feat_dict["control_slice_concordant"] == 1.0
                else ("LOCALIZED_TO_SLICE_1" if feat_dict["control_slice_concordant"] == 0.0 else None)
            )

            return {
                "window_id": window_id,
                "slice_id": slice_id,
                "drift_detected": bool(drift_detected),
                "verdict": verdict,
                "abstain_reason": abstain_reason,
                "confidence_type": "evidence_category",
                "proportional_growth_test": prop_growth,
                "per_ue_rate_evaluation": evaluate_per_ue_rate(window.get("ratio_features", {}), baseline_bundle),
                "supporting_signals": {
                    "attributor_type": "learned",
                    "model_type": self.config.model_type,
                    "sequential_horizon": n_target,
                    "accumulated_windows": n_history,
                    "ue_entropy_delta": feat_dict["ue_entropy_delta"],
                    "new_ue_rate": feat_dict["new_ue_rate"],
                    "nas_failure_ratio": feat_dict["nas_failure_ratio"],
                    "pfcp_failure_ratio": feat_dict["pfcp_failure_ratio"],
                    "control_slice_concordance": concordance_label,
                    "change_log_match": change_log_match,
                    "detector_agreement_state": str(detector_output.get("fusion", {}).get("agreement_state", "NONE")) if detector_output else "NONE",
                    "features_extracted": feat_dict,
                },
                "action": action,
                "action_recommendation": action_desc,
            }

        except Exception as err:
            logger.error("LearnedAttributor encountered error on window %s: %s; falling back to rules.", window_id, err)
            fallback_res = self.fallback_attributor.attribute(
                window=window,
                baseline_bundle=baseline_bundle,
                recent_windows=recent_windows,
                drift_detected=drift_detected,
                detector_output=detector_output,
                control_slice_concordant=control_slice_concordant,
                change_log_match=change_log_match,
                control_slice_window=control_slice_window,
                **kwargs,
            )
            fallback_res["supporting_signals"]["attributor_type"] = "learned_fallback_rules"
            fallback_res["supporting_signals"]["fallback_used"] = True
            fallback_res["supporting_signals"]["fallback_error"] = str(err)
            return fallback_res
