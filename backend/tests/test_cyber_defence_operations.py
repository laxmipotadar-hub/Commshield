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
