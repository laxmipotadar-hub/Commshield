"""Tests for Real 5G-NIDD Evaluation Correctness, Split Integrity, and Determinism.

Per task specifications:
- Tests verify correctness (split integrity, determinism, label alignment), NOT performance targets.
- Verifies non-overlapping chronological bounds for train/val splits.
- Verifies deterministic reproducibility under fixed seeds.
- Verifies clean ground-truth label alignment without data leakage.
"""

from copy import deepcopy
from datetime import datetime
from pathlib import Path
import json
import numpy as np
import pytest

from ml_engine.evaluation.real_evaluator import (
    FixedZScoreDetector,
    load_real_benign_windows,
)
from ml_engine.preprocessing.adapters.fiveg_nidd import (
    BS1_SLICE_ID,
    FiveGNIDDAdapter,
    split_chronologically,
)
from ml_engine.preprocessing.windowing import FEATURE_NAMES

FIXTURE_PATH = Path(__file__).resolve().parent / "fixtures" / "nidd_sample.csv"
RESULTS_DIR = Path(__file__).resolve().parent.parent.parent / "experiments" / "results" / "real"


def test_fixed_zscore_detector_correctness_and_stability():
    """Verify FixedZScoreDetector calculates z-scores, respects thresholds, and avoids div-by-zero."""
    # 5 samples, 3 features; feature 2 has constant value (zero variance)
    X_train = np.array([
        [1.0, 10.0, 5.0],
        [2.0, 20.0, 5.0],
        [3.0, 30.0, 5.0],
        [4.0, 40.0, 5.0],
        [5.0, 50.0, 5.0],
    ], dtype=np.float32)

    detector = FixedZScoreDetector(threshold=2.0)
    detector.fit(X_train)

    assert detector.fitted is True
    assert detector.means is not None
    assert detector.stds is not None
    # Constant feature should have std set to 1.0 to prevent zero division
    assert detector.stds[2] == 1.0

    # Normal point near mean
    X_normal = np.array([[3.0, 30.0, 5.0]], dtype=np.float32)
    pred_normal = detector.predict(X_normal)
    assert not pred_normal[0], "Point near training mean must not be flagged"

    # Extreme outlier (> 2.0 std)
    X_outlier = np.array([[100.0, 30.0, 5.0]], dtype=np.float32)
    pred_outlier = detector.predict(X_outlier)
    assert pred_outlier[0], "Extreme point must be flagged as anomalous"


def test_split_integrity_chronological_non_overlapping():
    """Verify chronological split produces strictly ordered, non-overlapping windows."""
    adapter = FiveGNIDDAdapter()
    records = list(adapter.parse_records(FIXTURE_PATH))
    windows = adapter.adapt(records, slice_id=BS1_SLICE_ID, window_duration_sec=60)
    assert len(windows) >= 3

    train_w, val_w, test_w = split_chronologically(windows, train_ratio=0.5, val_ratio=0.25, benign_only_train=False)

    # Validate split counts
    assert len(train_w) > 0
    assert len(val_w) > 0
    assert len(train_w) + len(val_w) + len(test_w) == len(windows)

    # Validate temporal ordering between train and validation
    train_end = max(datetime.fromisoformat(w["window_end"]) for w in train_w)
    val_start = min(datetime.fromisoformat(w["window_start"]) for w in val_w)
    assert train_end <= val_start, f"Train split end ({train_end}) must precede validation start ({val_start})"

    if test_w:
        val_end = max(datetime.fromisoformat(w["window_end"]) for w in val_w)
        test_start = min(datetime.fromisoformat(w["window_start"]) for w in test_w)
        assert val_end <= test_start, f"Validation end ({val_end}) must precede test start ({test_start})"


def test_label_alignment_and_zero_leakage():
    """Verify ground truth metadata aligns with flow labels and is isolated from features."""
    adapter = FiveGNIDDAdapter(default_attack_threshold=0.05)
    records = list(adapter.parse_records(FIXTURE_PATH))
    windows = adapter.adapt(records, slice_id=BS1_SLICE_ID, window_duration_sec=60)

    for w in windows:
        gt = w["ground_truth"]
        # Ground truth keys exist
        assert "is_attack" in gt
        assert "attack_type" in gt
        assert "malicious_flow_ratio" in gt
        assert isinstance(gt["is_attack"], bool)
        assert 0.0 <= gt["malicious_flow_ratio"] <= 1.0

        # Features must NOT leak ground truth labels
        assert "is_attack" not in w["ratio_features"]
        assert "attack_type" not in w["ratio_features"]
        assert "is_attack" not in w["raw_counters"]
        assert "label" not in w["raw_counters"]
        assert "label" not in w["composition_vector"]


def test_seed_determinism_across_runs():
    """Verify detector predictions and scores are strictly deterministic given a seed."""
    np.random.seed(42)
    X = np.random.randn(20, len(FEATURE_NAMES)).astype(np.float32)

    det1 = FixedZScoreDetector(threshold=2.5)
    det1.fit(X[:10])
    preds1 = det1.predict(X[10:])

    det2 = FixedZScoreDetector(threshold=2.5)
    det2.fit(X[:10])
    preds2 = det2.predict(X[10:])

    np.testing.assert_array_equal(preds1, preds2, err_msg="Z-Score detector must be completely deterministic")


def test_saved_results_schema_and_boundaries():
    """Verify real experiment results exist in experiments/results/real/ and contain valid schema."""
    expected_files = [
        "detection_evaluation.json",
        "growth_attribution.json",
        "governance_evaluation.json",
        "three_arm_summary.json",
        "metadata.json",
    ]
    for fname in expected_files:
        fpath = RESULTS_DIR / fname
        assert fpath.is_file(), f"Expected results file {fname} not found in {RESULTS_DIR}"

    # Verify metadata.json has dataset files, split boundaries, and config version
    with open(RESULTS_DIR / "metadata.json", "r", encoding="utf-8") as f:
        meta = json.load(f)
    assert "dataset_files_used" in meta
    assert len(meta["dataset_files_used"]) > 0
    assert "split_boundaries" in meta
    assert "config_version" in meta
    assert meta["split_boundaries"]["training_windows_count"] > 0
    assert meta["split_boundaries"]["validation_windows_count"] > 0

    # Verify detection_evaluation.json has all attack types and metrics
    with open(RESULTS_DIR / "detection_evaluation.json", "r", encoding="utf-8") as f:
        det = json.load(f)
    assert "attack_evaluations" in det
    for atk_name, atk_res in det["attack_evaluations"].items():
        assert "detectors" in atk_res
        for model in ["commshield", "isolation_forest", "autoencoder", "fixed_zscore"]:
            assert model in atk_res["detectors"]
            assert "recall" in atk_res["detectors"][model]
            assert "fpr" in atk_res["detectors"][model]
            assert "detection_delay_windows" in atk_res["detectors"][model]
# CommShield AI Core
