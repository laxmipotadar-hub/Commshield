import asyncio
from datetime import datetime, timezone
from pathlib import Path
import sys
import pytest
from httpx import ASGITransport, AsyncClient

# Ensure commshield root is on sys.path
root_dir = Path(__file__).resolve().parent.parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))
backend_dir = root_dir / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from ml_engine.preprocessing.synthetic_generator import SyntheticGenerator
from ml_engine.preprocessing.windowing import RobustScaler, slice_into_windows
from ml_engine.preprocessing.adapters import FiveGNIDDAdapter, SyntheticAdapter
from backend.app.main import app
from backend.app.database import SessionLocal
from backend.app.models import CanonicalWindow
from backend.app.services.replay import replay_service


@pytest.fixture
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac


def test_generator_determinism():
    """Verify that the same seed gives exactly the same data and different seeds differ."""
    gen1 = SyntheticGenerator(seed=1337)
    gen2 = SyntheticGenerator(seed=1337)
    gen_diff = SyntheticGenerator(seed=9999)

    windows1 = gen1.generate_scenario_windows("slow_attack_ramp", num_windows=15, window_duration_sec=60)
    windows2 = gen2.generate_scenario_windows("slow_attack_ramp", num_windows=15, window_duration_sec=60)
    windows_diff = gen_diff.generate_scenario_windows("slow_attack_ramp", num_windows=15, window_duration_sec=60)

    assert len(windows1) == 15
    assert len(windows2) == 15

    for w1, w2 in zip(windows1, windows2):
        assert w1["raw_counters"] == w2["raw_counters"]
        assert w1["ratio_features"] == w2["ratio_features"]
        assert w1["composition_vector"] == w2["composition_vector"]
        assert w1["ground_truth"] == w2["ground_truth"]

    # Verify that different seed produces distinct values
    diff_count = sum(
        1 for w1, wd in zip(windows1, windows_diff)
        if w1["raw_counters"]["total_bytes_uplink"] != wd["raw_counters"]["total_bytes_uplink"]
    )
    assert diff_count > 0


def test_ground_truth_labels_exist_for_every_attack_window():
    """Verify ground-truth labels exist and are accurately assigned for every attack window."""
    gen = SyntheticGenerator(seed=42)

    scenarios = ["slow_attack_ramp", "attack_in_growth", "mimicry_attack"]

    for sc in scenarios:
        windows = gen.generate_scenario_windows(sc, num_windows=30, window_duration_sec=60)
        attack_windows = [w for w in windows if w["ground_truth"]["is_attack"]]

        assert len(attack_windows) > 0, f"Scenario {sc} must contain attack windows."

        for w in attack_windows:
            gt = w["ground_truth"]
            assert gt["is_attack"] is True
            assert gt["attack_type"] == sc, f"Window attack_type must match {sc}"

        benign_windows = [w for w in windows if not w["ground_truth"]["is_attack"]]
        for w in benign_windows:
            gt = w["ground_truth"]
            assert gt["is_attack"] is False
            assert gt["attack_type"] is None


def test_no_scaler_leakage():
    """Verify that the scaler is fit only on training data and retains parameters during transforms."""
    gen = SyntheticGenerator(seed=101)

    train_windows = gen.generate_scenario_windows("clean_training", num_windows=40, window_duration_sec=60)
    attack_windows = gen.generate_scenario_windows("slow_attack_ramp", num_windows=40, window_duration_sec=60)

    scaler = RobustScaler()
    with pytest.raises(RuntimeError):
        scaler.transform(train_windows)  # Must fail before fit

    # Fit strictly on clean training period
    scaler.fit(train_windows)
    assert scaler.fitted is True

    medians_baseline = dict(scaler.medians)
    iqrs_baseline = dict(scaler.iqrs)

    # Transform attack windows
    transformed_attack = scaler.transform(attack_windows)
    assert len(transformed_attack) == 40
    assert "scaled_features" in transformed_attack[0]

    # Invariant: Scaler parameters must not be modified by transforming test/attack windows
    assert scaler.medians == medians_baseline
    assert scaler.iqrs == iqrs_baseline

    # Test serialization to dict and loading
    scaler_dict = scaler.to_dict()
    assert "medians" in scaler_dict
    assert "iqrs" in scaler_dict

    reloaded = RobustScaler.from_dict(scaler_dict)
    assert reloaded.fitted is True
    assert reloaded.medians == medians_baseline
    assert reloaded.iqrs == iqrs_baseline


def test_adapters_protocol():
    """Verify adapter interface and FiveGNIDDAdapter execution."""
    adapter_nidd = FiveGNIDDAdapter()
    assert list(adapter_nidd.parse_records([])) == []
    empty_win = adapter_nidd.aggregate_window([], "sst-1-sd-010203", "UPF-01", 60, datetime.now(timezone.utc), datetime.now(timezone.utc))
    assert empty_win["slice_id"] == "sst-1-sd-010203"
    assert "raw_counters" in empty_win

    # Verify SyntheticAdapter
    adapter = SyntheticAdapter()
    gen = SyntheticGenerator(seed=7)
    sec_event = gen.generate_raw_second("eMBB", datetime.now(timezone.utc))
    parsed = list(adapter.parse_records([sec_event]))
    assert len(parsed) == 1


@pytest.mark.anyio
async def test_replay_stores_expected_number_of_windows(client: AsyncClient):
    """Verify replay service steps through scenario windows, stores them in DB, and GET returns them."""
    db = SessionLocal()
    initial_db_count = db.query(CanonicalWindow).count()
    db.close()

    # Start replay of stable_benign scenario
    start_payload = {
        "dataset_id": "stable_benign",
        "speed_multiplier": 50.0,
        "active_arms": ["arm_c_commshield"],
        "window_scale_sec": 60,
    }

    # Test POST /api/replay/start
    res_start = await client.post("/api/replay/start", json=start_payload)
    assert res_start.status_code == 200
    status_data = res_start.json()
    assert status_data["status"] == "RUNNING"
    assert status_data["dataset_id"] == "stable_benign"
    assert status_data["total_windows"] > 0

    # Test POST /api/replay/pause and resume
    res_pause = await client.post("/api/replay/pause")
    assert res_pause.status_code == 200
    assert res_pause.json()["status"] == "PAUSED"

    res_resume = await client.post("/api/replay/resume")
    assert res_resume.status_code == 200
    assert res_resume.json()["status"] == "RUNNING"

    # Step synchronously to guarantee windows are persisted in test
    stored_step_count = replay_service.step_sync(5)
    assert stored_step_count == 5

    # Check database persistence
    db = SessionLocal()
    new_db_count = db.query(CanonicalWindow).count()
    db.close()
    assert new_db_count >= initial_db_count + 5

    # Test GET /api/traffic/windows (reads real data from database)
    res_windows = await client.get("/api/traffic/windows?limit=10")
    assert res_windows.status_code == 200
    data_windows = res_windows.json()
    assert data_windows["total"] >= 5
    assert len(data_windows["items"]) >= 5

    # Test GET /api/replay/status
    res_status = await client.get("/api/replay/status")
    assert res_status.status_code == 200
    assert res_status.json()["current_window_index"] >= 5

    # Stop replay
    res_stop = await client.post("/api/replay/stop")
    assert res_stop.status_code == 200
    assert res_stop.json()["status"] == "STOPPED"
# CommShield AI Core
