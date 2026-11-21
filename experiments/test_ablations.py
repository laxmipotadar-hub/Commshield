"""Unit tests for Stage S7: Determinism on fixed seed & ablation config flags."""

import json
from pathlib import Path
import sys
import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
backend_path = PROJECT_ROOT / "backend"
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

from ml_engine.evaluation.ablation_runner import (
    BoilingFrogRunner,
    FourWayAblationRunner,
    compute_bootstrap_ci,
)
from ml_engine.governance.checks import DriftBudgetCheck, ProportionalGrowthCheck


def test_ablation_determinism_on_fixed_seed():
    """Verify that ablation runner is strictly deterministic on a fixed seed."""
    frog = BoilingFrogRunner()
    batches_1 = frog.generate_slow_poisoning_steps(num_steps=5, step_increment_sigma=0.35, seed=42)
    batches_2 = frog.generate_slow_poisoning_steps(num_steps=5, step_increment_sigma=0.35, seed=42)

    assert len(batches_1) == len(batches_2) == 5
    for b1, b2 in zip(batches_1, batches_2):
        for w1, w2 in zip(b1, b2):
            assert w1["ratio_features"]["nas_failure_ratio"] == w2["ratio_features"]["nas_failure_ratio"]
            assert w1["ratio_features"]["pfcp_failure_ratio"] == w2["ratio_features"]["pfcp_failure_ratio"]

    # Bootstrap CI determinism
    data = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0]
    m1, l1, u1 = compute_bootstrap_ci(data, random_state=42)
    m2, l2, u2 = compute_bootstrap_ci(data, random_state=42)
    assert (m1, l1, u1) == (m2, l2, u2)


def test_ablation_config_flags_correctly_disable_components():
    """Verify that ablation configurations correctly disable individual governance checks."""
    frog = BoilingFrogRunner()
    four_way = FourWayAblationRunner()
    anchor_bundle = four_way.anchor_bundle

    batches = frog.generate_slow_poisoning_steps(num_steps=8, step_increment_sigma=0.40, seed=42)

    # 1. Step only vs Cumulative budget:
    # Step-only accepts steps because each step is small
    res_step = frog.run_configuration("step_only", batches, anchor_bundle)
    assert res_step["accepted_steps"] >= 6, "Step-only should accept creeping steps"

    # Step + cumulative budget blocks once B_rms is reached
    res_budget = frog.run_configuration("step_plus_budget", batches, anchor_bundle)
    assert res_budget["accepted_steps"] < res_step["accepted_steps"], "Cumulative budget must cap total drift steps"
    assert res_budget["rejection_reason"] == "Cumulative budget exhausted"

    # Full gate blocks early due to normal holdout / proportional growth / canaries
    res_full = frog.run_configuration("full_gate", batches, anchor_bundle)
    assert res_full["accepted_steps"] <= res_budget["accepted_steps"]
