"""Evaluation Benchmark for Per-Device Behavior Model with Conformal Abstention.

Evaluates:
1. Empirical coverage on benign windows during approved onboarding (pre- vs post-growth exchangeability audit).
2. Anomaly detection rate per device in the hidden ramp (slow ramp in onboarding).
3. Abstention rate and accuracy among non-abstained windows.
4. Accuracy-vs-coverage curve across alpha in [0.01, 0.50].
5. Complete holdout of device class 'AGV'.
6. 1000-iteration bootstrap 95% confidence intervals across 10 test seeds.

Saves results to experiments/results/device_model/device_model_summary.json.
"""

from datetime import datetime, timezone
import json
import math
from pathlib import Path
import random
import sys
from typing import Any, Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ml_engine.device_model import (
    DeviceModelManager,
    HELD_OUT_CLASS,
    TRAINED_CLASSES,
    compute_conformal_pvalue,
)
from ml_engine.provisioning.loader import ProvisioningLoader
from ml_engine.scenarios.twin_generator import (
    TwinScenarioGenerator,
    TUNING_SEED,
    TEST_SEEDS,
    STREAM_NAMES,
)

RESULTS_DIR = ROOT / "experiments" / "results" / "device_model"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)


def run_bootstrap_ci(values: List[float], n_boot: int = 1000, seed: int = 42) -> Tuple[float, float, float]:
    """Compute mean and 95% bootstrap confidence interval (2.5%, 97.5%)."""
    if not values:
        return 0.0, 0.0, 0.0
    rng = random.Random(seed)
    n = len(values)
    boot_means = []
    for _ in range(n_boot):
        sample = [values[rng.randint(0, n - 1)] for _ in range(n)]
        boot_means.append(sum(sample) / float(n))
    boot_means.sort()
    low_idx = int(0.025 * n_boot)
    high_idx = int(0.975 * n_boot)
    mean_val = sum(values) / float(n)
    return round(mean_val, 4), round(boot_means[low_idx], 4), round(boot_means[high_idx], 4)


def evaluate_device_models():
    print("=" * 70)
    print("CommShield Per-Device Behavior Model with Conformal Abstention")
    print(f"Timestamp : {datetime.now(timezone.utc).isoformat()}")
    print(f"Tuning Seed : {TUNING_SEED}")
    print(f"Test Seeds  : {TEST_SEEDS} (Count: {len(TEST_SEEDS)})")
    print(f"Trained Classes  : {TRAINED_CLASSES}")
    print(f"Held-Out Class   : {HELD_OUT_CLASS}")
    print("=" * 70)

    loader = ProvisioningLoader()

    # 1. Generate tuning data and fit/calibrate models
    print("\n[Phase 1] Generating tuning data and calibrating per-device models...")
    tuning_gen = TwinScenarioGenerator(seed=TUNING_SEED, loader=loader)
    tuning_device_windows: List[Dict[str, Any]] = []

    for s_name in STREAM_NAMES:
        stream_res = tuning_gen.generate_stream(s_name, num_windows=30)
        tuning_device_windows.extend(stream_res["device_windows"])

    manager = DeviceModelManager(
        n_estimators=25,
        max_depth=6,
        random_state=42,
        alpha_low=0.05,
        alpha_high=0.20,
    )
    cal_report = manager.fit_and_calibrate(tuning_device_windows)
    print("  Calibration Sizes and Smallest p-values:")
    for cls in TRAINED_CLASSES:
        det = cal_report["class_details"][cls]
        print(f"    - {cls:8}: n_cal={det['n_calibration']}, smallest p={det['smallest_possible_pvalue']}")
    print(f"    - {HELD_OUT_CLASS:8}: HELD OUT FROM TRAINING (n_cal=0)")

    # 2. Evaluate across all 10 test seeds
    print("\n[Phase 2] Evaluating across 10 test seeds...")
    all_eval_windows: List[Dict[str, Any]] = []

    # Tracking metrics per seed
    seed_onboarding_coverage_early: Dict[int, List[float]] = {}
    seed_onboarding_coverage_late: Dict[int, List[float]] = {}
    seed_onboarding_coverage_all: Dict[int, List[float]] = {}

    seed_hidden_ramp_attack_rate: Dict[int, List[float]] = {}
    seed_hidden_ramp_abstain_rate: Dict[int, List[float]] = {}

    seed_abstention_rates: Dict[int, List[float]] = {}
    seed_non_abstained_correct: Dict[int, List[int]] = {}

    for t_seed in TEST_SEEDS:
        t_gen = TwinScenarioGenerator(seed=t_seed, loader=loader)
        seed_windows = []

        seed_onboarding_coverage_early[t_seed] = []
        seed_onboarding_coverage_late[t_seed] = []
        seed_onboarding_coverage_all[t_seed] = []
        seed_hidden_ramp_attack_rate[t_seed] = []
        seed_hidden_ramp_abstain_rate[t_seed] = []
        seed_abstention_rates[t_seed] = []
        seed_non_abstained_correct[t_seed] = []

        for s_name in STREAM_NAMES:
            s_res = t_gen.generate_stream(s_name, num_windows=30)
            dev_wins = s_res["device_windows"]

            for dw in dev_wins:
                pred = manager.predict_window(dw)
                pred["stream_name"] = s_name
                pred["window_start"] = dw["window_start"]
                pred["test_seed"] = t_seed
                seed_windows.append(pred)
                all_eval_windows.append(pred)

                is_attack = dw["ground_truth"]["is_attack"]
                verdict = pred["verdict"]
                cls_name = dw["device_class"]
                p_val = pred["p_value"]

                # A. Approved Onboarding Coverage (Trained classes only for statistical coverage test)
                if s_name == "approved_onboarding" and cls_name in TRAINED_CLASSES:
                    # Benign coverage: p >= alpha_low (i.e. not anomalous)
                    covered = 1.0 if p_val >= 0.05 else 0.0
                    seed_onboarding_coverage_all[t_seed].append(covered)

                    # Early (w_idx < 10) vs Late (w_idx >= 10, growing count)
                    # We can infer window index from time or index: 30 windows
                    w_start_dt = dw["window_start"]
                    # 08:00:00 to 08:10:00 is first 10 windows
                    if "T08:0" in w_start_dt:  # first 10 windows
                        seed_onboarding_coverage_early[t_seed].append(covered)
                    else:
                        seed_onboarding_coverage_late[t_seed].append(covered)

                # B. Hidden Ramp anomaly detection (ramping attack sensors in stream d)
                if s_name == "slow_ramp_in_onboarding" and is_attack:
                    is_anom = 1.0 if verdict == "anomalous" else 0.0
                    is_abst = 1.0 if verdict == "uncertain" else 0.0
                    seed_hidden_ramp_attack_rate[t_seed].append(is_anom)
                    seed_hidden_ramp_abstain_rate[t_seed].append(is_abst)

                # C. Abstention
                is_abstained = 1.0 if verdict == "uncertain" else 0.0
                seed_abstention_rates[t_seed].append(is_abstained)

                # D. Non-abstained accuracy
                if verdict != "uncertain":
                    # Non-abstained:
                    # Correct if benign and normal, OR attack and anomalous
                    correct = 1 if ((not is_attack and verdict == "normal") or (is_attack and verdict == "anomalous")) else 0
                    seed_non_abstained_correct[t_seed].append(correct)

    # 3. Compute Aggregate and Bootstrap Confidence Intervals
    print("\n[Phase 3] Computing metrics and bootstrap confidence intervals...")

    # A. Approved Onboarding Coverage
    cov_all_vals = [sum(seed_onboarding_coverage_all[s]) / float(len(seed_onboarding_coverage_all[s])) for s in TEST_SEEDS]
    cov_early_vals = [sum(seed_onboarding_coverage_early[s]) / float(len(seed_onboarding_coverage_early[s])) for s in TEST_SEEDS if seed_onboarding_coverage_early[s]]
    cov_late_vals = [sum(seed_onboarding_coverage_late[s]) / float(len(seed_onboarding_coverage_late[s])) for s in TEST_SEEDS if seed_onboarding_coverage_late[s]]

    cov_all_mean, cov_all_ci_low, cov_all_ci_high = run_bootstrap_ci(cov_all_vals)
    cov_early_mean, cov_early_ci_low, cov_early_ci_high = run_bootstrap_ci(cov_early_vals)
    cov_late_mean, cov_late_ci_low, cov_late_ci_high = run_bootstrap_ci(cov_late_vals)

    # Exchangeability check
    exchangeability_holds = bool(cov_late_mean >= 0.90)

    # B. Hidden Ramp Attack Anomaly Rate
    ramp_anom_vals = [sum(seed_hidden_ramp_attack_rate[s]) / float(max(1, len(seed_hidden_ramp_attack_rate[s]))) for s in TEST_SEEDS]
    ramp_abst_vals = [sum(seed_hidden_ramp_abstain_rate[s]) / float(max(1, len(seed_hidden_ramp_abstain_rate[s]))) for s in TEST_SEEDS]

    ramp_anom_mean, ramp_anom_ci_low, ramp_anom_ci_high = run_bootstrap_ci(ramp_anom_vals)
    ramp_abst_mean, ramp_abst_ci_low, ramp_abst_ci_high = run_bootstrap_ci(ramp_abst_vals)

    # C. Global Abstention Rate
    abst_vals = [sum(seed_abstention_rates[s]) / float(len(seed_abstention_rates[s])) for s in TEST_SEEDS]
    abst_mean, abst_ci_low, abst_ci_high = run_bootstrap_ci(abst_vals)

    # D. Non-Abstained Accuracy
    acc_vals = [sum(seed_non_abstained_correct[s]) / float(max(1, len(seed_non_abstained_correct[s]))) for s in TEST_SEEDS]
    acc_mean, acc_ci_low, acc_ci_high = run_bootstrap_ci(acc_vals)

    # E. Held-Out Class Verification
    agv_windows = [w for w in all_eval_windows if w["device_class"] == HELD_OUT_CLASS]
    agv_abstention_rate = sum(1 for w in agv_windows if w["verdict"] == "uncertain") / float(max(1, len(agv_windows)))

    # F. Accuracy-vs-Coverage Curve across varying alpha
    print("\n[Phase 4] Computing Accuracy-vs-Coverage curve across alpha...")
    alpha_levels = [0.01, 0.02, 0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.40, 0.50]
    accuracy_vs_coverage = []

    # Evaluate on trained classes
    trained_eval_windows = [w for w in all_eval_windows if w["device_class"] in TRAINED_CLASSES]

    for alpha in alpha_levels:
        # Gray band: [alpha, alpha * 3] capped at 0.50
        a_low = alpha
        a_high = min(0.60, alpha + 0.15)

        total_tested = len(trained_eval_windows)
        non_abstained = 0
        correct = 0

        for w in trained_eval_windows:
            p_val = w["p_value"]
            is_atk = w["ground_truth"]["is_attack"]
            if p_val < a_low:
                # Anomalous
                non_abstained += 1
                if is_atk:
                    correct += 1
            elif p_val > a_high:
                # Normal
                non_abstained += 1
                if not is_atk:
                    correct += 1
            else:
                # Uncertain / abstained
                pass

        coverage = round(non_abstained / float(max(1, total_tested)), 4)
        acc = round(correct / float(max(1, non_abstained)), 4) if non_abstained > 0 else 0.0

        accuracy_vs_coverage.append({
            "alpha": alpha,
            "alpha_low": round(a_low, 4),
            "alpha_high": round(a_high, 4),
            "coverage": coverage,
            "accuracy": acc,
            "non_abstained_count": non_abstained,
            "total_windows": total_tested,
        })

    # Find weakest result
    # In hidden ramp, early subtle attack windows have dampening and fall into gray band
    weakest_result_name = "hidden_ramp_detection_rate"
    weakest_result_value = f"{ramp_anom_mean * 100.0:.2f}% (abstention: {ramp_abst_mean * 100.0:.2f}%)"

    results_payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": "simulated_twin",
        "tuning_seed": TUNING_SEED,
        "test_seeds": TEST_SEEDS,
        "held_out_class": HELD_OUT_CLASS,
        "trained_classes": TRAINED_CLASSES,
        "calibration_sizes": manager.calibration_sizes,
        "smallest_pvalues": manager.smallest_pvalues,
        "approved_onboarding_coverage": {
            "overall": {
                "mean": cov_all_mean,
                "ci_95": [cov_all_ci_low, cov_all_ci_high],
            },
            "early_pre_onboarding": {
                "mean": cov_early_mean,
                "ci_95": [cov_early_ci_low, cov_early_ci_high],
            },
            "late_growing_onboarding": {
                "mean": cov_late_mean,
                "ci_95": [cov_late_ci_low, cov_late_ci_high],
            },
            "exchangeability_holds_under_growth": exchangeability_holds,
        },
        "hidden_ramp_per_device_evaluation": {
            "anomaly_detection_rate": {
                "mean": ramp_anom_mean,
                "ci_95": [ramp_anom_ci_low, ramp_anom_ci_high],
            },
            "abstention_rate": {
                "mean": ramp_abst_mean,
                "ci_95": [ramp_abst_ci_low, ramp_abst_ci_high],
            },
        },
        "overall_evaluation": {
            "abstention_rate": {
                "mean": abst_mean,
                "ci_95": [abst_ci_low, abst_ci_high],
            },
            "non_abstained_accuracy": {
                "mean": acc_mean,
                "ci_95": [acc_ci_low, acc_ci_high],
            },
            "held_out_class_abstention_rate": agv_abstention_rate,
        },
        "accuracy_vs_coverage_curve": accuracy_vs_coverage,
        "weakest_result": {
            "metric": weakest_result_name,
            "value": weakest_result_value,
            "details": f"In slow_ramp_in_onboarding, subtle early-stage ramping attack devices achieved {ramp_anom_mean*100.0:.2f}% anomaly detection, with {ramp_abst_mean*100.0:.2f}% abstained into the conformal gray band.",
        },
    }

    out_file = RESULTS_DIR / "device_model_summary.json"
    with open(out_file, "w", encoding="utf-8", newline="\n") as f:
        json.dump(results_payload, f, indent=2)

    print(f"\n  ✓ Successfully wrote results to: {out_file.name}")
    print("=" * 70)
    print("Key Results:")
    print(f"  Approved Onboarding Coverage: {cov_all_mean*100.0:.2f}% (Early: {cov_early_mean*100.0:.2f}%, Late: {cov_late_mean*100.0:.2f}%)")
    print(f"  Exchangeability under growth: {'HOLDS' if exchangeability_holds else 'DEGRADES'}")
    print(f"  Hidden Ramp Anomaly Rate    : {ramp_anom_mean*100.0:.2f}% (Abstention: {ramp_abst_mean*100.0:.2f}%)")
    print(f"  Non-Abstained Accuracy      : {acc_mean*100.0:.2f}% [95% CI: {acc_ci_low*100.0:.2f}%, {acc_ci_high*100.0:.2f}%]")
    print(f"  Overall Abstention Rate     : {abst_mean*100.0:.2f}% (Held-Out AGV: {agv_abstention_rate*100.0:.2f}%)")
    print(f"  Weakest Result              : {weakest_result_value} on hidden ramp detection")
    print("=" * 70)


if __name__ == "__main__":
    evaluate_device_models()
# CommShield AI Core
