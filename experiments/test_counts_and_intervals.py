"""Tests for Stage Q1: Counts, intervals, honest groups, and deterministic Wilson intervals."""

import json
from pathlib import Path
import sys
import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ml_engine.evaluation.metrics import (
    compute_metric_ci,
    partition_real_attacks,
    wilson_score_interval,
    DATA_FACT_REASONS,
)
REAL_RESULTS_DIR = PROJECT_ROOT / "experiments" / "results" / "real"
EXP_SUMMARY_PATH = PROJECT_ROOT / "experiments" / "results" / "experiment_summary.json"


def test_wilson_interval_exactness_and_determinism():
    """Verify Wilson score intervals are strictly deterministic and mathematically bounded."""
    # Test k=8, n=11 (SlowrateDoS)
    low1, high1 = wilson_score_interval(8, 11)
    low2, high2 = wilson_score_interval(8, 11)
    assert low1 == low2 == 0.4344
    assert high1 == high2 == 0.9025
    assert 0.0 <= low1 <= high1 <= 1.0

    # Test edge case k=0, n=10 (ICMPFlood)
    low_zero, high_zero = wilson_score_interval(0, 10)
    assert low_zero == 0.0
    assert high_zero == 0.2775

    # Test edge case k=10, n=10
    low_full, high_full = wilson_score_interval(10, 10)
    assert low_full == 0.7225
    assert high_full == 1.0


def test_metric_ci_formatting_handles_small_sample_sizes():
    """Verify that n < 10 displays 'n=<count>, interval too wide to interpret'."""
    # n = 4 (< 10)
    res_small = compute_metric_ci(1.0, 4, is_proportion=True)
    assert res_small["ci"] is None
    assert "interval too wide to interpret" in res_small["ci_text"]
    assert "n=4" in res_small["ci_text"]

    # n = 11 (>= 10)
    res_large = compute_metric_ci(0.7273, 11, is_proportion=True)
    assert res_large["ci"] is not None
    assert isinstance(res_large["ci"], tuple)
    assert len(res_large["ci"]) == 2
    assert "95% CI" in res_large["display"]


def test_detection_evaluation_json_carries_counts_intervals_and_honest_groups():
    """Verify detection_evaluation.json contains honest groups, reason fields, and slices_assigned."""
    det_path = REAL_RESULTS_DIR / "detection_evaluation.json"
    assert det_path.is_file(), f"Missing {det_path}"

    with open(det_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # 1. Slices assigned disclosure
    assert data.get("slices_assigned") is True, "Must explicitly disclose 'slices_assigned: true'"

    # 2. Honest groups partition
    assert "effective_attacks" in data
    assert "where_it_does_not_work" in data

    not_working = data["where_it_does_not_work"]
    # ICMPFlood has 0% recall, UDPFlood/HTTPFlood/SYNScan have < 5 windows
    assert "ICMPFlood" in not_working
    assert "UDPFlood" in not_working
    assert "HTTPFlood" in not_working
    assert "SYNScan" in not_working

    # Every item in 'where_it_does_not_work' must contain a non-empty reason
    for atk_name, item in not_working.items():
        assert "reason" in item and len(item["reason"]) > 10
        assert atk_name in DATA_FACT_REASONS

    # 3. Every detector metric in effective attacks must carry n and ci_text
    effective = data["effective_attacks"]
    for atk_name, item in effective.items():
        for det_name, det_data in item.get("detectors", {}).items():
            assert "recall_n" in det_data
            assert "recall_ci_text" in det_data
            assert "fpr_n" in det_data
            assert "fpr_ci_text" in det_data
            # If n < 10, ci_text must state interval too wide
            if det_data["recall_n"] < 10:
                assert "interval too wide to interpret" in det_data["recall_ci_text"]


def test_three_arm_summary_carries_counts_and_slices_assigned():
    """Verify three_arm_summary.json has slices_assigned and intervals."""
    summary_path = REAL_RESULTS_DIR / "three_arm_summary.json"
    assert summary_path.is_file(), f"Missing {summary_path}"

    with open(summary_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data.get("slices_assigned") is True

    for sc_name, sc_data in data.get("summaries", {}).items():
        assert sc_data.get("slices_assigned") is True
        for arm_name, arm in sc_data.get("arms", {}).items():
            assert "total_windows" in arm
            if arm.get("recall_mean") is not None:
                assert "recall_n" in arm
                assert "recall_ci_text" in arm
            if arm.get("fpr_mean") is not None:
                assert "fpr_n" in arm
                assert "fpr_ci_text" in arm
