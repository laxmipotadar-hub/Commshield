"""Trainer and Evaluator for Per-Device Behavior Models with Conformal Abstention."""

from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from ml_engine.provisioning.schema import validate_device_window
from .isolation_forest import DeviceIsolationForest
from .conformal import (
    DEFAULT_ALPHA_LOW,
    DEFAULT_ALPHA_HIGH,
    compute_conformal_pvalue,
    evaluate_device_verdict,
)

HELD_OUT_CLASS: str = "AGV"
TRAINED_CLASSES: List[str] = ["sensor", "camera"]

FEATURE_NAMES: List[str] = [
    "packets_per_sec",
    "bytes_uplink_per_sec",
    "bytes_downlink_per_sec",
    "events_per_sec",
    "bytes_per_packet",
    "uplink_byte_ratio",
    "failure_ratio",
]


def extract_device_features(window: Dict[str, Any]) -> List[float]:
    """Extract standard normalized feature vector from a per-device canonical window."""
    validate_device_window(window)
    rf = window["rate_features"]
    rt = window["ratio_features"]
    return [
        float(rf["packets_per_sec"]),
        float(rf["bytes_uplink_per_sec"]),
        float(rf["bytes_downlink_per_sec"]),
        float(rf["events_per_sec"]),
        float(rt["bytes_per_packet"]),
        float(rt["uplink_byte_ratio"]),
        float(rt["failure_ratio"]),
    ]


class DeviceModelManager:
    """Manages per-device class Isolation Forests and split-conformal calibration sets."""

    def __init__(
        self,
        n_estimators: int = 25,
        max_depth: int = 6,
        random_state: int = 42,
        alpha_low: float = DEFAULT_ALPHA_LOW,
        alpha_high: float = DEFAULT_ALPHA_HIGH,
    ):
        self.n_estimators = n_estimators
        self.max_depth = max_depth
        self.random_state = random_state
        self.alpha_low = alpha_low
        self.alpha_high = alpha_high

        self.models: Dict[str, DeviceIsolationForest] = {}
        self.calibration_scores: Dict[str, List[float]] = {}
        self.calibration_sizes: Dict[str, int] = {}
        self.smallest_pvalues: Dict[str, float] = {}

        # Audit tracking for disjoint sets
        self.split_window_ids: Dict[str, Dict[str, Set[str]]] = {}

    def fit_and_calibrate(
        self,
        tuning_device_windows: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Fit models on benign training split and calibrate on disjoint calibration split."""
        # 1. Filter benign windows and group by device class
        benign_by_class: Dict[str, List[Dict[str, Any]]] = {
            "sensor": [],
            "camera": [],
            "AGV": [],
        }

        for w in tuning_device_windows:
            validate_device_window(w)
            if not w["ground_truth"]["is_attack"]:
                cls = w["device_class"]
                if cls in benign_by_class:
                    benign_by_class[cls].append(w)

        report: Dict[str, Any] = {
            "held_out_class": HELD_OUT_CLASS,
            "trained_classes": TRAINED_CLASSES,
            "model_params": {
                "n_estimators": self.n_estimators,
                "max_depth": self.max_depth,
                "random_state": self.random_state,
                "alpha_low": self.alpha_low,
                "alpha_high": self.alpha_high,
            },
            "class_details": {},
        }

        # 2. Process each class
        for cls in TRAINED_CLASSES:
            windows = benign_by_class[cls]
            n_tot = len(windows)
            if n_tot < 10:
                raise ValueError(f"Insufficient benign windows for class {cls}: {n_tot}")

            # 50% train, 25% threshold, 25% calibration
            n_train = int(n_tot * 0.50)
            n_thresh = int(n_tot * 0.25)
            
            train_set = windows[:n_train]
            thresh_set = windows[n_train:n_train + n_thresh]
            cal_set = windows[n_train + n_thresh:]

            train_ids = {w["window_id"] for w in train_set}
            thresh_ids = {w["window_id"] for w in thresh_set}
            cal_ids = {w["window_id"] for w in cal_set}

            # Verify strict disjointness
            assert train_ids.isdisjoint(cal_ids), f"Train and cal IDs overlap in {cls}"
            assert train_ids.isdisjoint(thresh_ids), f"Train and thresh IDs overlap in {cls}"
            assert cal_ids.isdisjoint(thresh_ids), f"Cal and thresh IDs overlap in {cls}"

            self.split_window_ids[cls] = {
                "train_ids": train_ids,
                "thresh_ids": thresh_ids,
                "cal_ids": cal_ids,
            }

            # Fit Isolation Forest on train_set
            train_X = [extract_device_features(w) for w in train_set]
            model = DeviceIsolationForest(
                n_estimators=self.n_estimators,
                max_depth=self.max_depth,
                random_state=self.random_state + (hash(cls) % 1000),
            )
            model.fit(train_X)
            self.models[cls] = model

            # Calibrate on cal_set
            cal_X = [extract_device_features(w) for w in cal_set]
            cal_scores = model.score_samples(cal_X)
            self.calibration_scores[cls] = sorted(cal_scores)
            
            n_cal = len(cal_scores)
            self.calibration_sizes[cls] = n_cal
            smallest_p = round(1.0 / float(n_cal + 1), 6)
            self.smallest_pvalues[cls] = smallest_p

            report["class_details"][cls] = {
                "total_benign_windows": n_tot,
                "n_train": len(train_set),
                "n_threshold": len(thresh_set),
                "n_calibration": n_cal,
                "smallest_possible_pvalue": smallest_p,
            }

        # Document held out class explicitly
        report["class_details"][HELD_OUT_CLASS] = {
            "status": "HELD_OUT_FROM_TRAINING",
            "total_benign_windows": len(benign_by_class[HELD_OUT_CLASS]),
            "n_train": 0,
            "n_calibration": 0,
            "smallest_possible_pvalue": None,
        }

        return report

    def predict_window(self, window: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluate a per-device window returning split-conformal verdict and p-value."""
        validate_device_window(window)
        dev_class = window["device_class"]
        source = window.get("source", "simulated_twin")

        if dev_class == HELD_OUT_CLASS or dev_class not in self.models:
            verdict, reason = evaluate_device_verdict(
                p_value=0.5,
                is_held_out=True,
                alpha_low=self.alpha_low,
                alpha_high=self.alpha_high,
            )
            return {
                "window_id": window["window_id"],
                "source": source,
                "device_id_hash": window["device_id_hash"],
                "device_class": dev_class,
                "slice_id": window["slice_id"],
                "score": 0.5,
                "p_value": 0.5,
                "verdict": verdict,
                "abstain_reason": reason,
                "ground_truth": window["ground_truth"],
            }

        feats = extract_device_features(window)
        model = self.models[dev_class]
        cal_scores = self.calibration_scores[dev_class]

        test_score = model.score(feats)
        p_val = compute_conformal_pvalue(test_score, cal_scores)
        verdict, reason = evaluate_device_verdict(
            p_value=p_val,
            is_held_out=False,
            alpha_low=self.alpha_low,
            alpha_high=self.alpha_high,
        )

        return {
            "window_id": window["window_id"],
            "source": source,
            "device_id_hash": window["device_id_hash"],
            "device_class": dev_class,
            "slice_id": window["slice_id"],
            "score": round(test_score, 6),
            "p_value": p_val,
            "verdict": verdict,
            "abstain_reason": reason,
            "ground_truth": window["ground_truth"],
        }
# CommShield AI Core
