"""Evaluate all 5 synthetic scenarios and compute honest Recall and FPR for:
- Fused detector
- Isolation Forest alone
- Autoencoder alone
"""

import json
from pathlib import Path
from typing import Dict, List, Tuple
import numpy as np

from ml_engine.detection import DetectionEngine, fuse_scores
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


def evaluate_all():
    # Cache baselines by slice
    baselines = {}
    for s_id in ["sst-1-sd-010203", "sst-2-sd-010203", "sst-3-sd-010203"]:
        try:
            baselines[s_id] = load_baseline(s_id)
        except Exception as e:
            pass

    default_bundle = list(baselines.values())[0]

    results = []

    for sc_name in SCENARIOS:
        sc_path = SYNTHETIC_DIR / f"{sc_name}.json"
        if not sc_path.is_file():
            print(f"File not found: {sc_path}")
            continue

        with open(sc_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            windows = data.get("windows", [])

        # Slices in this scenario might have per-slice CUSUM
        # We instantiate a fresh DetectionEngine per slice for the scenario
        engines = {}
        scalers = {}
        for s_id, bundle in baselines.items():
            eng = DetectionEngine()
            for name, det in bundle.get("detectors", {}).items():
                eng.register_detector(name, det)
            engines[s_id] = eng
            scalers[s_id] = bundle["scaler"]

        y_true = []
        pred_if = []
        pred_ae = []
        pred_fused = []

        for w in windows:
            s_id = w.get("slice_id", "sst-1-sd-010203")
            eng = engines.get(s_id, engines.get("sst-1-sd-010203"))
            scaler = scalers.get(s_id, scalers.get("sst-1-sd-010203"))

            gt = w.get("ground_truth", {})
            is_attack = bool(gt.get("is_attack", False))
            y_true.append(is_attack)

            # Extract features
            ratios = w.get("ratio_features", {})
            scaled = scaler.transform_vector(ratios)
            x_row = np.array([[scaled[f] for f in FEATURE_NAMES]], dtype=np.float32)

            res = eng.evaluate_vector(x_row, slice_id=s_id, threshold_percentile=95.0)

            if_flag = res["isolation_forest"]["is_flagged"]
            ae_flag = res["autoencoder"]["is_flagged"]
            fused_flag = res["fusion"]["is_anomalous"] or res["cusum"]["is_alarm"]

            pred_if.append(if_flag)
            pred_ae.append(ae_flag)
            pred_fused.append(fused_flag)

        # Compute metrics
        y_true_arr = np.array(y_true, dtype=bool)
        n_pos = np.sum(y_true_arr)
        n_neg = np.sum(~y_true_arr)

        def calc_metrics(y_pred):
            y_pred_arr = np.array(y_pred, dtype=bool)
            tp = np.sum(y_true_arr & y_pred_arr)
            fp = np.sum((~y_true_arr) & y_pred_arr)
            recall = float(tp / n_pos) if n_pos > 0 else 0.0
            fpr = float(fp / n_neg) if n_neg > 0 else 0.0
            return recall, fpr

        rec_if, fpr_if = calc_metrics(pred_if)
        rec_ae, fpr_ae = calc_metrics(pred_ae)
        rec_fused, fpr_fused = calc_metrics(pred_fused)

        results.append({
            "scenario": sc_name,
            "windows": len(windows),
            "attack_windows": int(n_pos),
            "fused_recall": rec_fused,
            "fused_fpr": fpr_fused,
            "if_recall": rec_if,
            "if_fpr": fpr_if,
            "ae_recall": rec_ae,
            "ae_fpr": fpr_ae,
        })

    # Print Table
    header = f"{'Scenario':<22} | {'Fused Recall':<12} | {'Fused FPR':<10} | {'IF Recall':<10} | {'IF FPR':<8} | {'AE Recall':<10} | {'AE FPR':<8}"
    sep = "-" * len(header)
    print(sep)
    print(header)
    print(sep)
    for r in results:
        rec_f_str = f"{r['fused_recall']*100:.1f}%" if r['attack_windows'] > 0 else "N/A (0 atk)"
        rec_if_str = f"{r['if_recall']*100:.1f}%" if r['attack_windows'] > 0 else "N/A (0 atk)"
        rec_ae_str = f"{r['ae_recall']*100:.1f}%" if r['attack_windows'] > 0 else "N/A (0 atk)"

        print(
            f"{r['scenario']:<22} | "
            f"{rec_f_str:<12} | "
            f"{r['fused_fpr']*100:.1f}%{'':<5} | "
            f"{rec_if_str:<10} | "
            f"{r['if_fpr']*100:.1f}%{'':<3} | "
            f"{rec_ae_str:<10} | "
            f"{r['ae_fpr']*100:.1f}%"
        )
    print(sep)


if __name__ == "__main__":
    evaluate_all()
