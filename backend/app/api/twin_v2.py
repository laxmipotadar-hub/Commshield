"""CommShield AI Digital Twin v2 REST and WebSocket API.

Provides stable, strictly typed endpoints for the Windows 3D Frontend and External Consumers:
- State & Topology: /api/twin/state, /api/twin/topology, /api/twin/components/{id}
- High-Resolution Telemetry: /api/twin/telemetry
- Cyber Attack Scenarios: /api/twin/scenarios, /api/twin/scenarios/start, pause, resume, stop, reset
- Blast Radius Propagation: /api/twin/propagation, /api/twin/propagate
- Cybersecurity Mitigation: /api/twin/mitigation/actions, /api/twin/mitigation/apply, /api/twin/mitigation/status
- What-If Experimentation Sandbox: /api/twin/what-if/templates, /api/twin/what-if/simulate, history
- Quantitative Resilience: /api/twin/resilience
- Historical Incident Ledger: /api/twin/events
- Real-Time WebSocket Synchronization: /api/twin/ws
"""

import asyncio
from datetime import datetime, timezone
import json
import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field

from ..twin.mitigation import mitigation_engine
from ..twin.models import (
    AttackPropagationResult,
    DigitalTwinStateSnapshot,
    HistoricalNetworkEvent,
    IncidentRecord,
    MitigationActionRecord,
    MitigationActionType,
    MitigationRecommendation,
    NetworkComponent,
    NetworkConnection,
    NetworkSliceInfo,
    ResilienceMetrics,
    ScenarioType,
    TelemetryMetric,
    TrafficBreakdown,
    WhatIfExperimentRecord,
)
from ..twin.propagation import AttackPropagationEngine
from ..twin.resilience import resilience_engine
from ..twin.scenarios import scenario_engine
from ..twin.state_engine import twin_state_engine

logger = logging.getLogger("commshield.twin.api")

router = APIRouter(prefix="/twin", tags=["Digital Twin Core v2"])
propagation_engine = AttackPropagationEngine()


# -------------------------------------------------------------
# Request Schemas
# -------------------------------------------------------------

class StartScenarioRequest(BaseModel):
    scenario_type: str = Field(..., description="Scenario type identifier e.g. DDOS_TRAFFIC_FLOOD")
    target_component: Optional[str] = Field(None, description="Target component ID e.g. upf-01")
    entry_point: Optional[str] = Field(None, description="Entry point component ID e.g. ue-camera-01")
    intensity: float = Field(3.0, ge=1.0, le=10.0, description="Attack traffic intensity multiplier")
    auto_progress: bool = Field(True, description="Whether lifecycle automatically steps through phases")
    is_distributed: bool = Field(False, description="Whether attack originates from multiple distributed sources")
    attacker_sources: Optional[List[str]] = Field(None, description="Explicit list of attacker source UEs")


class PropagateRequest(BaseModel):
    entry_point: str = Field("ue-camera-01", description="Ingress component")
    target_component: str = Field("upf-01", description="Target component")
    intensity: float = Field(3.0, ge=1.0, le=10.0, description="Traffic intensity multiplier")
    is_distributed: bool = Field(False, description="Whether propagation includes multiple distributed sources")
    attacker_sources: Optional[List[str]] = Field(None, description="Attacker sources")


class ApplyMitigationRequest(BaseModel):
    action_type: str = Field("RATE_LIMITING", description="Mitigation action type")
    target_component: str = Field("upf-01", description="Component or node to apply mitigation")
    target_slice: Optional[str] = Field(None, description="Optional target slice ID")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Action-specific parameters")
    auto_verify: bool = Field(True, description="Whether to trigger automated verification and recovery")


class WhatIfRequest(BaseModel):
    name: str = Field(..., description="Descriptive title of the hypothetical experiment")
    hypothesis: str = Field(..., description="Hypothesis statement being tested")
    scenario_type: str = Field("UPF_OUTAGE", description="Hypothetical scenario type")
    target_component: str = Field("upf-01", description="Target component ID")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Custom parameters")


class ApproveRecommendationRequest(BaseModel):
    recommendation_id: str = Field(..., description="Recommendation ID to approve")


class SetDefenceModeRequest(BaseModel):
    mode: str = Field(..., description="Operating mode: AUTOMATIC or MANUAL")


class SetDetectionConfigRequest(BaseModel):
    sensitivity: Optional[str] = Field(None, description="Sensitivity: LOW, MEDIUM, or HIGH")
    threshold: Optional[float] = Field(None, description="Anomaly threshold between 0.0 and 1.0")
    ai_detection_enabled: Optional[bool] = Field(None, description="Toggle AI detection engine")


class SetSpeedRequest(BaseModel):
    speed: float = Field(..., description="Simulation speed: 0.5, 1.0, 2.0, 5.0, or 10.0")


class SetDataModeRequest(BaseModel):
    mode: str = Field(..., description="Data mode: REAL_DATASET, LIVE_SIMULATION, or HYBRID")


class SetSyntheticRequest(BaseModel):
    enabled: bool = Field(..., description="Toggle synthetic data generation")


class SetActiveSliceRequest(BaseModel):
    slice_id: str = Field(..., description="Target slice ID: e.g. sst-1-sd-010203")


class SetEnsembleFusionRequest(BaseModel):
    enabled: bool = Field(..., description="Toggle multi-detector ensemble fusion")


class VerifyMitigationRequest(BaseModel):
    action_id: Optional[str] = Field(None, description="Specific mitigation action ID or omit for latest")


class RollbackPolicyRequest(BaseModel):
    action_id: str = Field(..., description="Action ID to roll back")


# -------------------------------------------------------------
# State & Topology Endpoints
# -------------------------------------------------------------

@router.get("/state", response_model=DigitalTwinStateSnapshot)
def get_twin_state():
    """Retrieve full authoritative snapshot of the 5G Digital Twin single source of truth."""
    return twin_state_engine.get_snapshot()


@router.get("/topology")
def get_topology():
    """Retrieve graph topology with 3D coordinates, node metadata, and logical links."""
    components = twin_state_engine.get_components()
    connections = twin_state_engine.get_connections()
    slices = twin_state_engine.get_slices()

    return {
        "nodes": [comp.model_dump() for comp in components.values()],
        "links": [conn.model_dump() for conn in connections.values()],
        "slices": [s.model_dump() for s in slices.values()],
        "total_nodes": len(components),
        "total_links": len(connections),
        "total_slices": len(slices),
        "state_version": twin_state_engine.get_state_version(),
    }


@router.get("/components/{component_id}", response_model=NetworkComponent)
def get_component(component_id: str):
    """Retrieve real-time health, performance, and security status for a single network entity."""
    comp = twin_state_engine.get_component(component_id)
    if not comp:
        raise HTTPException(status_code=404, detail=f"Component '{component_id}' not found in Digital Twin.")
    return comp


@router.get("/telemetry")
def get_telemetry(
    component_id: Optional[str] = Query(None, description="Component ID or omit for global"),
    metric_name: Optional[str] = Query(None, description="Specific metric name"),
    limit: int = Query(30, ge=1, le=120, description="Number of historical samples"),
):
    """Retrieve classified telemetry series for graphing and trend inspection."""
    if metric_name:
        history = twin_state_engine.get_telemetry_history(component_id, metric_name, limit=limit)
        return {"component_id": component_id, "metric_name": metric_name, "series": [m.model_dump() for m in history]}
    
    # Return overview of key metrics
    return {
        "overall_health": twin_state_engine.calculate_overall_health(),
        "throughput_mbps": sum(c.traffic_volume_mbps for c in twin_state_engine.get_components().values()),
        "state_version": twin_state_engine.get_state_version(),
    }


# -------------------------------------------------------------
# Attack Scenario Lifecycle Endpoints
# -------------------------------------------------------------

@router.get("/scenarios")
def list_scenarios():
    """List catalog of 6 supported Private 5G cyber attack scenarios."""
    return {"scenarios": scenario_engine.get_catalog()}


@router.get("/scenarios/active")
def get_active_scenario():
    """Retrieve details of the active attack scenario and current lifecycle phase."""
    active = scenario_engine.get_active_scenario()
    return {
        "active": active is not None,
        "scenario": active,
        "lifecycle_state": twin_state_engine.get_lifecycle_state().value,
    }


@router.post("/scenarios/start")
def start_scenario(req: StartScenarioRequest):
    """Initiate an attack scenario with causal metric propagation across the 5G graph."""
    result = scenario_engine.start_scenario(
        scenario_type=req.scenario_type,
        target_component=req.target_component,
        entry_point=req.entry_point,
        intensity=req.intensity,
        auto_progress=req.auto_progress,
        is_distributed=req.is_distributed,
        attacker_sources=req.attacker_sources,
    )
    if result.get("status") == "ALREADY_RUNNING":
        raise HTTPException(status_code=409, detail=result.get("message"))
    return result


@router.post("/scenarios/step")
def step_scenario():
    """Manually advance the active scenario by one lifecycle phase."""
    result = scenario_engine.step_progression()
    if result.get("status") == "NO_ACTIVE_SCENARIO":
        raise HTTPException(status_code=400, detail="No active scenario to advance.")
    return result


@router.post("/scenarios/pause")
def pause_scenario():
    """Pause the background progression of an active attack simulation."""
    result = scenario_engine.pause_scenario()
    if result.get("status") == "NO_ACTIVE_SCENARIO":
        raise HTTPException(status_code=400, detail="No active scenario to pause.")
    return result


@router.post("/scenarios/resume")
def resume_scenario():
    """Resume execution of a paused attack simulation."""
    result = scenario_engine.resume_scenario()
    if result.get("status") == "NO_ACTIVE_SCENARIO":
        raise HTTPException(status_code=400, detail="No active scenario to resume.")
    return result


@router.post("/scenarios/stop")
def stop_scenario():
    """Stop the active attack simulation."""
    result = scenario_engine.stop_scenario()
    return result


@router.post("/scenarios/reset")
def reset_simulation():
    """Reset the Digital Twin state, telemetry, and health back to nominal baseline."""
    result = scenario_engine.reset_simulation()
    return result


# -------------------------------------------------------------
# Blast Radius & Attack Propagation
# -------------------------------------------------------------

@router.get("/propagation")
def get_current_propagation():
    """Retrieve current attack path, blast radius score, and affected component breakdown."""
    prop = twin_state_engine.get_propagation_result()
    if not prop:
        return {
            "status": "NO_ACTIVE_PROPAGATION",
            "message": "No active attack scenario. Run /api/twin/scenarios/start or /api/twin/propagate.",
            "blast_radius_score": 0.0,
            "directly_targeted": [],
            "indirectly_affected": [],
            "potentially_affected": [],
            "unaffected": [c for c in twin_state_engine.get_components().keys()],
        }
    return prop.model_dump()


@router.post("/propagate", response_model=AttackPropagationResult)
def calculate_hypothetical_propagation(req: PropagateRequest):
    """Deterministically compute graph-based blast radius for any ingress/target pair without mutating state."""
    components = twin_state_engine.get_components()
    connections = twin_state_engine.get_connections()
    return propagation_engine.compute_propagation(
        scenario_id="ad-hoc-propagation",
        entry_point=req.entry_point,
        target_component=req.target_component,
        components=components,
        connections=connections,
        traffic_intensity_multiplier=req.intensity,
    )


# -------------------------------------------------------------
# Mitigation & Verifiable Recovery
# -------------------------------------------------------------

@router.get("/mitigation/actions")
def get_supported_mitigations():
    """List supported multi-tier cybersecurity mitigations."""
    return {"actions": mitigation_engine.get_supported_actions()}


@router.post("/mitigation/apply")
def apply_mitigation(req: ApplyMitigationRequest):
    """Enact cybersecurity mitigation and begin verifiable metric recovery."""
    result = mitigation_engine.apply_mitigation(
        action_type=req.action_type,
        target_component=req.target_component,
        target_slice=req.target_slice,
        parameters=req.parameters,
        auto_verify=req.auto_verify,
    )
    return result


@router.get("/mitigation/status")
def get_mitigation_status():
    """Retrieve status of active mitigations and historical recovery actions."""
    return {
        "active_mitigations": [m.model_dump() for m in twin_state_engine.get_active_mitigations()],
        "history": [m.model_dump() for m in mitigation_engine.get_action_history()],
        "lifecycle_state": twin_state_engine.get_lifecycle_state().value,
    }


# -------------------------------------------------------------
# Cyber Defence Operations & Intelligent Defence Operations Centre
# -------------------------------------------------------------

@router.get("/traffic/breakdown", response_model=TrafficBreakdown)
def get_traffic_breakdown():
    """Retrieve real-time split of normal, legitimate, malicious, and blocked traffic."""
    return twin_state_engine.get_traffic_breakdown()


@router.get("/defence/recommendations")
def get_defence_recommendations():
    """Retrieve active mitigation recommendations proposed by policy decision engine."""
    recs = twin_state_engine.get_recommendations()
    return {"recommendations": [r.model_dump() for r in recs], "count": len(recs)}


@router.post("/defence/approve")
def approve_recommendation(req: ApproveRecommendationRequest):
    """Operator explicitly approves a recommended mitigation action."""
    rec = twin_state_engine.approve_recommendation(req.recommendation_id)
    if not rec:
        raise HTTPException(status_code=404, detail=f"Recommendation '{req.recommendation_id}' not found.")
    
    # Automatically apply approved action
    apply_result = mitigation_engine.apply_mitigation(
        action_type=rec.proposed_action.value,
        target_component=rec.target_component,
        target_slice=rec.target_slice,
        parameters=rec.parameters,
        auto_verify=True,
    )
    return {
        "status": "APPROVED_AND_EXECUTED",
        "recommendation": rec.model_dump(),
        "execution": apply_result,
    }


@router.post("/defence/execute")
def execute_defence_action(req: ApplyMitigationRequest):
    """Manually execute specific mitigation defence action."""
    return mitigation_engine.apply_mitigation(
        action_type=req.action_type,
        target_component=req.target_component,
        target_slice=req.target_slice,
        parameters=req.parameters,
        auto_verify=req.auto_verify,
    )


@router.post("/defence/verify")
def verify_defence_containment(req: VerifyMitigationRequest):
    """Trigger verification engine audit to assess containment efficacy and legitimate traffic safety."""
    return mitigation_engine.verify_mitigation(req.action_id)


@router.post("/defence/recover")
def initiate_network_recovery():
    """Initiate complete network recovery returning metrics and components to nominal state."""
    return mitigation_engine.initiate_recovery()


@router.post("/defence/rollback")
def rollback_defence_policy(req: RollbackPolicyRequest):
    """Roll back an applied mitigation action and restore baseline parameters."""
    return mitigation_engine.rollback_policy(req.action_id)


@router.get("/defence/mode")
def get_defence_mode():
    """Retrieve current defence operating mode: AUTOMATIC or MANUAL."""
    return {"mode": twin_state_engine.get_defence_mode()}


@router.post("/defence/mode")
def set_defence_mode(req: SetDefenceModeRequest):
    """Switch operating mode between AUTOMATIC and MANUAL defence."""
    new_mode = twin_state_engine.set_defence_mode(req.mode)
    return {"mode": new_mode, "status": "MODE_UPDATED"}


@router.get("/detection/config")
def get_detection_config():
    """Retrieve active detection configuration, sensitivity, and thresholds."""
    return twin_state_engine.get_detection_config()


@router.post("/detection/config")
def set_detection_config(req: SetDetectionConfigRequest):
    """Update detection sensitivity (LOW, MEDIUM, HIGH) and threshold."""
    return twin_state_engine.set_detection_config(
        sensitivity=req.sensitivity,
        threshold=req.threshold,
        ai_detection_enabled=req.ai_detection_enabled,
    )


@router.get("/speed")
def get_simulation_speed():
    """Retrieve active simulation speed multiplier."""
    return {"speed": twin_state_engine.get_simulation_speed()}


@router.post("/speed")
def set_simulation_speed(req: SetSpeedRequest):
    """Set simulation speed multiplier (0.5x, 1x, 2x, 5x, 10x)."""
    speed = twin_state_engine.set_simulation_speed(req.speed)
    return {"speed": speed, "status": "SPEED_UPDATED"}


@router.get("/data/mode")
def get_data_mode():
    """Retrieve current data mode (REAL_DATASET, LIVE_SIMULATION, HYBRID)."""
    return {"data_mode": twin_state_engine.get_data_mode()}


@router.post("/data/mode")
def set_data_mode(req: SetDataModeRequest):
    """Switch data mode between REAL_DATASET, LIVE_SIMULATION, and HYBRID."""
    mode = twin_state_engine.set_data_mode(req.mode)
    return {"data_mode": mode, "status": "DATA_MODE_UPDATED"}


@router.get("/data/synthetic")
def get_synthetic_data_status():
    """Retrieve synthetic data generation toggle status."""
    return {"synthetic_enabled": twin_state_engine.get_synthetic_enabled()}


@router.post("/data/synthetic")
def set_synthetic_data_status(req: SetSyntheticRequest):
    """Toggle synthetic data generation on or off."""
    enabled = twin_state_engine.set_synthetic_enabled(req.enabled)
    return {"synthetic_enabled": enabled, "status": "SYNTHETIC_DATA_UPDATED"}


@router.get("/slice/active")
def get_active_slice():
    """Retrieve currently active network slice ID."""
    return {"active_slice_id": twin_state_engine.get_active_slice()}


@router.post("/slice/active")
def set_active_slice(req: SetActiveSliceRequest):
    """Switch active network slice context."""
    slice_id = twin_state_engine.set_active_slice(req.slice_id)
    return {"active_slice_id": slice_id, "status": "ACTIVE_SLICE_UPDATED"}


@router.get("/detection/fusion")
def get_ensemble_fusion_status():
    """Retrieve multi-detector ensemble fusion toggle state."""
    return {"ensemble_fusion_enabled": twin_state_engine.get_ensemble_fusion()}


@router.post("/detection/fusion")
def set_ensemble_fusion_status(req: SetEnsembleFusionRequest):
    """Toggle multi-detector ensemble fusion on or off."""
    enabled = twin_state_engine.set_ensemble_fusion(req.enabled)
    return {"ensemble_fusion_enabled": enabled, "status": "ENSEMBLE_FUSION_UPDATED"}


@router.get("/data/integrity")
def get_data_integrity():
    """Retrieve comprehensive data integrity, validation rules, and schema conformance status."""
    return twin_state_engine.get_data_integrity_report()


@router.get("/incidents")
def list_incidents():
    """Retrieve immutable forensic ledger of historical attack incidents."""
    incidents = twin_state_engine.get_incidents()
    return {"incidents": [inc.model_dump() for inc in incidents], "count": len(incidents)}


@router.get("/incidents/{incident_id}")
def get_incident_detail(incident_id: str):
    """Retrieve full forensic detail for a single incident."""
    inc = twin_state_engine.get_incident(incident_id)
    if not inc:
        raise HTTPException(status_code=404, detail=f"Incident '{incident_id}' not found.")
    return inc.model_dump()


@router.get("/incidents/{incident_id}/report")
def export_incident_report(incident_id: str, format: str = Query("markdown", description="markdown or json")):
    """Export formatted incident forensic report in Markdown or JSON format."""
    inc = twin_state_engine.get_incident(incident_id)
    if not inc:
        raise HTTPException(status_code=404, detail=f"Incident '{incident_id}' not found.")
    
    if format.lower() == "json":
        return inc.model_dump()

    md_report = f"""# COMMSHIELD CYBER DEFENCE INCIDENT REPORT
## Incident Reference: `{inc.incident_id}`

- **Attack Classification:** {inc.attack_type}
- **Severity Rating:** {inc.severity}
- **Target Infrastructure:** `{inc.target_component}`
- **Containment Verdict:** `{inc.verification_status}`
- **Legitimate Traffic Preserved:** {inc.legitimate_preserved_pct}%
- **Peak Malicious Ingress:** {inc.peak_malicious_traffic_mbps} Mbps
- **Packets Blocked:** {inc.blocked_packets_count:,}

### Forensic Timeline
- **Attack Initiated:** {inc.start_time}
- **Threat Detected:** {inc.detection_time or 'N/A'}
- **Policy Applied:** {inc.mitigation_time or 'N/A'}
- **Mitigation Verified:** {inc.verification_time or 'N/A'}
- **Full Recovery:** {inc.recovery_time or 'N/A'}

### Impacted Infrastructure Nodes
{chr(10).join(f"- `{n}`" for n in inc.affected_nodes)}

### Enacted Mitigation Policies
{chr(10).join(f"- **{p}**" for p in inc.applied_policies)}

### Telemetry Evidence & Verification Checklist
```json
{json.dumps(inc.evidence, indent=2)}
```

### Outcome Summary
> {inc.final_outcome}
"""
    return {"incident_id": inc.incident_id, "format": "markdown", "report": md_report}


# -------------------------------------------------------------
# What-If Experimentation Sandbox
# -------------------------------------------------------------

@router.get("/what-if/templates")
def get_whatif_templates():
    """Retrieve standardized What-If hypothetical questions."""
    from ..twin.whatif import whatif_engine
    return {"templates": whatif_engine.get_templates()}


@router.post("/what-if/simulate", response_model=WhatIfExperimentRecord)
def run_whatif_simulation(req: WhatIfRequest):
    """Run hypothetical simulation on an isolated clone of the digital twin graph."""
    from ..twin.whatif import whatif_engine
    return whatif_engine.simulate_what_if(
        name=req.name,
        hypothesis=req.hypothesis,
        scenario_type=req.scenario_type,
        target_component=req.target_component,
        parameters=req.parameters,
    )


@router.get("/what-if/history")
def get_whatif_history():
    """Retrieve history of completed What-If experiments."""
    from ..twin.whatif import whatif_engine
    return {"experiments": [e.model_dump() for e in whatif_engine.get_history()]}


# -------------------------------------------------------------
# Resilience Intelligence & Historical Events
# -------------------------------------------------------------

@router.get("/resilience", response_model=ResilienceMetrics)
def get_resilience():
    """Retrieve quantitative network resilience metrics and mathematical formula."""
    snapshot = twin_state_engine.get_snapshot()
    return resilience_engine.calculate_resilience(snapshot)


@router.get("/events")
def list_events(
    scenario_id: Optional[str] = Query(None, description="Filter by scenario ID"),
    severity: Optional[str] = Query(None, description="Filter by severity e.g. CRITICAL, WARNING"),
    limit: int = Query(50, ge=1, le=200, description="Max event count"),
):
    """Retrieve immutable timestamped incident ledger entries."""
    events = twin_state_engine.get_historical_events(scenario_id=scenario_id, severity=severity, limit=limit)
    return {"events": [e.model_dump() for e in events], "count": len(events)}


# -------------------------------------------------------------
# Real-Time WebSocket Streaming Endpoint
# -------------------------------------------------------------

@router.websocket("/ws")
async def digital_twin_websocket(websocket: WebSocket):
    """Full-duplex WebSocket stream for real-time 3D state synchronization."""
    await websocket.accept()
    loop = asyncio.get_running_loop()
    client_queue: asyncio.Queue = asyncio.Queue(maxsize=100)

    # Bridge synchronous state engine callback to async queue
    def on_state_event(event_dict: Dict[str, Any]):
        try:
            loop.call_soon_threadsafe(
                lambda: client_queue.put_nowait(event_dict) if not client_queue.full() else None
            )
        except Exception:
            pass

    twin_state_engine.subscribe(on_state_event)
    logger.info("New WebSocket client connected to /api/twin/ws")

    # Send initial snapshot
    initial_snapshot = twin_state_engine.get_snapshot()
    await websocket.send_text(json.dumps({
        "event_type": "INITIAL_SNAPSHOT",
        "version": initial_snapshot.version,
        "timestamp": initial_snapshot.timestamp,
        "data": initial_snapshot.model_dump(),
    }))

    async def sender_task():
        """Pushes events from queue out to the WebSocket client."""
        while True:
            event_data = await client_queue.get()
            await websocket.send_text(json.dumps(event_data))
            client_queue.task_done()

    async def receiver_task():
        """Listens for client ping/commands over the WebSocket."""
        while True:
            msg = await websocket.receive_text()
            try:
                cmd = json.loads(msg)
                action = cmd.get("action") or cmd.get("type")
                if action in ("PING", "ping"):
                    await websocket.send_text(json.dumps({"event_type": "PONG", "timestamp": datetime.now(timezone.utc).isoformat()}))
                elif action == "subscribe":
                    await websocket.send_text(json.dumps({
                        "event_type": "SUBSCRIBED",
                        "type": "subscribed",
                        "payload": cmd.get("payload", {}),
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    }))
                elif action == "GET_SNAPSHOT":
                    snap = twin_state_engine.get_snapshot()
                    await websocket.send_text(json.dumps({
                        "event_type": "SNAPSHOT_RESPONSE",
                        "data": snap.model_dump(),
                    }))
            except Exception:
                pass

    sender = asyncio.create_task(sender_task())
    receiver = asyncio.create_task(receiver_task())

    try:
        # Wait until either task fails or client disconnects
        done, pending = await asyncio.wait(
            [sender, receiver],
            return_when=asyncio.FIRST_COMPLETED,
        )
        for task in pending:
            task.cancel()
    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected from /api/twin/ws")
    finally:
        twin_state_engine.unsubscribe(on_state_event)
        sender.cancel()
        receiver.cancel()
# CommShield AI Core
