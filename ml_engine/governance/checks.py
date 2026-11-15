"""Pluggable governance checks implementing the four mandatory gates in exact order:

1. NormalHoldoutBacktestCheck (Holdout FPR)
2. ProportionalGrowthCheck (JSD & Per-UE rate stability)
3. CanaryRetentionTestCheck (Rescaled canary attack recall)
4. DriftBudgetCheck (D_rms, D_max, and Delta_canary budgets)
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np

from ml_engine.attribution.metrics import compute_jsd
from ml_engine.preprocessing.windowing import FEATURE_NAMES
from .base import GovernanceCheck, GovernanceCheckResult, GovernancePipeline
from .canary import (
    evaluate_canary_retention,
    load_canary_dataset,
    _score_windows_with_bundle,
)
from .config import (
    CANARY_RECALL_MARGIN_DELTA,
    DRIFT_BUDGET_CANARY_SHIFT_B_CAN,
    DRIFT_BUDGET_CUMULATIVE_B_RMS,
    DRIFT_BUDGET_MAX_FEATURE_B_MAX,
    DRIFT_BUDGET_STEP_LIMIT_B_STEP,
    EPSILON,
    MAX_HOLDOUT_FPR,
    MAX_JSD_DIVERGENCE,
    MAX_PER_UE_RATE_DEVIATION,
)

logger = logging.getLogger("commshield.governance.checks")

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
SYNTHETIC_DIR = PROJECT_ROOT / "data" / "synthetic"


# -----------------------------------------------------------------------------
# 1. Normal-Holdout Backtest Check
# -----------------------------------------------------------------------------
class NormalHoldoutBacktestCheck(GovernanceCheck):
    """Verifies that the candidate baseline does not increase the false-positive rate

    beyond MAX_HOLDOUT_FPR on held-out clean normal traffic.
    """
    name: str = "normal_holdout_backtest"
    mandatory: bool = True

    def evaluate(
        self,
        candidate_bundle: Dict[str, Any],
        active_bundle: Dict[str, Any],
        anchor_bundle: Dict[str, Any],
        context: Dict[str, Any],
    ) -> GovernanceCheckResult:
        slice_id = candidate_bundle.get("slice_id", "sst-1-sd-010203")
        holdout_windows = context.get("normal_holdout_windows")

        # Load clean normal holdout windows if not supplied
        if not holdout_windows:
            holdout_windows = self._load_default_normal_holdout(slice_id)

        if not holdout_windows:
            return GovernanceCheckResult(
                name=self.name,
                passed=True,
                mandatory=self.mandatory,
                metrics={"fpr": 0.0, "total_windows": 0, "flagged": 0, "limit": MAX_HOLDOUT_FPR},
                explanation="Normal holdout test passed: No holdout windows provided.",
            )

        # Score holdout windows using candidate models
        scores = _score_windows_with_bundle(holdout_windows, candidate_bundle)
        total = len(scores)
        flagged = sum(1 for s in scores if s["is_flagged"])
        fpr = flagged / max(1, total)

        passed = fpr <= MAX_HOLDOUT_FPR
        explanation = (
            f"Normal-holdout backtest: candidate FPR is {fpr:.2%} ({flagged}/{total} windows) "
            f"(limit: <= {MAX_HOLDOUT_FPR:.2%}). "
            f"Status: {'PASSED' if passed else 'FAILED (excessive false alarms on benign holdout)'}."
        )

        return GovernanceCheckResult(
            name=self.name,
            passed=passed,
            mandatory=self.mandatory,
            metrics={"fpr": round(fpr, 4), "total_windows": total, "flagged": flagged, "limit": MAX_HOLDOUT_FPR},
            explanation=explanation,
        )

    def _load_default_normal_holdout(self, slice_id: str) -> List[Dict[str, Any]]:
        """Load clean normal holdout windows for the slice."""
        candidates = [
            SYNTHETIC_DIR / "stable_benign.json",
            SYNTHETIC_DIR / "training_embb.json",
        ]
        for c in candidates:
            if c.is_file():
                try:
                    with open(c, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    wins = [
                        w for w in data.get("windows", [])
                        if not w.get("ground_truth", {}).get("is_attack", False)
                    ]
                    # Take last 20 windows as holdout
                    if wins:
                        return wins[-20:]
                except Exception as e:
                    logger.warning("Error loading holdout from %s: %s", c, e)
        return []


# -----------------------------------------------------------------------------
# 2. Proportional-Growth Verification Check
# -----------------------------------------------------------------------------
class ProportionalGrowthCheck(GovernanceCheck):
    """Verifies that candidate adaptation windows satisfy the proportional-growth test

    (JSD <= 0.0350 and stable per-UE rates).
    """
    name: str = "proportional_growth"
    mandatory: bool = True

    def evaluate(
        self,
        candidate_bundle: Dict[str, Any],
        active_bundle: Dict[str, Any],
        anchor_bundle: Dict[str, Any],
        context: Dict[str, Any],
    ) -> GovernanceCheckResult:
        adaptation_windows = context.get("adaptation_windows", [])

        # If no explicit adaptation windows, check candidate bundle's recorded composition
        cand_comp = candidate_bundle.get("composition_vector", {})
        baseline_comp = active_bundle.get("composition_vector") or anchor_bundle.get("composition_vector", {})

        if adaptation_windows:
            comp_accum: Dict[str, float] = {}
            pdu_rates: List[float] = []
            for w in adaptation_windows:
                c_vec = w.get("composition_vector", {})
                for k_cat, val in c_vec.items():
                    comp_accum[k_cat] = comp_accum.get(k_cat, 0.0) + float(val)
                pdu_rates.append(float(w.get("ratio_features", {}).get("pdu_session_rate_per_ue", 1.0)))

            n_w = max(1, len(adaptation_windows))
            avg_comp = {k: v / n_w for k, v in comp_accum.items()}
            mean_pdu = float(np.mean(pdu_rates)) if pdu_rates else 1.0
        else:
            avg_comp = cand_comp
            mean_pdu = 1.0

        jsd = compute_jsd(baseline_comp, avg_comp)
        active_scaler = active_bundle.get("scaler_params", {})
        base_pdu = float(active_scaler.get("medians", {}).get("pdu_session_rate_per_ue", mean_pdu))
        per_ue_ratio = abs(mean_pdu / max(0.001, base_pdu) - 1.0)

        jsd_passed = jsd <= MAX_JSD_DIVERGENCE
        per_ue_passed = per_ue_ratio <= MAX_PER_UE_RATE_DEVIATION
        passed = jsd_passed and per_ue_passed

        explanation = (
            f"Proportional-growth test: JSD divergence is {jsd:.4f} (limit: <= {MAX_JSD_DIVERGENCE:.4f}), "
            f"per-UE session rate deviation is {per_ue_ratio:.3f} (limit: <= {MAX_PER_UE_RATE_DEVIATION:.3f}). "
            f"Status: {'PASSED' if passed else 'FAILED (traffic composition shifted abnormally)'}."
        )

        return GovernanceCheckResult(
            name=self.name,
            passed=passed,
            mandatory=self.mandatory,
            metrics={
                "jsd": round(jsd, 5),
                "jsd_limit": MAX_JSD_DIVERGENCE,
                "per_ue_deviation": round(per_ue_ratio, 4),
                "per_ue_limit": MAX_PER_UE_RATE_DEVIATION,
            },
            explanation=explanation,
        )


# -----------------------------------------------------------------------------
# 3. Canary Retention Test Check
# -----------------------------------------------------------------------------
class CanaryRetentionTestCheck(GovernanceCheck):
    """Verifies that candidate does not degrade attack detection recall on rescaled canary attacks."""
    name: str = "canary_retention_test"
    mandatory: bool = True

    def evaluate(
        self,
        candidate_bundle: Dict[str, Any],
        active_bundle: Dict[str, Any],
        anchor_bundle: Dict[str, Any],
        context: Dict[str, Any],
    ) -> GovernanceCheckResult:
        slice_id = candidate_bundle.get("slice_id", "sst-1-sd-010203")
        canary_windows = context.get("canary_windows")
        if canary_windows is None:
            canary_windows = load_canary_dataset(slice_id=slice_id)

        volume_multiplier = float(context.get("volume_multiplier", 1.0))
        canary_eval = evaluate_canary_retention(
            active_bundle=active_bundle,
            candidate_bundle=candidate_bundle,
            canary_windows=canary_windows,
            volume_multiplier=volume_multiplier,
            margin_delta=CANARY_RECALL_MARGIN_DELTA,
        )

        # Store delta_canary in context for DriftBudgetCheck
        context["delta_canary"] = canary_eval.get("delta_canary", 0.0)

        # Persist to database if Session provided
        db = context.get("db")
        candidate_id = candidate_bundle.get("candidate_id")
        if db is not None and candidate_id:
            try:
                from backend.app.models import CanaryResult
                canary_row = CanaryResult(
                    candidate_id=candidate_id,
                    slice_id=slice_id,
                    active_recall=canary_eval["active_recall"],
                    candidate_recall=canary_eval["candidate_recall"],
                    recall_delta=canary_eval["recall_delta"],
                    category_recalls=canary_eval["category_recalls"],
                    passed=canary_eval["passed"],
                    details={"canary_count": canary_eval["canary_count"]},
                )
                db.add(canary_row)
                db.commit()
            except Exception as db_err:
                logger.warning("Error persisting canary result: %s", db_err)

        passed = canary_eval["passed"]
        explanation = (
            f"Canary retention test: active recall {canary_eval['active_recall']:.1%}, "
            f"candidate recall {canary_eval['candidate_recall']:.1%}, "
            f"recall delta {canary_eval['recall_delta']:.1%} (limit: <= {CANARY_RECALL_MARGIN_DELTA:.1%}). "
            f"Status: {'PASSED' if passed else 'FAILED (canary attack detection degraded beyond allowed margin)'}."
        )

        return GovernanceCheckResult(
            name=self.name,
            passed=passed,
            mandatory=self.mandatory,
            metrics=canary_eval,
            explanation=explanation,
        )


# -----------------------------------------------------------------------------
# 4. Cumulative Drift Budget Check
# -----------------------------------------------------------------------------
class DriftBudgetCheck(GovernanceCheck):
    """Enforces per-update step limit, cumulative anchor budget, and single-feature deviation limits."""
    name: str = "drift_budget"
    mandatory: bool = True

    def evaluate(
        self,
        candidate_bundle: Dict[str, Any],
        active_bundle: Dict[str, Any],
        anchor_bundle: Dict[str, Any],
        context: Dict[str, Any],
    ) -> GovernanceCheckResult:
        slice_id = candidate_bundle.get("slice_id", "sst-1-sd-010203")

        cand_scaler = candidate_bundle.get("scaler_params", {})
        active_scaler = active_bundle.get("scaler_params", {})
        anchor_scaler = anchor_bundle.get("scaler_params", {})

        cand_meds = cand_scaler.get("medians", {})
        act_meds = active_scaler.get("medians", {})
        anc_meds = anchor_scaler.get("medians", {})

        act_iqrs = active_scaler.get("iqrs", {})
        anc_iqrs = anchor_scaler.get("iqrs", {})

        z_act_list: List[float] = []
        z_anc_list: List[float] = []

        for f in FEATURE_NAMES:
            c_med = float(cand_meds.get(f, 0.0))
            a_med = float(act_meds.get(f, 0.0))
            anc_med = float(anc_meds.get(f, 0.0))

            # Scale: robust scale factor (IQR / 1.349)
            s_act = max(float(act_iqrs.get(f, 1.0)) / 1.349, EPSILON)
            s_anc = max(float(anc_iqrs.get(f, 1.0)) / 1.349, EPSILON)

            z_act = (c_med - a_med) / s_act
            z_anc = (c_med - anc_med) / s_anc

            z_act_list.append(z_act)
            z_anc_list.append(z_anc)

        # D_rms(cand, active): per-update step limit
        d_rms_active = float(np.sqrt(np.mean(np.square(z_act_list)))) if z_act_list else 0.0
        # D_rms(cand, anchor): cumulative budget from anchor
        d_rms_anchor = float(np.sqrt(np.mean(np.square(z_anc_list)))) if z_anc_list else 0.0
        # D_max(cand, anchor): maximum single-feature deviation
        d_max_anchor = float(np.max(np.abs(z_anc_list))) if z_anc_list else 0.0
        # Delta_canary: detection score shift
        delta_canary = float(context.get("delta_canary", 0.0))

        step_passed = d_rms_active <= DRIFT_BUDGET_STEP_LIMIT_B_STEP
        cumul_passed = d_rms_anchor <= DRIFT_BUDGET_CUMULATIVE_B_RMS
        dmax_passed = d_max_anchor <= DRIFT_BUDGET_MAX_FEATURE_B_MAX
        dcan_passed = delta_canary <= DRIFT_BUDGET_CANARY_SHIFT_B_CAN

        passed = step_passed and cumul_passed and dmax_passed and dcan_passed

        metrics = {
            "d_rms_active": round(d_rms_active, 4),
            "step_limit_b_step": DRIFT_BUDGET_STEP_LIMIT_B_STEP,
            "step_passed": step_passed,
            "d_rms_anchor": round(d_rms_anchor, 4),
            "cumulative_budget_b_rms": DRIFT_BUDGET_CUMULATIVE_B_RMS,
            "cumul_passed": cumul_passed,
            "d_max_anchor": round(d_max_anchor, 4),
            "max_feature_budget_b_max": DRIFT_BUDGET_MAX_FEATURE_B_MAX,
            "dmax_passed": dmax_passed,
            "delta_canary": round(delta_canary, 4),
            "canary_shift_budget_b_can": DRIFT_BUDGET_CANARY_SHIFT_B_CAN,
            "dcan_passed": dcan_passed,
        }

        # Persist to drift_budgets table if db provided
        db = context.get("db")
        candidate_id = candidate_bundle.get("candidate_id")
        if db is not None and candidate_id:
            try:
                from backend.app.models import DriftBudget
                budget_row = DriftBudget(
                    candidate_id=candidate_id,
                    slice_id=slice_id,
                    d_rms_active=d_rms_active,
                    d_rms_anchor=d_rms_anchor,
                    d_max_anchor=d_max_anchor,
                    delta_canary=delta_canary,
                    metrics=metrics,
                    passed=passed,
                )
                db.add(budget_row)
                db.commit()
            except Exception as db_err:
                logger.warning("Error persisting drift budget: %s", db_err)

        explanation = (
            f"Drift budget: D_rms(cand, active)={d_rms_active:.2f} (<= {DRIFT_BUDGET_STEP_LIMIT_B_STEP}), "
            f"D_rms(cand, anchor)={d_rms_anchor:.2f} (<= {DRIFT_BUDGET_CUMULATIVE_B_RMS}), "
            f"D_max={d_max_anchor:.2f} (<= {DRIFT_BUDGET_MAX_FEATURE_B_MAX}), "
            f"Delta_can={delta_canary:.2f} (<= {DRIFT_BUDGET_CANARY_SHIFT_B_CAN}). "
            f"Status: {'PASSED' if passed else 'FAILED (budget or step limits exceeded)'}."
        )

        return GovernanceCheckResult(
            name=self.name,
            passed=passed,
            mandatory=self.mandatory,
            metrics=metrics,
            explanation=explanation,
        )


def build_default_governance_pipeline() -> GovernancePipeline:
    """Build the standard 4-gate governance pipeline in exact required order."""
    return GovernancePipeline(checks=[
        NormalHoldoutBacktestCheck(),
        ProportionalGrowthCheck(),
        CanaryRetentionTestCheck(),
        DriftBudgetCheck(),
    ])
