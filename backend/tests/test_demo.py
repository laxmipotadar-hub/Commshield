import json
from pathlib import Path
import pytest
from httpx import AsyncClient, ASGITransport

from backend.app.main import app
from backend.app.services.replay import replay_service

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


@pytest.mark.anyio
async def test_demo_scenarios_endpoint():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        # Test unversioned /api/demo/scenarios
        res = await client.get("/api/demo/scenarios")
        assert res.status_code == 200
        data = res.json()
        assert "scenarios" in data
        scenarios = data["scenarios"]
        assert len(scenarios) == 4

        # Test versioned /api/v1/demo/scenarios
        res_v1 = await client.get("/api/v1/demo/scenarios")
        assert res_v1.status_code == 200
        assert len(res_v1.json()["scenarios"]) == 4

        # Scenario 1: real benign
        s1 = scenarios[0]
        assert s1["id"] == "real_benign"
        assert s1["data_label"] == "real"
        assert s1["window_range"]["total_windows"] == 40
        assert s1["window_range"]["start_index"] == 0
        assert s1["window_range"]["end_index"] == 39
        assert len(s1["key_events"]) >= 2

        # Scenario 2: real attack
        s2 = scenarios[1]
        assert s2["id"] == "real_attack"
        assert s2["data_label"] == "real"
        assert s2["best_attack_type"] == "SYNScan"
        assert s2["window_range"]["total_windows"] == 21
        assert s2["window_range"]["end_index"] == 20
        assert any(e["event_type"] == "first_alert" for e in s2["key_events"])

        # Scenario 3: scaled benign growth
        s3 = scenarios[2]
        assert s3["id"] == "scaled_growth"
        assert s3["data_label"] == "semi-synthetic"
        assert s3["window_range"]["total_windows"] == 40
        assert any(e["event_type"] == "candidate_built" for e in s3["key_events"])

        # Scenario 4: attack injected into growth
        s4 = scenarios[3]
        assert s4["id"] == "attack_in_growth"
        assert s4["data_label"] == "semi-synthetic"
        assert s4["window_range"]["total_windows"] == 21
        assert s4["three_arm_summary"] is not None
        assert "arm_c_commshield" in s4["three_arm_summary"]["arms"]
        assert s4["decision_trace"] is not None
        assert s4["decision_trace"]["overall_status"] == "REJECTED"


def test_demo_scenario_files_exist_and_non_empty():
    synth_dir = PROJECT_ROOT / "data" / "synthetic"
    expected_files = [
        "demo_real_benign.json",
        "demo_real_attack.json",
        "demo_scaled_growth.json",
        "demo_attack_in_growth.json",
    ]
    for fn in expected_files:
        fp = synth_dir / fn
        assert fp.is_file(), f"Demo scenario file {fn} missing"
        with open(fp, "r", encoding="utf-8") as f:
            data = json.load(f)
            assert "windows" in data
            assert len(data["windows"]) > 0, f"Demo file {fn} has no windows"


def test_demo_replay_determinism():
    # Start sync replay for scenario 1 twice and assert strict identity
    res1 = replay_service.start_sync("demo_real_benign")
    assert res1.status == "RUNNING"
    assert res1.total_windows == 40
    windows_run1 = [w["window_id"] for w in replay_service._windows]

    res2 = replay_service.start_sync("demo_real_benign")
    assert res2.total_windows == 40
    windows_run2 = [w["window_id"] for w in replay_service._windows]

    assert windows_run1 == windows_run2

    # Start sync replay for attack in growth
    res_atk = replay_service.start_sync("demo_attack_in_growth")
    assert res_atk.total_windows == 21
    assert replay_service._windows[20]["ground_truth"]["is_attack"] is True
