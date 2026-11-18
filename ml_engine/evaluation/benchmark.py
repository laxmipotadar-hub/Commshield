"""Three-Arm Replay Benchmark Evaluator.

Retrieves empirical evaluation metrics directly from persisted experimental result files
(experiments/results/ and experiments/snapshot/), without hardcoded numbers or mock rules.
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger("commshield.benchmark")
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
RESULTS_DIR = PROJECT_ROOT / "experiments" / "results"
SNAPSHOT_DIR = PROJECT_ROOT / "experiments" / "snapshot"
REAL_RESULTS_DIR = RESULTS_DIR / "real"
REAL_SNAPSHOT_DIR = SNAPSHOT_DIR / "real"


def evaluate_three_arms(dataset_id: str = "5g_nidd_portscan_growth") -> Dict[str, Any]:
    """Retrieve empirical benchmark results across three operational paradigms from saved result files."""
    did = (dataset_id or "5g_nidd_portscan_growth").strip().lower()

    # 1. Real 5G-NIDD Scenarios
    is_real = any(k in did for k in ("real", "5g_nidd", "nidd", "attack_in_scaled_growth", "scaled_benign_growth"))

    if is_real:
        real_file = REAL_RESULTS_DIR / "three_arm_summary.json"
        if not real_file.is_file():
            real_file = REAL_SNAPSHOT_DIR / "three_arm_summary.json"

        if real_file.is_file():
            try:
                with open(real_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                summaries = data.get("summaries", {})

                # Match scenario key
                matched_key = None
                for candidate in (did, "attack_in_scaled_growth", "real_attacks", "real_benign", "scaled_benign_growth"):
                    if candidate in summaries:
                        matched_key = candidate
                        break

                if matched_key and matched_key in summaries:
                    sc_data = summaries[matched_key]
                    arms_data = {}
                    for arm_k, arm_m in sc_data.get("arms", {}).items():
                        name_map = {
                            "arm_a_static": "Static Anchor",
                            "arm_b_naive": "Naive Retraining",
                            "arm_c_commshield": "CommShield Gated Adaptation",
                        }
                        arms_data[arm_k] = {
                            "name": name_map.get(arm_k, arm_k),
                            "recall": arm_m.get("recall_mean"),
                            "false_alarm_rate": arm_m.get("fpr_mean"),
                            "contamination": arm_m.get("contamination_mean"),
                            "adaptations": arm_m.get("adaptations_mean"),
                            "quarantined": arm_m.get("quarantined_mean"),
                            "recovery_time": arm_m.get("recovery_time_mean"),
                        }
                    return {
                        "dataset_id": dataset_id,
                        "data_label": sc_data.get("label", "real"),
                        "arms": arms_data,
                    }
            except Exception as e:
                logger.warning("Error reading real three-arm summary file %s: %s", real_file, e)

    # 2. Synthetic Benchmark Scenarios
    synth_file = RESULTS_DIR / "experiment_summary.json"
    if not synth_file.is_file():
        synth_file = SNAPSHOT_DIR / "experiment_summary.json"

    if synth_file.is_file():
        try:
            with open(synth_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            summaries = data.get("summaries", {})

            matched_key = None
            for candidate in (did, "slow_attack_ramp", "attack_in_growth", "mimicry_attack", "legitimate_growth", "stable_benign"):
                if candidate in summaries:
                    matched_key = candidate
                    break

            if not matched_key:
                matched_key = "attack_in_growth" if "growth" in did else "slow_attack_ramp"

            if matched_key in summaries:
                sc_data = summaries[matched_key]
                arms_data = {}
                for arm_k, arm_m in sc_data.get("arms", {}).items():
                    name_map = {
                        "arm_a_static": "Static Anchor",
                        "arm_b_naive": "Naive Retraining",
                        "arm_c_commshield": "CommShield Gated Adaptation",
                    }
                    arms_data[arm_k] = {
                        "name": name_map.get(arm_k, arm_k),
                        "recall": arm_m.get("recall_mean"),
                        "false_alarm_rate": arm_m.get("fpr_mean"),
                        "contamination": arm_m.get("contamination_mean"),
                        "adaptations": arm_m.get("adaptations_mean"),
                        "quarantined": arm_m.get("quarantined_mean"),
                        "recovery_time": arm_m.get("recovery_time_mean"),
                    }
                return {
                    "dataset_id": dataset_id,
                    "data_label": "synthetic",
                    "arms": arms_data,
                }
        except Exception as e:
            logger.warning("Error reading synthetic summary file %s: %s", synth_file, e)

    # If result files are missing entirely, return empty arms dictionary
    return {
        "dataset_id": dataset_id,
        "arms": {},
    }
