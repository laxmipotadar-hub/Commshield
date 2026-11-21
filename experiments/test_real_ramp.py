"""Tests for Stage Q2: Real-backbone hidden ramp scenario and governance benchmark."""

from pathlib import Path
import sys
import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ml_engine.scenarios.real_ramp_generator import (
    RealBackboneHiddenRampScenario,
    run_real_backbone_hidden_ramp_benchmark,
)

RESULTS_FILE = PROJECT_ROOT / "experiments" / "results" / "real_ramp" / "real_ramp_summary.json"


def test_no_test_window_in_baseline_training_data():
    """Verify strict chronological non-overlapping separation between train and test windows."""
    scenario = RealBackboneHiddenRampScenario()
    train_ids = set(w["window_id"] for w in scenario.train_windows)
    val_ids = set(w["window_id"] for w in scenario.val_windows)
    test_ids = set(w["window_id"] for w in scenario.test_benign_windows)

    # Disjointness checks
    assert train_ids.isdisjoint(val_ids), "Training and validation windows must be strictly disjoint"
    assert train_ids.isdisjoint(test_ids), "Training and test windows must be strictly disjoint (zero test leakage)"
    assert val_ids.isdisjoint(test_ids), "Validation and test windows must be strictly disjoint"


def test_scenario_generation_and_label_alignment():
    """Verify generated semi-synthetic windows have correct ground truth labels and schema compliance."""
    scenario = RealBackboneHiddenRampScenario()
    windows = scenario.generate(seed=42, num_windows=40, scale_factor=2.0)

    assert len(windows) == 40
    # Windows 0..9: nominal benign
    for idx in range(10):
        w = windows[idx]
        assert w["ground_truth"]["is_growth"] is False
        assert w["ground_truth"]["is_attack"] is False
        assert w["ground_truth"]["label"] == "benign"

    # Windows 10..19: approved growth, benign
    for idx in range(10, 20):
        w = windows[idx]
        assert w["ground_truth"]["is_growth"] is True
        assert w["ground_truth"]["is_attack"] is False
        assert w["ground_truth"]["label"] == "benign"

    # Windows 20..34: hidden attack ramp inside growth
    for idx in range(20, 35):
        w = windows[idx]
        assert w["ground_truth"]["is_growth"] is True
        assert w["ground_truth"]["is_attack"] is True
        assert w["ground_truth"]["label"] == "attack"
        assert w["ground_truth"]["attack_type"] == "SYNFlood"

    # Windows 35..39: post-attack clean growth
    for idx in range(35, 40):
        w = windows[idx]
        assert w["ground_truth"]["is_growth"] is True
        assert w["ground_truth"]["is_attack"] is False
        assert w["ground_truth"]["label"] == "benign"


def test_scenario_determinism_across_fixed_seeds():
    """Verify that identical seeds produce bitwise-identical feature vectors and metrics."""
    scenario = RealBackboneHiddenRampScenario()
    wins_a = scenario.generate(seed=101, num_windows=40, scale_factor=2.0)
    wins_b = scenario.generate(seed=101, num_windows=40, scale_factor=2.0)

    assert len(wins_a) == len(wins_b) == 40
    for wa, wb in zip(wins_a, wins_b):
        assert wa["window_id"] == wb["window_id"]
        assert wa["raw_counters"] == wb["raw_counters"]
        assert wa["ratio_features"] == wb["ratio_features"]
        assert wa["ground_truth"] == wb["ground_truth"]


def test_saved_real_ramp_summary_results():
    """Verify saved real_ramp_summary.json exists, carries source tag, window counts, and intervals."""
    assert RESULTS_FILE.is_file(), f"Missing {RESULTS_FILE}"
    import json
    with open(RESULTS_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data.get("source") == "semi_synthetic"
    assert data.get("slices_assigned") is True
    assert "seeds" in data and len(data["seeds"]) >= 5
    assert "window_counts" in data
    assert data["window_counts"]["attack_windows"] == 15
    assert data["window_counts"]["benign_windows"] == 25

    arms = data.get("arms", {})
    assert "arm_a_static" in arms
    assert "arm_b_naive" in arms
    assert "arm_c_commshield" in arms

    # Arm B should exhibit positive contamination, Arm C should exhibit 0.0% contamination
    assert arms["arm_b_naive"]["contamination_mean"] > 0.0
    assert arms["arm_c_commshield"]["contamination_mean"] == 0.0
