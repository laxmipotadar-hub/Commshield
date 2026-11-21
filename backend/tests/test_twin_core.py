"""Comprehensive unit and integration tests for CommShield AI Digital Twin Core.

Validates:
1. 3GPP Canonical Topology & State Initialization
2. Graph-based Attack Propagation & Blast Radius Calculation
3. Scenario Engine Lifecycle & State Machine (6 Scenarios)
4. Multi-Tier Mitigation & Verifiable Recovery
5. Decoupled What-If Experimentation Sandbox
6. Quantitative Resilience Formula & Grading
7. REST API Endpoints (/api/twin/*) & WebSocket Streaming
"""

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.twin.models import (
    DataClassification,
    MitigationActionType,
    MitigationStatus,
    OperationalStatus,
    ScenarioLifecycleState,
    ScenarioType,
    SecurityStatus,
)
from backend.app.twin.mitigation import mitigation_engine
from backend.app.twin.propagation import AttackPropagationEngine
from backend.app.twin.resilience import resilience_engine
from backend.app.twin.scenarios import SCENARIO_CATALOG, scenario_engine
from backend.app.twin.state_engine import twin_state_engine
from backend.app.twin.whatif import whatif_engine


client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_twin_state():
    """Ensure clean nominal baseline before and after each test."""
    scenario_engine.stop_scenario()
    twin_state_engine.reset_to_nominal()
    yield
    scenario_engine.stop_scenario()
    twin_state_engine.reset_to_nominal()


def test_canonical_topology_initialization():
    """Verify 3GPP private 5G components, connections, and slices are initialized."""
    snapshot = twin_state_engine.get_snapshot()

    # Check components
    assert len(snapshot.components) >= 25  # RAN, 13 UEs, 10 Core, Infra
    assert "gnb-01" in snapshot.components
    assert "upf-01" in snapshot.components
    assert "amf-01" in snapshot.components
    assert "ue-camera-01" in snapshot.components
    assert "ue-agv-01" in snapshot.components
    assert "ue-sensor-01" in snapshot.components

    # Check slices
    assert len(snapshot.slices) == 3
    assert "sst-1-sd-010203" in snapshot.slices  # eMBB
    assert "sst-2-sd-020304" in snapshot.slices  # URLLC
    assert "sst-3-sd-030405" in snapshot.slices  # mMTC

    # Check baseline health and resilience
    assert snapshot.overall_health_score == 100.0
    assert snapshot.lifecycle_state == ScenarioLifecycleState.NORMAL
    assert snapshot.resilience.resilience_score == 100.0
    assert snapshot.resilience.assessment_grade == "EXCELLENT"


def test_atomic_state_updates():
    """Verify thread-safe component and connection updates."""
    initial_version = twin_state_engine.get_state_version()

    # Update UPF component
    updated_upf = twin_state_engine.update_component(
        "upf-01",
        cpu_utilization_pct=45.0,
        latency_ms=3.5,
    )
    assert updated_upf.cpu_utilization_pct == 45.0
    assert updated_upf.latency_ms == 3.5
    assert twin_state_engine.get_state_version() > initial_version

    # Update connection
    updated_conn = twin_state_engine.update_connection(
        "conn-n3-gnb-upf",
        utilization_mbps=5000.0,
    )
    assert updated_conn.utilization_mbps == 5000.0
    assert updated_conn.utilization_pct == 50.0  # 5000 / 10000 Mbps capacity


def test_attack_propagation_and_blast_radius():
    """Verify graph BFS traversal, causal classification, and blast radius calculation."""
    prop_engine = AttackPropagationEngine()
    components = twin_state_engine.get_components()
    connections = twin_state_engine.get_connections()

    result = prop_engine.compute_propagation(
        scenario_id="test-ddos",
        entry_point="ue-camera-01",
        target_component="upf-01",
        components=components,
        connections=connections,
        traffic_intensity_multiplier=3.0,
    )

    assert "upf-01" in result.directly_targeted
    assert "ue-camera-01" in result.directly_targeted
    assert len(result.attack_path) >= 2
    assert result.blast_radius_score > 0.0
    assert len(result.containment_boundaries) > 0
    assert len(result.unaffected) > 0  # Not everything is attacked


def test_scenario_engine_lifecycle_and_step():
    """Verify scenario catalog, start, step progression, and threat registration."""
    catalog = scenario_engine.get_catalog()
    assert len(catalog) == 6

    # Start DDoS scenario without auto-progress for synchronous verification
    res = scenario_engine.start_scenario(
        scenario_type=ScenarioType.DDOS_TRAFFIC_FLOOD.value,
        auto_progress=False,
    )
    assert res["status"] == "STARTED"
    assert twin_state_engine.get_lifecycle_state() == ScenarioLifecycleState.ATTACK_INITIATED

    # Step to SUSPICIOUS_ACTIVITY
    step1 = scenario_engine.step_progression()
    assert step1["status"] == "ADVANCED"
    assert twin_state_engine.get_lifecycle_state() == ScenarioLifecycleState.SUSPICIOUS_ACTIVITY

    # Step to ANALYSING
    step2 = scenario_engine.step_progression()
    assert step2["status"] == "ADVANCED"
    assert twin_state_engine.get_lifecycle_state() == ScenarioLifecycleState.ANALYSING

    # Step to THREAT_DETECTED
    step3 = scenario_engine.step_progression()
    assert step3["status"] == "ADVANCED"
    assert twin_state_engine.get_lifecycle_state() == ScenarioLifecycleState.THREAT_DETECTED

    # Verify threat is registered in state engine
    snapshot = twin_state_engine.get_snapshot()
    assert len(snapshot.active_threats) >= 1
    assert snapshot.active_threats[0].severity == "CRITICAL"
    assert snapshot.overall_health_score < 100.0


def test_mitigation_and_verifiable_recovery():
    """Verify mitigation action execution and restoration of network metrics."""
    # Start and advance scenario to THREAT_DETECTED
    scenario_engine.start_scenario(
        scenario_type=ScenarioType.DDOS_TRAFFIC_FLOOD.value,
        auto_progress=False,
    )
    scenario_engine.step_progression(ScenarioLifecycleState.THREAT_DETECTED)

    # Check degraded UPF
    upf_degraded = twin_state_engine.get_component("upf-01")
    assert upf_degraded.security_status in (SecurityStatus.ATTACKED, SecurityStatus.SUSPICIOUS)

    # Apply Rate Limiting mitigation without auto-verify background thread
    mit_res = mitigation_engine.apply_mitigation(
        action_type=MitigationActionType.RATE_LIMITING.value,
        target_component="upf-01",
        auto_verify=False,
    )
    assert mit_res["status"] == "APPLIED"
    assert twin_state_engine.get_lifecycle_state() == ScenarioLifecycleState.MITIGATING

    # Trigger verification pass
    mitigation_engine._run_verification_worker(mit_res["action_id"])

    # Verify recovered state
    assert twin_state_engine.get_lifecycle_state() == ScenarioLifecycleState.RECOVERED
    upf_recovered = twin_state_engine.get_component("upf-01")
    assert upf_recovered.security_status == SecurityStatus.SECURE
    assert upf_recovered.operational_status == OperationalStatus.ACTIVE
    assert upf_recovered.packet_loss_pct <= 0.1

    # Verify all threats marked mitigated
    snapshot = twin_state_engine.get_snapshot()
    assert all(t.is_mitigated for t in snapshot.active_threats)


def test_whatif_experiment_sandbox():
    """Verify isolated what-if simulation does not mutate active twin state."""
    initial_version = twin_state_engine.get_state_version()
    initial_health = twin_state_engine.calculate_overall_health()

    templates = whatif_engine.get_templates()
    assert len(templates) >= 5

    # Run what-if UPF outage experiment
    exp = whatif_engine.simulate_what_if(
        name="Test UPF Failure",
        hypothesis="Simulate loss of primary UPF",
        scenario_type="UPF_OUTAGE",
        target_component="upf-01",
    )

    assert exp.experiment_id.startswith("exp-whatif-")
    assert exp.predicted_metrics["overall_health"] < initial_health
    assert exp.impact_delta["health_drop"] > 0.0
    assert len(exp.assumptions) > 0
    assert len(exp.limitations) > 0
    assert len(exp.recommendation) > 0

    # Ensure live twin state remains pristine
    assert twin_state_engine.get_state_version() == initial_version
    assert twin_state_engine.calculate_overall_health() == initial_health


def test_resilience_scoring_formula():
    """Verify quantitative resilience score calculation and mathematical properties."""
    snapshot = twin_state_engine.get_snapshot()

    # Nominal state: perfect score
    res_nominal = resilience_engine.calculate_resilience(snapshot)
    assert res_nominal.resilience_score == 100.0
    assert res_nominal.assessment_grade == "EXCELLENT"

    # Degraded state simulation
    res_degraded = resilience_engine.calculate_resilience(
        snapshot=snapshot,
        ttd_sec=15.0,
        ttm_sec=25.0,
        ttr_sec=30.0,
        residual_impact_ratio=0.15,
    )
    assert res_degraded.resilience_score < 100.0
    assert res_degraded.time_to_detect_sec == 15.0
    assert res_degraded.time_to_mitigate_sec == 25.0
    assert res_degraded.time_to_recover_sec == 30.0


def test_rest_api_state_and_topology():
    """Verify REST endpoints for state and topology return valid schemas."""
    resp = client.get("/api/twin/state")
    assert resp.status_code == 200
    data = resp.json()
    assert "components" in data
    assert "connections" in data
    assert "slices" in data
    assert data["provenance"] == "SIMULATED"

    resp_topo = client.get("/api/twin/topology")
    assert resp_topo.status_code == 200
    topo = resp_topo.json()
    assert "nodes" in topo
    assert "links" in topo
    assert topo["total_nodes"] >= 25


def test_rest_api_scenarios_and_propagation():
    """Verify REST endpoints for scenarios and propagation calculations."""
    # List scenarios
    resp_scen = client.get("/api/twin/scenarios")
    assert resp_scen.status_code == 200
    assert len(resp_scen.json()["scenarios"]) == 6

    # Calculate ad-hoc propagation
    resp_prop = client.post(
        "/api/twin/propagate",
        json={"entry_point": "ue-camera-01", "target_component": "upf-01", "intensity": 3.0},
    )
    assert resp_prop.status_code == 200
    prop_data = resp_prop.json()
    assert "upf-01" in prop_data["directly_targeted"]


def test_rest_api_mitigation_and_whatif():
    """Verify REST endpoints for mitigations and what-if simulation."""
    # Mitigations catalog
    resp_mit = client.get("/api/twin/mitigation/actions")
    assert resp_mit.status_code == 200
    assert len(resp_mit.json()["actions"]) >= 5

    # What-If simulation
    resp_whatif = client.post(
        "/api/twin/what-if/simulate",
        json={
            "name": "API What-If Test",
            "hypothesis": "Testing via API",
            "scenario_type": "UPF_OUTAGE",
            "target_component": "upf-01",
        },
    )
    assert resp_whatif.status_code == 200
    assert "predicted_metrics" in resp_whatif.json()


def test_websocket_streaming():
    """Verify WebSocket connection sends initial snapshot and handles commands."""
    with client.websocket_connect("/api/twin/ws") as websocket:
        initial_msg = websocket.receive_json()
        assert initial_msg["event_type"] == "INITIAL_SNAPSHOT"
        assert "data" in initial_msg
        assert "components" in initial_msg["data"]

        # Send PING command
        websocket.send_text('{"action": "PING"}')
        pong_msg = websocket.receive_json()
        assert pong_msg["event_type"] == "PONG"
