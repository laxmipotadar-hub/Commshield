"""Acceptance Tests for CommShield Intelligent Cyber Defence Operations Centre."""

import pytest
from starlette.testclient import TestClient

from app.main import app
from app.twin.state_engine import twin_state_engine

client = TestClient(app)


def test_healthy_network_initialization():
    """TEST 1: Start network and verify healthy operation."""
    resp = client.get("/api/twin/state")
    assert resp.status_code == 200
    data = resp.json()
    assert data["overall_health_score"] >= 95.0
    assert data["total_components_count"] >= 28
    assert data["traffic_breakdown"]["normal_traffic_mbps"] == 75.0


def test_speed_and_defence_mode_toggles():
    """TEST 6: Switch between automatic and manual modes, and change speed."""
    # Speed
    resp = client.post("/api/twin/speed", json={"speed": 2.0})
    assert resp.status_code == 200
    assert resp.json()["speed"] == 2.0

    # Mode
    resp = client.post("/api/twin/defence/mode", json={"mode": "MANUAL"})
    assert resp.status_code == 200
    assert resp.json()["mode"] == "MANUAL"


def test_attack_lifecycle_and_recommendation_flow():
    """TEST 2, 3, 4, 5: Launch DDoS, verify telemetry, detection, and recommendation."""
    # Start attack with alias
    resp = client.post("/api/twin/scenarios/start", json={
        "scenario_type": "Volumetric DDoS",
        "target_component": "upf-01",
        "intensity": 3.0,
        "auto_progress": False,
    })
    assert resp.status_code == 200
    assert resp.json()["status"] == "STARTED"

    # Step progression to THREAT_DETECTED
    client.post("/api/twin/scenarios/step")  # SUSPICIOUS_ACTIVITY
    client.post("/api/twin/scenarios/step")  # ANALYSING
    step_resp = client.post("/api/twin/scenarios/step")  # THREAT_DETECTED
    assert step_resp.status_code == 200

    # Verify traffic breakdown
    tb_resp = client.get("/api/twin/traffic/breakdown")
    assert tb_resp.status_code == 200
    tb = tb_resp.json()
    assert tb["malicious_traffic_mbps"] > 100.0

    # Verify recommendation generated
    rec_resp = client.get("/api/twin/defence/recommendations")
    assert rec_resp.status_code == 200
    recs = rec_resp.json()["recommendations"]
    assert len(recs) >= 1
    assert recs[-1]["proposed_action"] == "RATE_LIMITING"

    # Operator approves recommendation (TEST 5 & 7)
    app_resp = client.post("/api/twin/defence/approve", json={"recommendation_id": recs[-1]["recommendation_id"]})
    assert app_resp.status_code == 200
    assert app_resp.json()["status"] == "APPROVED_AND_EXECUTED"

    # Verify legitimate traffic continued (TEST 9)
    tb_after = client.get("/api/twin/traffic/breakdown").json()
    assert tb_after["legitimate_preserved_pct"] >= 95.0
    assert tb_after["malicious_blocked_mbps"] > 0.0

    # Containment Verification (TEST 11)
    ver_resp = client.post("/api/twin/defence/verify", json={})
    assert ver_resp.status_code == 200
    ver = ver_resp.json()
    assert ver["verdict"] in ("CONTAINMENT_VERIFIED", "PARTIAL_MITIGATION")

    # Network Recovery (TEST 12)
    rec_resp = client.post("/api/twin/defence/recover")
    assert rec_resp.status_code == 200
    assert rec_resp.json()["status"] == "RECOVERED"

    # Verify historical incident records (TEST 13)
    inc_resp = client.get("/api/twin/incidents")
    assert inc_resp.status_code == 200
    incidents = inc_resp.json()["incidents"]
    assert len(incidents) >= 1
    inc_id = incidents[-1]["incident_id"]

    # Incident Report Export (Markdown)
    rep_resp = client.get(f"/api/twin/incidents/{inc_id}/report?format=markdown")
    assert rep_resp.status_code == 200
    assert "COMMSHIELD CYBER DEFENCE INCIDENT REPORT" in rep_resp.json()["report"]


def test_reset_network_preserves_incidents():
    """Verify reset to healthy state clears temporary policies but preserves incidents."""
    inc_before = len(twin_state_engine.get_incidents())
    client.post("/api/twin/scenarios/reset")
    snap = client.get("/api/twin/state").json()
    assert snap["overall_health_score"] >= 95.0
    assert snap["lifecycle_state"] == "NORMAL"
    assert len(twin_state_engine.get_incidents()) == inc_before


def test_distributed_ddos_propagation():
    """Verify distributed DDoS initiates multiple distinct attacker sources and paths."""
    client.post("/api/twin/scenarios/reset")
    resp = client.post("/api/twin/scenarios/start", json={
        "scenario_type": "Distributed DDoS",
        "target_component": "upf-01",
        "intensity": 4.0,
        "is_distributed": True,
        "auto_progress": False,
    })
    assert resp.status_code == 200
    prop = resp.json()["propagation"]
    assert prop["is_distributed"] is True
    assert len(prop["attacker_sources"]) >= 3
    assert len(prop["attack_paths"]) >= 3
    # Check that multiple paths converge on target
    for path in prop["attack_paths"]:
        assert path[-1] == "upf-01"


def test_complete_network_recovery_removes_attack_state():
    """Verify recovery completely clears attack states, removes red paths, and archives incident."""
    # Start and advance attack
    client.post("/api/twin/scenarios/start", json={
        "scenario_type": "Volumetric DDoS",
        "target_component": "upf-01",
        "intensity": 3.0,
        "auto_progress": False,
    })
    client.post("/api/twin/scenarios/step")
    client.post("/api/twin/scenarios/step")
    client.post("/api/twin/scenarios/step")

    # Apply mitigation
    rec_resp = client.get("/api/twin/defence/recommendations").json()
    rec_id = rec_resp["recommendations"][-1]["recommendation_id"]
    client.post("/api/twin/defence/approve", json={"recommendation_id": rec_id})

    # Initiate recovery
    recov_resp = client.post("/api/twin/defence/recover")
    assert recov_resp.status_code == 200
    assert recov_resp.json()["status"] == "RECOVERED"

    # Inspect authoritative state
    snap = client.get("/api/twin/state").json()
    assert snap["lifecycle_state"] == "RECOVERED"
    assert snap["current_propagation"] is None
    assert len(snap["active_threats"]) == 0
    assert snap["overall_health_score"] >= 95.0
    assert snap["traffic_breakdown"]["malicious_traffic_mbps"] == 0.0
    assert snap["traffic_breakdown"]["legitimate_preserved_pct"] == 100.0


def test_data_modes_and_integrity_panel():
    """Verify data modes, synthetic toggle, slice switcher, and data integrity report."""
    # Data mode toggle
    mode_resp = client.post("/api/twin/data/mode", json={"mode": "REAL_DATASET"})
    assert mode_resp.status_code == 200
    assert mode_resp.json()["data_mode"] == "REAL_DATASET"

    # Synthetic toggle
    syn_resp = client.post("/api/twin/data/synthetic", json={"enabled": False})
    assert syn_resp.status_code == 200
    assert syn_resp.json()["synthetic_enabled"] is False

    # Slice switcher
    slice_resp = client.post("/api/twin/slice/active", json={"slice_id": "sst-2-sd-020304"})
    assert slice_resp.status_code == 200
    assert slice_resp.json()["active_slice_id"] == "sst-2-sd-020304"

    # Ensemble fusion toggle
    fusion_resp = client.post("/api/twin/detection/fusion", json={"enabled": False})
    assert fusion_resp.status_code == 200
    assert fusion_resp.json()["ensemble_fusion_enabled"] is False

    # Data integrity endpoint
    diag_resp = client.get("/api/twin/data/integrity")
    assert diag_resp.status_code == 200
    diag = diag_resp.json()
    assert diag["status"] in ("VALID", "DEGRADED")
    assert diag["rules_evaluated"] >= 12
