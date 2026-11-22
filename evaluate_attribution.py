"""Evaluate drift attribution across all 5 synthetic scenarios and print honest results table."""

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Dict, List
import numpy as np

from ml_engine.attribution import (
    AdwinSliceTracker,
    AttributionEngine,
    RuleBasedAttributor,
)
from ml_engine.detection import DetectionEngine
from ml_engine.preprocessing.windowing import FEATURE_NAMES, RobustScaler
import joblib

PROJECT_ROOT = Path(__file__).resolve().parent
SYNTHETIC_DIR = PROJECT_ROOT / "data" / "synthetic"
BASELINES_DIR = PROJECT_ROOT / "data" / "processed" / "baselines"

SCENARIOS = [
    "stable_benign",
    "legitimate_growth",
    "slow_attack_ramp",
    "attack_in_growth",
    "mimicry_attack",
]


def load_baseline(slice_id: str):
    candidates = list(BASELINES_DIR.glob(f"{slice_id}_*.joblib"))
    if not candidates:
        raise FileNotFoundError(f"No baseline found for {slice_id}")
    return joblib.load(candidates[0])


def evaluate_attribution_scenarios():
    # Cache baselines
    baselines = {}
    for s_id in ["sst-1-sd-010203", "sst-2-sd-010203", "sst-3-sd-010203"]:
        try:
            baselines[s_id] = load_baseline(s_id)
        except Exception:
            pass

    table_rows = []

    for sc_name in SCENARIOS:
        sc_file = SYNTHETIC_DIR / f"{sc_name}.json"
        if not sc_file.is_file():
            continue

        with open(sc_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            windows = data.get("windows", [])

        tracker = AdwinSliceTracker()
        attributor = RuleBasedAttributor()
        history: List[dict] = []

        # Setup detection engine
        det_engines = {}
        for s_id, bundle in baselines.items():
            d_eng = DetectionEngine()
            for name, det in bundle.get("detectors", {}).items():
                d_eng.register_detector(name, det)
            det_engines[s_id] = d_eng

        drift_count = 0
        benign_count = 0
        attack_count = 0
        uncertain_count = 0
        gt_attacks = 0

        for w in windows:
            s_id = w.get("slice_id", "sst-1-sd-010203")
            b_bundle = baselines.get(s_id, list(baselines.values())[0])
            d_eng = det_engines.get(s_id, list(det_engines.values())[0])
            scaler = b_bundle["scaler"]

            gt = w.get("ground_truth", {})
            if gt.get("is_attack", False):
                gt_attacks += 1

            counters = w.get("raw_counters", {})
            total_bytes = float(counters.get("total_bytes_uplink", 0) + counters.get("total_bytes_downlink", 0))

            drift_detected, _ = tracker.update(s_id, total_bytes, w.get("window_id", ""))
            history.append(w)

            # Score detector
            ratios = w.get("ratio_features", {})
            scaled = scaler.transform_vector(ratios)
            x_row = np.array([[scaled[f] for f in FEATURE_NAMES]], dtype=np.float32)
            det_out = d_eng.evaluate_vector(x_row, slice_id=s_id, threshold_percentile=95.0)

            # Evaluate attribution on drift or whenever evaluated
            if drift_detected or w.get("ground_truth", {}).get("is_attack", False) or sc_name == "legitimate_growth":
                if drift_detected:
                    drift_count += 1
                res = attributor.attribute(
                    window=w,
                    baseline_bundle=b_bundle,
                    recent_windows=history[-10:],
                    drift_detected=drift_detected,
                    detector_output=det_out,
                )
                v = res["verdict"]
                if v == "likely_benign":
                    benign_count += 1
                elif v == "likely_attack":
                    attack_count += 1
                else:
                    uncertain_count += 1

        table_rows.append({
            "scenario": sc_name,
            "total_windows": len(windows),
            "gt_attacks": gt_attacks,
            "drift_events": drift_count,
            "benign": benign_count,
            "attack": attack_count,
            "uncertain": uncertain_count,
        })

    # Print Formatted Table
    hdr = f"{'Scenario':<22} | {'Windows (Atk)':<15} | {'Drifts':<8} | {'Benign':<8} | {'Attack':<8} | {'Uncertain':<10}"
    sep = "-" * len(hdr)
    print(sep)
    print(hdr)
    print(sep)
    for r in table_rows:
        win_str = f"{r['total_windows']} ({r['gt_attacks']})"
        print(
            f"{r['scenario']:<22} | "
            f"{win_str:<15} | "
            f"{r['drift_events']:<8} | "
            f"{r['benign']:<8} | "
            f"{r['attack']:<8} | "
            f"{r['uncertain']:<10}"
        )
    print(sep)


if __name__ == "__main__":
    evaluate_attribution_scenarios()
# CommShield AI Core
