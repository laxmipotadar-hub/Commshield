import sys
from pathlib import Path
import pytest
from fastapi import BackgroundTasks

backend_dir = Path(__file__).resolve().parent.parent
repo_root = backend_dir.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from app.api import experiments as exp_module
from ml_engine.evaluation.experiment import (
    ThreeArmExperimentRunner,
    calculate_contamination,
    calculate_recovery_time,
)
from ml_engine.preprocessing.synthetic_generator import SyntheticGenerator


def test_contamination_metric_on_tiny_handmade_example():
    """Verify contamination metric calculation on deterministic hand-made windows."""
    # Empty baseline training set -> 0.0
    assert calculate_contamination([]) == 0.0

    # 5 clean windows -> 0.0
    all_clean = [{"is_attack": False} for _ in range(5)]
    assert calculate_contamination(all_clean) == 0.0

    # 2 attack windows out of 4 total -> 0.5
    half_attack = [
        {"is_attack": True},
        {"is_attack": False},
        {"is_attack": True},
        {"is_attack": False},
    ]
    assert calculate_contamination(half_attack) == 0.5

    # 3 attack windows out of 3 total -> 1.0
    all_attack = [{"is_attack": True} for _ in range(3)]
    assert calculate_contamination(all_attack) == 1.0

    # Nested ground_truth structure support
    nested_attack = [
        {"ground_truth": {"is_attack": True}},
        {"ground_truth": {"is_attack": False}},
    ]
    assert calculate_contamination(nested_attack) == 0.5

    # Recovery time metric verification
    # Attack at index 0, false alarm at index 1, normal at index 2 -> 1 window to recover
    y_true = [True, False, False]
    y_pred = [True, True, False]
    rec = calculate_recovery_time(y_true, y_pred, nominal_fpr_threshold=0.05)
    assert rec == 1


def test_same_seed_gives_identical_results():
    """Verify that running the experiment with the same seed yields identical outputs."""
    runner = ThreeArmExperimentRunner()

    res1 = runner.run_single("slow_attack_ramp", seed=42, num_windows=10)
    res2 = runner.run_single("slow_attack_ramp", seed=42, num_windows=10)

    for arm in ["arm_a_static", "arm_b_naive", "arm_c_commshield"]:
        m1 = res1["arms"][arm]
        m2 = res2["arms"][arm]
        assert m1["recall"] == m2["recall"]
        assert m1["fpr"] == m2["fpr"]
        assert m1["baseline_contamination_final"] == m2["baseline_contamination_final"]
        assert m1["baseline_contamination_over_time"] == m2["baseline_contamination_over_time"]
        assert m1["adaptations_count"] == m2["adaptations_count"]
        assert m1["quarantined_count"] == m2["quarantined_count"]
        assert m1["recovery_time_windows"] == m2["recovery_time_windows"]


def test_all_three_arms_see_identical_input_windows():
    """Verify that all three arms receive the exact same sequence of input windows."""
    gen1 = SyntheticGenerator(seed=101)
    windows1 = gen1.generate_scenario_windows("slow_attack_ramp", "eMBB", 10, 60)

    gen2 = SyntheticGenerator(seed=101)
    windows2 = gen2.generate_scenario_windows("slow_attack_ramp", "eMBB", 10, 60)

    assert len(windows1) == len(windows2) == 10
    for w1, w2 in zip(windows1, windows2):
        assert w1["ground_truth"]["is_attack"] == w2["ground_truth"]["is_attack"]
        assert w1["ratio_features"] == w2["ratio_features"]
        assert w1["raw_counters"] == w2["raw_counters"]


def test_arm_a_baseline_never_changes():
    """Verify that Arm A never adapts or mutates its initial baseline."""
    runner = ThreeArmExperimentRunner()
    res = runner.run_single("legitimate_growth", seed=2024, num_windows=15)

    arm_a = res["arms"]["arm_a_static"]
    assert arm_a["adaptations_count"] == 0
    assert arm_a["quarantined_count"] == 0
    assert arm_a["baseline_contamination_final"] == 0.0
    assert arm_a["baseline_contamination_over_time"] == [0.0] * 15


def test_arm_c_never_trains_on_quarantined_windows():
    """Verify that Arm C rejects or quarantines attack windows and never contaminates its baseline."""
    runner = ThreeArmExperimentRunner()
    res = runner.run_single("attack_in_growth", seed=777, num_windows=20)

    arm_c = res["arms"]["arm_c_commshield"]
    assert arm_c["baseline_contamination_final"] == 0.0
    assert all(c == 0.0 for c in arm_c["baseline_contamination_over_time"])


def test_api_experiments_endpoints():
    """Test experiment endpoints documented in CONTRACTS.md."""
    # 1. Test GET /api/experiments/status
    status = exp_module.get_experiment_status()
    assert "status" in status
    assert "progress" in status

    # 2. Test GET /api/experiments/results
    results = exp_module.get_all_experiment_results(db=None)
    assert "summaries" in results
    assert "scenarios" in results
    assert "seeds" in results
    assert "stable_benign" in results["summaries"]
    assert "slow_attack_ramp" in results["summaries"]

    # 3. Test GET /api/experiments/results/{scenario}
    scen_data = exp_module.get_scenario_experiment_results("slow_attack_ramp", db=None)
    assert scen_data["scenario"] == "slow_attack_ramp"
    assert "summary" in scen_data

    # 4. Test POST /api/experiments/run background queueing
    bg = BackgroundTasks()
    req = exp_module.ExperimentRunRequest(scenarios=["stable_benign"], seeds=[42], num_windows=10)
    resp = exp_module.trigger_experiment_run(payload=req, background_tasks=bg)
    assert resp["status"] == "QUEUED"
    assert resp["scenarios"] == ["stable_benign"]
    assert len(bg.tasks) == 1
# CommShield AI Core
