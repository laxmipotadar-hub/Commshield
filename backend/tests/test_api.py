import sys
from datetime import datetime, timezone
from pathlib import Path
import uuid
import pytest
from httpx import ASGITransport, AsyncClient

backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.main import app
from app.database import SessionLocal
from app.models import Baseline, CanonicalWindow, CandidateBaseline


@pytest.fixture
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac


@pytest.mark.anyio
async def test_get_datasets(client: AsyncClient):
    response = await client.get("/api/v1/datasets")
    assert response.status_code == 200
    data = response.json()
    assert "datasets" in data
    assert "total" in data
    assert len(data["datasets"]) > 0
    first = data["datasets"][0]
    assert "dataset_id" in first
    assert "name" in first


@pytest.mark.anyio
async def test_replay_lifecycle(client: AsyncClient):
    # Ensure replay is stopped before test
    await client.post("/api/v1/replay/stop")

    # Start replay
    payload = {
        "dataset_id": "legitimate_growth",
        "speed_multiplier": 5.0,
        "active_arms": ["arm_a_static", "arm_b_naive", "arm_c_commshield"],
        "window_scale_sec": 60,
    }
    response = await client.post("/api/v1/replay/start", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "RUNNING"
    assert data["dataset_id"] == "legitimate_growth"
    assert "current_window_index" in data
    assert "total_windows" in data

    # Attempting to start again should fail with 409
    res_duplicate = await client.post("/api/v1/replay/start", json=payload)
    assert res_duplicate.status_code == 409
    assert "detail" in res_duplicate.json()

    # Pause replay
    res_pause = await client.post("/api/v1/replay/pause")
    assert res_pause.status_code == 200
    assert res_pause.json()["status"] == "PAUSED"

    # Resume replay
    res_resume = await client.post("/api/v1/replay/resume")
    assert res_resume.status_code == 200
    assert res_resume.json()["status"] == "RUNNING"

    # Status check
    res_status = await client.get("/api/v1/replay/status")
    assert res_status.status_code == 200
    assert res_status.json()["status"] in ["RUNNING", "COMPLETED"]

    # Stop replay
    res_stop = await client.post("/api/v1/replay/stop")
    assert res_stop.status_code == 200
    assert res_stop.json()["status"] == "STOPPED"


@pytest.mark.anyio
async def test_replay_stream(client: AsyncClient):
    response = await client.get("/api/v1/replay/stream?speed=1")
    assert response.status_code == 200
    assert "text/event-stream" in response.headers.get("content-type", "")
    content = response.text
    assert "data:" in content
    assert "window" in content
    assert "event_type" in content


@pytest.mark.anyio
async def test_get_windows(client: AsyncClient):
    # Insert a window first to guarantee at least one exists
    db = SessionLocal()
    test_slice = "sst-1-sd-010203"
    try:
        win = CanonicalWindow(
            id=f"win-{uuid.uuid4().hex[:8]}",
            slice_id=test_slice,
            nf_id="UPF-01",
            window_start=datetime.now(timezone.utc),
            window_end=datetime.now(timezone.utc),
            duration_sec=60,
            raw_counters={"pkts": 100},
            ratio_features={"rate": 1.5},
            composition_vector={"p": 1.0},
        )
        db.add(win)
        db.commit()
    finally:
        db.close()

    response = await client.get(f"/api/v1/windows?slice_id={test_slice}&limit=10&offset=0")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert "limit" in data
    assert "offset" in data
    assert len(data["items"]) > 0
    item = data["items"][0]
    assert "window_id" in item
    assert "slice_id" in item
    assert "nf_id" in item
    assert "raw_counters" in item
    assert "ratio_features" in item
    assert "composition_vector" in item


@pytest.mark.anyio
async def test_get_window_explain(client: AsyncClient):
    # Insert a canonical window and test explain
    db = SessionLocal()
    window_id = f"win-exp-{uuid.uuid4().hex[:8]}"
    test_slice = "sst-1-sd-010203"
    try:
        win = CanonicalWindow(
            id=window_id,
            slice_id=test_slice,
            nf_id="UPF-01",
            window_start=datetime.now(timezone.utc),
            window_end=datetime.now(timezone.utc),
            duration_sec=60,
            raw_counters={"pdu_sessions_active": 500, "bytes_dl": 100000},
            ratio_features={"dl_ul_ratio": 2.5},
            composition_vector={"pdu_share": 1.0},
        )
        db.add(win)
        db.commit()
    finally:
        db.close()

    response = await client.get(f"/api/v1/windows/{window_id}/explain")
    assert response.status_code == 200
    data = response.json()
    assert data["window_id"] == window_id
    assert data["slice_id"] == test_slice
    assert "is_anomalous" in data
    assert "fused_percentile" in data
    assert "shap_values" in data
    assert "hypothesis" in data
    assert "attribution_summary" in data


@pytest.mark.anyio
async def test_get_baselines(client: AsyncClient):
    response = await client.get("/api/v1/baselines?slice_id=sst-1-sd-010203")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    if len(data) > 0:
        b = data[0]
        assert "id" in b
        assert "slice_id" in b
        assert "nf_id" in b
        assert "version" in b
        assert "is_anchor" in b
        assert "is_active" in b


@pytest.mark.anyio
async def test_candidate_approval_and_rejection(client: AsyncClient):
    db = SessionLocal()
    test_slice = f"slice-{uuid.uuid4().hex[:8]}"
    cand_id = f"cand-{uuid.uuid4().hex[:8]}"
    base_id = f"base-{uuid.uuid4().hex[:8]}"
    try:
        base = Baseline(
            id=base_id,
            slice_id=test_slice,
            nf_id="UPF-01",
            version="v1.0.0-anchor",
            is_anchor=True,
            is_active=True,
            training_window_start=datetime.now(timezone.utc),
            training_window_end=datetime.now(timezone.utc),
            model_artifact_path="/tmp/model.joblib",
            scaler_params={"scale": 1.0},
            threshold_params={"thresh": 0.99},
            feature_schema={"f": ["a"]},
        )
        cand = CandidateBaseline(
            id=cand_id,
            slice_id=test_slice,
            candidate_version="v1.1.0-cand",
            active_baseline_id=base.id,
            anchor_baseline_id=base.id,
            status="PENDING",
            gate_metrics={"d_rms": 0.1},
            decision_trace=["Evaluated gates"],
        )
        db.add_all([base, cand])
        db.commit()
    finally:
        db.close()

    # Get candidates
    res_list = await client.get("/api/v1/candidates?status=PENDING")
    assert res_list.status_code == 200
    assert any(c["id"] == cand_id for c in res_list.json())

    # Approve candidate
    payload_appr = {
        "analyst_id": "analyst_sec_09",
        "notes": "Verified organic traffic surge matches change-event log.",
    }
    res_appr = await client.post(f"/api/v1/candidates/{cand_id}/approve", json=payload_appr)
    assert res_appr.status_code == 200
    data_appr = res_appr.json()
    assert data_appr["id"] == cand_id
    assert data_appr["status"] == "APPROVED"
    assert data_appr["reviewed_by"] == "analyst_sec_09"

    # Reject another candidate
    cand_rej_id = f"cand-rej-{uuid.uuid4().hex[:8]}"
    db = SessionLocal()
    try:
        cand_rej = CandidateBaseline(
            id=cand_rej_id,
            slice_id=test_slice,
            candidate_version="v1.1.1-cand",
            active_baseline_id=base_id,
            anchor_baseline_id=base_id,
            status="PENDING",
            gate_metrics={"d_rms": 0.9},
            decision_trace=["Gate failure"],
        )
        db.add(cand_rej)
        db.commit()
    finally:
        db.close()

    payload_rej = {
        "analyst_id": "analyst_sec_09",
        "notes": "Candidate exhibits canary degradation.",
    }
    res_rej = await client.post(f"/api/v1/candidates/{cand_rej_id}/reject", json=payload_rej)
    assert res_rej.status_code == 200
    data_rej = res_rej.json()
    assert data_rej["id"] == cand_rej_id
    assert data_rej["status"] == "REJECTED"


@pytest.mark.anyio
async def test_rollback_baseline(client: AsyncClient):
    payload = {
        "slice_id": "sst-1-sd-010203",
        "nf_id": "UPF-01",
        "target_baseline_version": "v1.0.0-anchor",
        "reason": "Detection degradation observed post candidate canary evaluation",
        "analyst_id": "analyst_sec_09",
    }
    response = await client.post("/api/v1/baselines/rollback", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "COMPLETED"
    assert data["slice_id"] == "sst-1-sd-010203"
    assert data["active_version"] == "v1.0.0-anchor"
    assert "restored_artifacts" in data
    assert "timestamp" in data


@pytest.mark.anyio
async def test_three_arm_comparison(client: AsyncClient):
    response = await client.get("/api/v1/experiments/three-arm?dataset_id=legitimate_growth")
    assert response.status_code == 200
    data = response.json()
    assert data["dataset_id"] == "legitimate_growth"
    assert "arms" in data
    assert "arm_a_static" in data["arms"]
    assert "arm_b_naive" in data["arms"]
    assert "arm_c_commshield" in data["arms"]


@pytest.mark.anyio
async def test_get_experiment_results_data_source_filter(client: AsyncClient):
    # 1. Synthetic data source
    res_synth = await client.get("/api/experiments/results?data_source=synthetic")
    assert res_synth.status_code == 200
    data_synth = res_synth.json()
    assert data_synth["data_source"] == "synthetic"
    assert "summaries" in data_synth or "results" in data_synth

    # 2. Real 5G-NIDD data source
    res_real = await client.get("/api/experiments/results?data_source=5g_nidd")
    assert res_real.status_code == 200
    data_real = res_real.json()
    assert data_real["data_source"] == "5g_nidd"
    assert "summaries" in data_real
    assert "real_benign" in data_real["summaries"]
    assert "real_attacks" in data_real["summaries"]
    assert "detection_evaluation" in data_real

    # 3. Open5GS lab data source (not yet ingested -> 404)
    res_open5gs = await client.get("/api/experiments/results?data_source=open5gs_lab")
    assert res_open5gs.status_code == 404

    # 4. Scenario filter with data source
    res_sc_real = await client.get("/api/experiments/results/real_attacks?data_source=5g_nidd")
    assert res_sc_real.status_code == 200
    assert res_sc_real.json()["scenario"] == "real_attacks"


def test_offline_snapshot_integrity():
    snapshot_dir = Path(__file__).resolve().parent.parent.parent / "experiments" / "snapshot"
    assert (snapshot_dir / "experiment_summary.json").is_file()
    assert (snapshot_dir / "real" / "three_arm_summary.json").is_file()
    assert (snapshot_dir / "real" / "detection_evaluation.json").is_file()
    assert (snapshot_dir / "README.md").is_file()

