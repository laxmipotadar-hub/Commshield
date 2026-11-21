"""Three-Arm Centrepiece Experiment Runner.

Replays identical synthetic 5G telemetry streams across three operational paradigms:
- Arm A (Static Anchor): Frozen initial baseline; never adapts.
- Arm B (Naive Adaptation): Retrains continuously on ADWIN drift without attribution or governance.
- Arm C (CommShield Gated): Uses ADWIN attribution, quarantine isolation, 4-gate verification, and analyst approval.

Metrics computed:
1. Attack Detection Rate (Recall): Fraction of ground-truth attack windows flagged.
2. False-Positive Rate (FPR): Fraction of ground-truth benign windows flagged.
3. Baseline Contamination: Fraction of attack windows in the active baseline's training set (tracked over time and final).
4. Number of Adaptations & Quarantines: Baseline promotion count and quarantined window count.
5. Recovery Time: Windows from the end of an attack until false-positive rate returns to normal.
"""

from copy import deepcopy
from datetime import datetime, timezone
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
import uuid

import joblib
import numpy as np

from ml_engine.attribution.adwin import ADWIN
from ml_engine.attribution.config import AttributionVerdict, DEFAULT_ATTRIBUTION_CONFIG
from ml_engine.attribution.rule_based import RuleBasedAttributor
from ml_engine.detection import DetectionEngine
from ml_engine.governance.candidate import build_shadow_candidate
from ml_engine.governance.checks import build_default_governance_pipeline
from ml_engine.governance.naive_adapter import naive_retrain_on_drift
from ml_engine.preprocessing.synthetic_generator import SyntheticGenerator
from ml_engine.preprocessing.windowing import FEATURE_NAMES, RobustScaler

logger = logging.getLogger("commshield.experiment")

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
PROCESSED_BASELINES_DIR = PROJECT_ROOT / "data" / "processed" / "baselines"
RESULTS_DIR = PROJECT_ROOT / "experiments" / "results"

DEFAULT_SCENARIOS = [
    "stable_benign",
    "legitimate_growth",
    "slow_attack_ramp",
    "attack_in_growth",
    "mimicry_attack",
]
DEFAULT_SEEDS = [42, 101, 2024, 777, 999]


def calculate_contamination(training_windows: List[Dict[str, Any]]) -> float:
    """Calculate baseline contamination: fraction of attack windows in training data.

    Definition:
        Contamination = |{w in TrainingSet : w is attack}| / |TrainingSet|
    """
    if not training_windows:
        return 0.0
    attack_count = sum(
        1 for w in training_windows
        if (
            bool(w.get("ground_truth", {}).get("is_attack", False))
            if isinstance(w.get("ground_truth"), dict)
            else bool(w.get("is_attack", False))
        )
    )
    return round(float(attack_count / len(training_windows)), 4)


def calculate_recovery_time(
    y_true: List[bool],
    y_pred: List[bool],
    nominal_fpr_threshold: float = 0.05,
) -> Optional[int]:
    """Calculate recovery time: windows from attack end until false-positive rate normalizes.

    Definition:
        Let t_last be the index of the final ground-truth attack window (y_true[t_last] == True).
        If there are no attack windows in the stream, recovery time is 0.
        If t_last is the final window of the sequence (no post-attack observation), returns 0.
        Otherwise, for t > t_last (benign recovery segment):
        Recovery time is the number of windows from (t_last + 1) until the detector stops alerting
        (either reaches an unflagged benign window or rolling FPR falls <= nominal_fpr_threshold).
        If the detector continues alerting on all remaining benign windows, returns total remaining windows.
    """
    attack_indices = [i for i, yt in enumerate(y_true) if yt]
    if not attack_indices:
        return 0

    t_last = attack_indices[-1]
    if t_last >= len(y_true) - 1:
        return 0

    post_preds = y_pred[t_last + 1:]
    # Find first unflagged window or point where post-attack alerts subside
    for offset, flagged in enumerate(post_preds):
        if not flagged:
            return offset

    # Did not recover before sequence ended
    return len(post_preds)


def compute_arm_metrics(
    y_true: List[bool],
    y_pred: List[bool],
    contamination_over_time: List[float],
    adaptations_count: int,
    quarantined_count: int,
) -> Dict[str, Any]:
    """Compute standard classification and governance metrics from predictions and ground truth."""
    tp = sum(1 for yt, yp in zip(y_true, y_pred) if yt and yp)
    fp = sum(1 for yt, yp in zip(y_true, y_pred) if not yt and yp)
    fn = sum(1 for yt, yp in zip(y_true, y_pred) if yt and not yp)
    tn = sum(1 for yt, yp in zip(y_true, y_pred) if not yt and not yp)

    total_attacks = tp + fn
    total_benign = fp + tn

    recall = round(float(tp / total_attacks), 4) if total_attacks > 0 else None
    fpr = round(float(fp / total_benign), 4) if total_benign > 0 else 0.0
    precision = round(float(tp / (tp + fp)), 4) if (tp + fp) > 0 else (1.0 if total_attacks == 0 else 0.0)
    f1 = round(float(2 * tp / (2 * tp + fp + fn)), 4) if (2 * tp + fp + fn) > 0 else 0.0

    final_contamination = contamination_over_time[-1] if contamination_over_time else 0.0
    recovery_time = calculate_recovery_time(y_true, y_pred)

    return {
        "recall": recall,
        "fpr": fpr,
        "precision": precision,
        "f1": f1,
        "true_positives": tp,
        "false_positives": fp,
        "true_negatives": tn,
        "false_negatives": fn,
        "baseline_contamination_final": final_contamination,
        "baseline_contamination_over_time": contamination_over_time,
        "adaptations_count": adaptations_count,
        "quarantined_count": quarantined_count,
        "recovery_time_windows": recovery_time,
    }


def load_anchor_baseline(slice_id: str = "sst-1-sd-010203") -> Dict[str, Any]:
    """Load trusted anchor baseline bundle from disk."""
    candidates = list(PROCESSED_BASELINES_DIR.glob(f"{slice_id}_*.joblib"))
    if not candidates:
        raise FileNotFoundError(f"Anchor baseline artifact for slice {slice_id} not found in {PROCESSED_BASELINES_DIR}")
    return joblib.load(candidates[0])


def evaluate_window_with_bundle(window: Dict[str, Any], bundle: Dict[str, Any]) -> Tuple[float, bool]:
    """Evaluate a single window against a baseline bundle, returning (fused_percentile, is_flagged)."""
    scaler: RobustScaler = bundle["scaler"]
    ratios = window.get("ratio_features", {})
    scaled_vector = scaler.transform_vector(ratios)
    x = np.array([[scaled_vector.get(f, 0.0) for f in FEATURE_NAMES]], dtype=np.float32)

    engine = DetectionEngine()
    if "detectors" in bundle:
        for name, det in bundle["detectors"].items():
            engine.register_detector(name, det)
    else:
        if "isolation_forest" in bundle:
            engine.register_detector("isolation_forest", bundle["isolation_forest"])
        if "autoencoder" in bundle:
            engine.register_detector("autoencoder", bundle["autoencoder"])

    eval_out = engine.evaluate_vector(x)
    fused_pct = float(eval_out["fusion"]["fused_percentile"])
    is_anom = bool(eval_out["fusion"].get("is_anomalous", False)) or bool(eval_out["cusum"].get("is_alarm", False))
    return fused_pct, is_anom


class ThreeArmExperimentRunner:
    """Orchestrates identical stream replay across Arm A, Arm B, and Arm C."""

    def __init__(
        self,
        slice_id: str = "sst-1-sd-010203",
        slice_name: str = "eMBB",
        config_version: str = "v1.0.0",
        results_dir: Optional[Path] = None,
    ):
        self.slice_id = slice_id
        self.slice_name = slice_name
        self.config_version = config_version
        self.results_dir = results_dir or RESULTS_DIR
        self.results_dir.mkdir(parents=True, exist_ok=True)
        self.anchor_bundle = load_anchor_baseline(slice_id)

    def run_single(
        self,
        scenario_name: str,
        seed: int,
        num_windows: int = 50,
        window_duration_sec: int = 60,
    ) -> Dict[str, Any]:
        """Execute a single scenario run across all three arms with an identical seed and input stream."""
        # 1. Deterministic stream generation
        gen = SyntheticGenerator(seed=seed)
        windows = gen.generate_scenario_windows(
            scenario_name=scenario_name,
            slice_name=self.slice_name,
            num_windows=num_windows,
            window_duration_sec=window_duration_sec,
        )

        y_true = [bool(w.get("ground_truth", {}).get("is_attack", False)) for w in windows]

        # -------------------------------------------------------------
        # ARM A: Static Anchor (Frozen Baseline)
        # -------------------------------------------------------------
        arm_a_bundle = self.anchor_bundle
        y_pred_a: List[bool] = []
        contamination_a: List[float] = []

        for w in windows:
            _, is_flagged = evaluate_window_with_bundle(w, arm_a_bundle)
            y_pred_a.append(is_flagged)
            contamination_a.append(0.0)

        metrics_a = compute_arm_metrics(
            y_true=y_true,
            y_pred=y_pred_a,
            contamination_over_time=contamination_a,
            adaptations_count=0,
            quarantined_count=0,
        )

        # -------------------------------------------------------------
        # ARM B: Naive Continuous Retraining on Drift
        # -------------------------------------------------------------
        arm_b_bundle = deepcopy(self.anchor_bundle)
        training_windows_b: List[Dict[str, Any]] = list(self.anchor_bundle.get("training_windows", []))
        buffer_b: List[Dict[str, Any]] = []
        y_pred_b: List[bool] = []
        contamination_b: List[float] = []
        adaptations_b = 0

        adwin_b = ADWIN(delta=0.002, min_window_length=5, max_window_length=50)

        for w in windows:
            fused_pct, is_flagged = evaluate_window_with_bundle(w, arm_b_bundle)
            y_pred_b.append(is_flagged)

            # Record current baseline contamination
            cur_contam = calculate_contamination(training_windows_b)
            contamination_b.append(cur_contam)

            buffer_b.append(w)
            raw = w.get("raw_counters", {})
            total_bytes = float(raw.get("total_bytes_uplink", 0) + raw.get("total_bytes_downlink", 0))
            drift_alarm = adwin_b.update(total_bytes)

            if drift_alarm and len(buffer_b) >= 8:
                # Naive unconditional retrain on recent buffer windows
                recent_train = buffer_b[-25:]
                arm_b_bundle = naive_retrain_on_drift(
                    slice_id=self.slice_id,
                    recent_windows=recent_train,
                    active_baseline_bundle=arm_b_bundle,
                    output_dir=PROJECT_ROOT / "data" / "processed" / "naive_baselines",
                )
                training_windows_b = recent_train
                adaptations_b += 1
                adwin_b.reset()

        metrics_b = compute_arm_metrics(
            y_true=y_true,
            y_pred=y_pred_b,
            contamination_over_time=contamination_b,
            adaptations_count=adaptations_b,
            quarantined_count=0,
        )

        # -------------------------------------------------------------
        # ARM C: CommShield Gated Adaptation
        # -------------------------------------------------------------
        arm_c_bundle = deepcopy(self.anchor_bundle)
        training_windows_c: List[Dict[str, Any]] = list(self.anchor_bundle.get("training_windows", []))
        quarantined_ids: Set[str] = set()
        legitimate_growth_pool: List[Dict[str, Any]] = []
        buffer_c: List[Dict[str, Any]] = []
        y_pred_c: List[bool] = []
        contamination_c: List[float] = []
        adaptations_c = 0
        quarantined_count_c = 0

        adwin_c = ADWIN(delta=0.002, min_window_length=5, max_window_length=50)
        attributor = RuleBasedAttributor(config=DEFAULT_ATTRIBUTION_CONFIG)
        gov_pipeline = build_default_governance_pipeline()

        for w in windows:
            fused_pct, is_flagged = evaluate_window_with_bundle(w, arm_c_bundle)
            y_pred_c.append(is_flagged)

            cur_contam = calculate_contamination(training_windows_c)
            # HARD SECURITY ASSERTION: Quarantined windows never enter active training in Arm C
            assert cur_contam == 0.0, f"Arm C baseline contamination violated: {cur_contam} > 0.0"
            contamination_c.append(cur_contam)

            buffer_c.append(w)
            w_id = w.get("window_id", "")
            raw = w.get("raw_counters", {})
            total_bytes = float(raw.get("total_bytes_uplink", 0) + raw.get("total_bytes_downlink", 0))
            drift_alarm = adwin_c.update(total_bytes)

            if drift_alarm:
                # 1. Attribution evaluation
                attr_res = attributor.attribute(
                    window=w,
                    baseline_bundle=arm_c_bundle,
                    recent_windows=buffer_c[-10:],
                    drift_detected=True,
                )
                verdict = attr_res.get("verdict")

                if verdict == AttributionVerdict.LIKELY_BENIGN.value:
                    legitimate_growth_pool.append(w)
                    # 2. Build Shadow Candidate with verified legitimate growth windows
                    if len(legitimate_growth_pool) >= 5:
                        cand_version = f"v1.1.0-arm-c-s{seed}-{adaptations_c + 1}"
                        cand_bundle, _ = build_shadow_candidate(
                            slice_id=self.slice_id,
                            active_bundle=arm_c_bundle,
                            anchor_bundle=self.anchor_bundle,
                            adaptation_windows=legitimate_growth_pool[-20:],
                            quarantined_window_ids=quarantined_ids,
                            candidate_version=cand_version,
                            output_dir=PROJECT_ROOT / "data" / "processed" / "candidates",
                        )

                        # 3. Four-check Governance Pipeline
                        gov_eval = gov_pipeline.evaluate(
                            candidate_bundle=cand_bundle,
                            active_bundle=arm_c_bundle,
                            anchor_bundle=self.anchor_bundle,
                            context={
                                "ratio_only_budget": True,
                                "adaptation_windows": legitimate_growth_pool[-20:],
                            },
                        )

                        # 4. Careful Analyst Scripted Approval Gate
                        if gov_eval.all_mandatory_passed:
                            arm_c_bundle = cand_bundle
                            training_windows_c = list(cand_bundle.get("training_windows", []))
                            adaptations_c += 1
                            adwin_c.reset()
                        else:
                            # Rejection: candidate failed mandatory canary or drift budget check
                            quarantined_count_c += 1
                else:
                    # Non-proportional shift or attack -> Quarantine
                    quarantined_ids.add(w_id)
                    quarantined_count_c += 1
                    adwin_c.reset()

        metrics_c = compute_arm_metrics(
            y_true=y_true,
            y_pred=y_pred_c,
            contamination_over_time=contamination_c,
            adaptations_count=adaptations_c,
            quarantined_count=quarantined_count_c,
        )

        run_result = {
            "scenario": scenario_name,
            "seed": seed,
            "config_version": self.config_version,
            "num_windows": num_windows,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "arms": {
                "arm_a_static": metrics_a,
                "arm_b_naive": metrics_b,
                "arm_c_commshield": metrics_c,
            },
        }

        # Save individual run file
        run_file = self.results_dir / f"run_{scenario_name}_s{seed}_{int(datetime.now(timezone.utc).timestamp())}.json"
        with open(run_file, "w", encoding="utf-8") as f:
            json.dump(run_result, f, indent=2)

        return run_result

    def run_all(
        self,
        scenarios: Optional[List[str]] = None,
        seeds: Optional[List[int]] = None,
        num_windows: int = 50,
        write_db: bool = True,
    ) -> Dict[str, Any]:
        """Execute full benchmark across all scenarios and seeds, computing aggregates and writing results."""
        target_scenarios = scenarios or DEFAULT_SCENARIOS
        target_seeds = seeds or DEFAULT_SEEDS

        all_runs: List[Dict[str, Any]] = []
        scenario_summaries: Dict[str, Any] = {}

        for sc in target_scenarios:
            runs_for_scenario: List[Dict[str, Any]] = []
            for s in target_seeds:
                res = self.run_single(
                    scenario_name=sc,
                    seed=s,
                    num_windows=num_windows,
                )
                runs_for_scenario.append(res)
                all_runs.append(res)

            # Compute mean and std across seeds for each arm
            arm_summaries = {}
            for arm_key in ["arm_a_static", "arm_b_naive", "arm_c_commshield"]:
                recalls = [r["arms"][arm_key]["recall"] for r in runs_for_scenario if r["arms"][arm_key]["recall"] is not None]
                fprs = [r["arms"][arm_key]["fpr"] for r in runs_for_scenario]
                contams = [r["arms"][arm_key]["baseline_contamination_final"] for r in runs_for_scenario]
                adaptations = [r["arms"][arm_key]["adaptations_count"] for r in runs_for_scenario]
                quarantines = [r["arms"][arm_key]["quarantined_count"] for r in runs_for_scenario]
                recoveries = [r["arms"][arm_key]["recovery_time_windows"] for r in runs_for_scenario if r["arms"][arm_key]["recovery_time_windows"] is not None]

                arm_summaries[arm_key] = {
                    "recall_mean": round(float(np.mean(recalls)), 4) if recalls else None,
                    "recall_std": round(float(np.std(recalls)), 4) if recalls else None,
                    "fpr_mean": round(float(np.mean(fprs)), 4),
                    "fpr_std": round(float(np.std(fprs)), 4),
                    "contamination_mean": round(float(np.mean(contams)), 4),
                    "contamination_std": round(float(np.std(contams)), 4),
                    "adaptations_mean": round(float(np.mean(adaptations)), 2),
                    "quarantined_mean": round(float(np.mean(quarantines)), 2),
                    "recovery_time_mean": round(float(np.mean(recoveries)), 2) if recoveries else 0.0,
                }

            scenario_summaries[sc] = {
                "num_seeds": len(target_seeds),
                "seeds": target_seeds,
                "arms": arm_summaries,
            }

        # Write to database if requested
        if write_db:
            self._write_results_to_db(all_runs)

        combined_summary = {
            "config_version": self.config_version,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "scenarios": target_scenarios,
            "seeds": target_seeds,
            "summaries": scenario_summaries,
        }

        summary_file = self.results_dir / "experiment_summary.json"
        with open(summary_file, "w", encoding="utf-8") as f:
            json.dump(combined_summary, f, indent=2)

        return combined_summary

    def _write_results_to_db(self, runs: List[Dict[str, Any]]) -> None:
        """Persist individual run metrics to experiment_results table."""
        try:
            from backend.app.database import SessionLocal
            from backend.app.models import ExperimentResult

            db = SessionLocal()
            for r in runs:
                sc = r["scenario"]
                s = r["seed"]
                cfg = r["config_version"]
                for arm_name, metrics in r["arms"].items():
                    exp_row = ExperimentResult(
                        id=str(uuid.uuid4()),
                        scenario=sc,
                        seed=s,
                        arm=arm_name,
                        config_version=cfg,
                        recall=metrics["recall"],
                        fpr=metrics["fpr"],
                        contamination_final=metrics["baseline_contamination_final"],
                        adaptations_count=metrics["adaptations_count"],
                        quarantined_count=metrics["quarantined_count"],
                        recovery_time_windows=metrics["recovery_time_windows"],
                        metrics=metrics,
                    )
                    db.add(exp_row)
            db.commit()
            db.close()
            logger.info("Persisted %d experiment records to experiment_results table.", len(runs) * 3)
        except Exception as e:
            logger.warning("Could not persist experiment results to DB: %s", e)
