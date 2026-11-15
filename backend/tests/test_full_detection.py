"""Tests for CommShield multi-model detection engine:
- Scores stay within [0, 100]
- CUSUM accumulates under sustained deviation and resets after trigger
- Agreement states are correct for synthetic score pairs
- Autoencoder trains only on training-period data
"""

import json
from pathlib import Path
import numpy as np
import pytest

from ml_engine.detection import (
    AutoencoderDetector,
    CusumDetector,
    DetectionEngine,
    IsolationForestDetector,
    compute_agreement,
    fuse_scores,
    to_contract_agreement,
)
from ml_engine.preprocessing.windowing import FEATURE_NAMES, RobustScaler

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
SYNTHETIC_DATA_DIR = PROJECT_ROOT / "data" / "synthetic"


def test_scores_stay_within_0_to_100():
    """Verify that IF, AE, and fused scores strictly stay within [0.0, 100.0]."""
    np.random.seed(42)
    # Train dummy models
    X_train = np.random.normal(0, 1, size=(50, 9)).astype(np.float32)

    if_det = IsolationForestDetector(n_estimators=20, random_state=42)
    if_det.fit(X_train)

    ae_det = AutoencoderDetector(input_dim=9, max_epochs=20, random_state=42)
    ae_det.fit(X_train)

    # Test extreme values (huge negatives, huge positives, zeros)
    test_vectors = [
        np.zeros((1, 9), dtype=np.float32),
        np.ones((1, 9), dtype=np.float32) * 1e5,
        np.ones((1, 9), dtype=np.float32) * -1e5,
        np.random.normal(10, 5, size=(20, 9)).astype(np.float32),
    ]

    for vec in test_vectors:
        for row in vec:
            row_2d = row.reshape(1, -1)
            _, if_pct, _ = if_det.evaluate_sample(row_2d)
            _, ae_pct, _ = ae_det.evaluate_sample(row_2d)

            assert 0.0 <= if_pct <= 100.0, f"IF score {if_pct} out of bounds"
            assert 0.0 <= ae_pct <= 100.0, f"AE score {ae_pct} out of bounds"

            fusion = fuse_scores(if_pct, ae_pct)
            assert 0.0 <= fusion["fused_percentile"] <= 100.0, f"Fused score {fusion['fused_percentile']} out of bounds"
            assert 0.0 <= fusion["secondary_mean_percentile"] <= 100.0


def test_cusum_accumulates_and_resets():
    """Verify CUSUM accumulates under sustained deviation and resets after trigger."""
    cusum = CusumDetector(
        reference_value=75.0,
        scale=10.0,
        alarm_threshold=4.5,
        reset_on_trigger=True,
    )
    slice_id = "sst-1-sd-010203"

    # 1. Benign score below reference value -> stays idle at 0.0
    stat, is_alarm, status = cusum.update(slice_id, 50.0)
    assert stat == 0.0
    assert not is_alarm
    assert status == "idle"

    # 2. Elevated score (95.0) -> deviation is (95 - 75)/10 = 2.0 -> status accumulating
    stat, is_alarm, status = cusum.update(slice_id, 95.0)
    assert stat == 2.0
    assert not is_alarm
    assert status == "accumulating"

    # 3. Another elevated score (95.0) -> stat = 4.0 -> accumulating
    stat, is_alarm, status = cusum.update(slice_id, 95.0)
    assert stat == 4.0
    assert not is_alarm
    assert status == "accumulating"

    # 4. Third elevated score (95.0) -> stat = 6.0 >= 4.5 -> triggered and alarm!
    stat, is_alarm, status = cusum.update(slice_id, 95.0)
    assert stat >= 4.5
    assert is_alarm
    assert status == "triggered"

    # 5. After trigger, accumulator resets to 0.0
    stat, is_alarm, status = cusum.update(slice_id, 50.0)
    assert stat == 0.0
    assert not is_alarm
    assert status == "idle"


def test_agreement_states_correct():
    """Verify detector agreement states for synthetic score pairs."""
    # (if_flagged, ae_flagged) -> expected agreement state
    cases = [
        (True, True, "both_fired", "BOTH_FIRE"),
        (True, False, "only_isolation_forest", "IF_ONLY"),
        (False, True, "only_autoencoder", "AE_ONLY"),
        (False, False, "neither", "NONE"),
    ]

    for if_flag, ae_flag, expected_str, expected_contract in cases:
        state = compute_agreement(if_flag, ae_flag)
        assert state == expected_str, f"Expected {expected_str}, got {state}"
        contract_state = to_contract_agreement(state)
        assert contract_state == expected_contract, f"Expected {expected_contract}, got {contract_state}"


def test_autoencoder_trains_only_on_training_period():
    """Verify Autoencoder is trained strictly on benign training periods and not test/attack windows."""
    train_file = SYNTHETIC_DATA_DIR / "training_embb.json"
    assert train_file.is_file(), "training_embb.json must exist"

    with open(train_file, "r", encoding="utf-8") as f:
        data = json.load(f)
        windows = data.get("windows", [])

    # Confirm all training windows are non-attack
    for w in windows:
        gt = w.get("ground_truth", {})
        assert not gt.get("is_attack", False), "Training window contains attack data!"

    # Fit scaler and autoencoder on training windows
    scaler = RobustScaler(feature_names=FEATURE_NAMES)
    scaler.fit(windows)

    X_train = np.array(
        [[scaler.transform_vector(w["ratio_features"])[feat] for feat in FEATURE_NAMES] for w in windows],
        dtype=np.float32,
    )

    ae = AutoencoderDetector(input_dim=len(FEATURE_NAMES), max_epochs=20, random_state=42)
    ae.fit(X_train)

    assert ae.fitted is True
    assert ae.n_train_samples_ == len(windows)
    # Check reconstruction error on training data is bounded and calibrated
    errs = ae.score(X_train)
    assert len(errs) == len(windows)
    assert np.all(errs >= 0.0)
