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
    assert data["is_placeholder"] is True
    assert len(data["datasets"]) > 0
    first = data["datasets"][0]
    assert "dataset_id" in first
    assert "name" in first


@pytest.mark.anyio
async def test_replay_start(client: AsyncClient):
    payload = {
        "dataset_id": "5g_nidd_portscan_growth",
        "speed_multiplier": 2.0,
        "active_arms": ["arm_a_static", "arm_b_naive", "arm_c_commshield"],
        "window_scale_sec": 60,
    }
    response = await client.post("/api/v1/replay/start", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "RUNNING"
    assert data["dataset_id"] == "5g_nidd_portscan_growth"
    assert "current_window_index" in data
    assert "total_windows" in data
    assert "speed_multiplier" in data
    assert "current_timestamp" in data
    assert data["is_placeholder"] is True


@pytest.mark.anyio
async def test_replay_pause(client: AsyncClient):
    response = await client.post("/api/v1/replay/pause")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "PAUSED"
    assert "dataset_id" in data
    assert "current_window_index" in data
    assert "total_windows" in data
    assert "speed_multiplier" in data
    assert "current_timestamp" in data
    assert data["is_placeholder"] is True


@pytest.mark.anyio
async def test_replay_resume(client: AsyncClient):
    response = await client.post("/api/v1/replay/resume")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "RUNNING"
    assert "dataset_id" in data
    assert "current_window_index" in data
    assert "total_windows" in data
    assert "speed_multiplier" in data
    assert "current_timestamp" in data
    assert data["is_placeholder"] is True


@pytest.mark.anyio
async def test_replay_stop(client: AsyncClient):
    response = await client.post("/api/v1/replay/stop")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "STOPPED"
    assert "dataset_id" in data
    assert "current_window_index" in data
    assert "total_windows" in data
    assert "speed_multiplier" in data
    assert "current_timestamp" in data
    assert data["is_placeholder"] is True


@pytest.mark.anyio
async def test_replay_status(client: AsyncClient):
    response = await client.get("/api/v1/replay/status")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "dataset_id" in data
    assert "current_window_index" in data
    assert "total_windows" in data
    assert "speed_multiplier" in data
    assert "current_timestamp" in data
    assert data["is_placeholder"] is True


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
    response = await client.get("/api/v1/windows?slice_id=sst-1-sd-010203&limit=10&offset=0")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert "limit" in data
    assert "offset" in data
    assert data["is_placeholder"] is True
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
    window_id = "c1f7a4d2-3c22-498b-967f-9e79432f41bb"
    response = await client.get(f"/api/v1/windows/{window_id}/explain")
    assert response.status_code == 200
    data = response.json()
    assert data["window_id"] == window_id
    assert "slice_id" in data
    assert "nf_id" in data
    assert "is_anomalous" in data
    assert "fused_percentile" in data
    assert "shap_values" in data
    assert "hypothesis" in data
    assert "attribution_summary" in data
    assert "verdict" in data["attribution_summary"]
    assert data["is_placeholder"] is True


@pytest.mark.anyio
async def test_get_baselines(client: AsyncClient):
    response = await client.get("/api/v1/baselines?slice_id=sst-1-sd-010203")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    b = data[0]
    assert "id" in b
    assert "slice_id" in b
    assert "nf_id" in b
    assert "version" in b
    assert "is_anchor" in b
    assert "is_active" in b
    assert "model_artifact_path" in b
    assert "scaler_params" in b
    assert "threshold_params" in b
    assert "feature_schema" in b
    assert b["is_placeholder"] is True


@pytest.mark.anyio
async def test_get_candidates(client: AsyncClient):
    response = await client.get("/api/v1/candidates?status=PENDING")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    c = data[0]
    assert "id" in c
    assert "slice_id" in c
    assert "candidate_version" in c
    assert "active_baseline_id" in c
    assert "anchor_baseline_id" in c
    assert "status" in c
    assert "gate_metrics" in c
    assert "decision_trace" in c
    assert c["is_placeholder"] is True


@pytest.mark.anyio
async def test_approve_candidate(client: AsyncClient):
    candidate_id = "cand-9f88b0a1-7b55-46f9-bf51-11c750e3d220"
    payload = {
        "analyst_id": "analyst_sec_09",
        "notes": "Verified organic marketing campaign traffic surge matches change-event log.",
    }
    response = await client.post(f"/api/v1/candidates/{candidate_id}/approve", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == candidate_id
    assert data["status"] == "APPROVED"
    assert data["reviewed_by"] == "analyst_sec_09"
    assert "gate_metrics" in data
    assert "decision_trace" in data
    assert data["is_placeholder"] is True


@pytest.mark.anyio
async def test_reject_candidate(client: AsyncClient):
    candidate_id = "cand-9f88b0a1-7b55-46f9-bf51-11c750e3d220"
    payload = {
        "analyst_id": "analyst_sec_09",
        "notes": "Candidate exhibits canary degradation.",
    }
    response = await client.post(f"/api/v1/candidates/{candidate_id}/reject", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == candidate_id
    assert data["status"] == "REJECTED"
    assert data["reviewed_by"] == "analyst_sec_09"
    assert "gate_metrics" in data
    assert "decision_trace" in data
    assert data["is_placeholder"] is True


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
    assert data["is_placeholder"] is True


@pytest.mark.anyio
async def test_three_arm_comparison(client: AsyncClient):
    response = await client.get("/api/v1/experiments/three-arm?dataset_id=5g_nidd_portscan_growth")
    assert response.status_code == 200
    data = response.json()
    assert data["dataset_id"] == "5g_nidd_portscan_growth"
    assert "arms" in data
    assert "arm_a_static" in data["arms"]
    assert "arm_b_naive" in data["arms"]
    assert "arm_c_commshield" in data["arms"]
    assert data["is_placeholder"] is True


@pytest.mark.anyio
async def test_database_integration_when_rows_exist(client: AsyncClient):
    db = SessionLocal()
    try:
        test_slice = f"slice-{uuid.uuid4().hex[:8]}"
        base = Baseline(
            id=f"base-{uuid.uuid4().hex[:8]}",
            slice_id=test_slice,
            nf_id="UPF-01",
            version="v2.0.0",
            is_anchor=True,
            is_active=True,
            training_window_start=datetime.now(timezone.utc),
            training_window_end=datetime.now(timezone.utc),
            model_artifact_path="/tmp/model.joblib",
            scaler_params={"scale": 1.0},
            threshold_params={"thresh": 0.99},
            feature_schema={"f": ["a"]},
        )
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
        db.add_all([base, win])
        db.commit()

        cand = CandidateBaseline(
            id=f"cand-{uuid.uuid4().hex[:8]}",
            slice_id=test_slice,
            candidate_version="v2.1.0-cand",
            active_baseline_id=base.id,
            anchor_baseline_id=base.id,
            status="PENDING",
            gate_metrics={"d_rms": 0.2},
            decision_trace=["Trace check"],
        )
        db.add(cand)
        db.commit()

        r_win = await client.get(f"/api/v1/windows?slice_id={test_slice}")
        assert r_win.status_code == 200
        data_win = r_win.json()
        assert data_win["total"] >= 1
        assert data_win["is_placeholder"] is False

        r_base = await client.get(f"/api/v1/baselines?slice_id={test_slice}")
        assert r_base.status_code == 200
        data_base = r_base.json()
        assert len(data_base) >= 1
        assert data_base[0]["is_placeholder"] is False

        r_cand = await client.get("/api/v1/candidates?status=PENDING")
        assert r_cand.status_code == 200
        data_cand = r_cand.json()
        assert any(c["id"] == cand.id and c["is_placeholder"] is False for c in data_cand)

        r_appr = await client.post(
            f"/api/v1/candidates/{cand.id}/approve",
            json={"analyst_id": "analyst_1", "notes": "Approved for testing"},
        )
        assert r_appr.status_code == 200
        assert r_appr.json()["status"] == "APPROVED"
        assert r_appr.json()["is_placeholder"] is False

        r_roll = await client.post(
            "/api/v1/baselines/rollback",
            json={
                "slice_id": test_slice,
                "nf_id": "UPF-01",
                "target_baseline_version": "v2.0.0",
                "reason": "Test rollback",
                "analyst_id": "analyst_1",
            },
        )
        assert r_roll.status_code == 200
        assert r_roll.json()["status"] == "COMPLETED"
        assert r_roll.json()["is_placeholder"] is False
    finally:
        db.close()
