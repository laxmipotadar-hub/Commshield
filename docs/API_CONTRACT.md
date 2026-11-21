# CommShield AI — Digital Twin API Contract & Integration Specification

**Version:** 2.0.0  
**Target Environment:** CommShield Private 5G Digital Twin Core (Ubuntu Backend & Windows 3D Frontend)  
**Base REST URL:** `http://<host>:8000/api/twin`  
**WebSocket URL:** `ws://<host>:8000/api/twin/ws`  
**CORS Status:** Enabled for `http://localhost:5173`, `http://localhost:3000`, `http://127.0.0.1:*`, and all LAN client origins.

---

## 1. Overview & Architectural Guarantees

This document serves as the **authoritative and stable API contract** for the CommShield AI 5G Digital Twin. The Windows 3D visualization and dashboard consume these endpoints.

### Key Guarantees:
1. **Single Source of Truth:** All graph nodes, connections, slices, active threats, mitigations, and resilience metrics are governed centrally by `CentralDigitalTwinStateEngine`.
2. **State Versioning:** Every state mutation increments `state_version` monotonically.
3. **Strict Data Provenance Classification:** Every metric, node, and link payload includes a `provenance` field:
   - `LIVE`: Hardware/Radio telemetry from physical interfaces.
   - `BACKEND`: Verified ground truth from the central state engine.
   - `SIMULATED`: Real-time mathematical simulation under cyber-attack conditions.
   - `DERIVED`: Graph analytics (e.g., blast radius, causal dependency scores).
   - `PREDICTED`: Decoupled What-If machine learning / heuristic projections.
4. **Verifiable Mitigations:** Mitigations follow an explicit lifecycle (`REQUESTED` $\rightarrow$ `IN_PROGRESS` $\rightarrow$ `VERIFYING` $\rightarrow$ `SUCCESSFUL`), with measurable metric recovery back to nominal levels.

---

## 2. Global Enums & Data Types

### DataClassification
`"LIVE"` | `"BACKEND"` | `"SIMULATED"` | `"DERIVED"` | `"PREDICTED"`

### OperationalStatus
`"ACTIVE"` | `"DEGRADED"` | `"CRITICAL"` | `"ISOLATED"` | `"OFFLINE"`

### SecurityStatus
`"SECURE"` | `"SUSPICIOUS"` | `"ATTACKED"` | `"COMPROMISED"` | `"QUARANTINED"`

### ConnectionType
`"CONTROL_PLANE"` | `"USER_PLANE"`

### ConnectionStatus
`"ACTIVE"` | `"CONGESTED"` | `"DEGRADED"` | `"DOWN"` | `"THROTTLED"`

### ScenarioLifecycleState
`"NORMAL"` | `"ATTACK_INITIATED"` | `"SUSPICIOUS_ACTIVITY"` | `"ANALYSING"` | `"THREAT_DETECTED"` | `"MITIGATING"` | `"VERIFYING_MITIGATION"` | `"RECOVERED"` | `"DETECTION_FAILED"` | `"MITIGATION_FAILED"` | `"RECOVERY_FAILED"` | `"SIMULATION_STOPPED"`

### ScenarioType
`"DDOS_TRAFFIC_FLOOD"` | `"AUTH_ANOMALY"` | `"SLICE_RESOURCE_ABUSE"` | `"UPF_OVERLOAD"` | `"SUSPICIOUS_UE_ACTIVITY"` | `"GATEWAY_COMPROMISE"`

### MitigationActionType
`"RATE_LIMITING"` | `"TRAFFIC_RESTRICTION"` | `"SUSPICIOUS_SOURCE_ISOLATION"` | `"SESSION_TERMINATION"` | `"COMPONENT_ISOLATION"` | `"SLICE_PROTECTION"` | `"POLICY_UPDATE"`

### MitigationStatus
`"REQUESTED"` | `"IN_PROGRESS"` | `"VERIFYING"` | `"SUCCESSFUL"` | `"FAILED"`

---

## 3. REST API Specification

### 3.1 State & Topology

#### `GET /api/twin/state`
Returns the complete authoritative snapshot of the 5G Digital Twin single source of truth.

- **Response:** `200 OK`
```json
{
  "version": 42,
  "timestamp": "2026-11-21T14:00:00Z",
  "provenance": "SIMULATED",
  "overall_health_score": 98.4,
  "active_scenario_id": null,
  "lifecycle_state": "NORMAL",
  "total_components_count": 28,
  "active_ues_count": 13,
  "network_throughput_mbps": 154.2,
  "average_latency_ms": 2.14,
  "average_packet_loss_pct": 0.005,
  "components": {
    "upf-01": {
      "id": "upf-01",
      "name": "UPF-01",
      "component_type": "UPF",
      "network_role": "Core User Plane Gateway",
      "operational_status": "ACTIVE",
      "health_score": 100.0,
      "cpu_utilization_pct": 28.5,
      "memory_utilization_pct": 42.0,
      "traffic_volume_mbps": 75.5,
      "latency_ms": 2.1,
      "packet_loss_pct": 0.01,
      "connected_components": ["gnb-01", "smf-01", "router-edge-01", "switch-core-01", "edge-node-01"],
      "network_slice": "ALL",
      "security_status": "SECURE",
      "provenance": "SIMULATED",
      "coordinates_3d": { "x": 8.0, "y": 0.0, "z": 0.0 },
      "metadata": { "gtpu_port": 2152, "pfcp_port": 8805, "capacity_gbps": 10.0 }
    }
  },
  "connections": {
    "conn-n3-gnb-upf": {
      "id": "conn-n3-gnb-upf",
      "source": "gnb-01",
      "destination": "upf-01",
      "connection_type": "USER_PLANE",
      "direction": "BIDIRECTIONAL",
      "protocol": "N3 (GTP-U UDP 2152)",
      "capacity_mbps": 10000.0,
      "utilization_mbps": 75.5,
      "utilization_pct": 0.75,
      "latency_ms": 2.1,
      "packet_loss_pct": 0.01,
      "connection_status": "ACTIVE",
      "associated_slice": "ALL",
      "security_status": "NORMAL",
      "provenance": "SIMULATED"
    }
  },
  "slices": {
    "sst-1-sd-010203": {
      "slice_id": "sst-1-sd-010203",
      "name": "eMBB High-Throughput (4K Surveillance & AR)",
      "sst": 1,
      "sd": "010203",
      "allocated_bandwidth_mbps": 500.0,
      "current_throughput_mbps": 45.2,
      "max_latency_ms": 20.0,
      "current_latency_ms": 8.5,
      "target_packet_loss_pct": 0.1,
      "current_packet_loss_pct": 0.01,
      "active_ues_count": 4,
      "security_state": "NOMINAL",
      "isolation_guarantee": "Dedicated UPF Session & VLAN 100"
    }
  },
  "active_threats": [],
  "active_mitigations": [],
  "recent_events": [],
  "resilience": {
    "time_to_detect_sec": 0.0,
    "time_to_mitigate_sec": 0.0,
    "time_to_recover_sec": 0.0,
    "service_availability_pct": 100.0,
    "network_degradation_pct": 0.0,
    "affected_components_count": 0,
    "affected_slices_count": 0,
    "residual_impact_pct": 0.0,
    "resilience_score": 100.0,
    "formula_documentation": "Resilience = 100 * [0.4*(Availability/100) + 0.4*(1 - Degradation/100) + 0.2*exp(-0.01*(TTD+TTM+TTR))] * (1 - ResidualImpact)",
    "assessment_grade": "EXCELLENT"
  }
}
```

#### `GET /api/twin/topology`
Optimized payload for Three.js / WebGL 3D graph rendering.
- **Response:** `200 OK`
```json
{
  "nodes": [...],
  "links": [...],
  "slices": [...],
  "total_nodes": 28,
  "total_links": 33,
  "total_slices": 3,
  "state_version": 42
}
```

#### `GET /api/twin/components/{component_id}`
Returns individual node state.
- **Response:** `200 OK` (or `404 Not Found` if invalid id)

---

### 3.2 High-Resolution Telemetry

#### `GET /api/twin/telemetry`
- **Query Parameters:**
  - `component_id` (optional): Filter to node ID.
  - `metric_name` (optional): Filter metric (e.g. `ingress_bandwidth_anomaly`, `target_cpu_drift`).
  - `limit` (default: 30, max: 120): Number of temporal samples.
- **Response:** `200 OK`

---

### 3.3 Cyber Attack Scenarios

#### `GET /api/twin/scenarios`
Returns the catalog of 6 supported scenarios with descriptions, target defaults, and attack vectors.

#### `GET /api/twin/scenarios/active`
Returns `{ "active": boolean, "scenario": object | null, "lifecycle_state": string }`.

#### `POST /api/twin/scenarios/start`
- **Request Body:**
```json
{
  "scenario_type": "DDOS_TRAFFIC_FLOOD",
  "target_component": "upf-01",
  "entry_point": "ue-camera-01",
  "intensity": 3.5,
  "auto_progress": true
}
```
- **Response:** `200 OK`
```json
{
  "status": "STARTED",
  "scenario_id": "scen-ddos_traffic_flood-1732190000",
  "scenario_type": "DDOS_TRAFFIC_FLOOD",
  "target_component": "upf-01",
  "entry_point": "ue-camera-01",
  "propagation": {
    "scenario_id": "scen-ddos_traffic_flood-1732190000",
    "entry_point": "ue-camera-01",
    "target_component": "upf-01",
    "attack_path": ["ue-camera-01", "gnb-01", "upf-01"],
    "directly_targeted": ["upf-01", "ue-camera-01"],
    "indirectly_affected": ["gnb-01", "smf-01", "router-edge-01", "switch-core-01", "edge-node-01"],
    "potentially_affected": ["amf-01", "data-network-01"],
    "unaffected": ["udm-01", "ausf-01", "pcf-01", "nrf-01", "nssf-01", "nef-01", "udr-01"],
    "affected_ues": ["ue-camera-01", "ue-camera-02", "ue-camera-03", "ue-camera-04"],
    "affected_slices": ["sst-1-sd-010203"],
    "blast_radius_score": 18.2,
    "impact_explanation": "Direct attack path identified across 2 hops..."
  }
}
```

#### `POST /api/twin/scenarios/pause`
Pauses running attack progression.

#### `POST /api/twin/scenarios/resume`
Resumes paused attack progression.

#### `POST /api/twin/scenarios/step`
Manually steps scenario to the next lifecycle phase.

#### `POST /api/twin/scenarios/stop`
Terminates active simulation, setting state to `SIMULATION_STOPPED`.

#### `POST /api/twin/scenarios/reset`
Resets the digital twin state, telemetry, and health back to nominal baseline (`100%`).

---

### 3.4 Blast Radius & Attack Propagation

#### `GET /api/twin/propagation`
Returns current blast radius and propagation analysis for the active scenario.

#### `POST /api/twin/propagate`
Ad-hoc graph analysis without mutating state:
```json
{
  "entry_point": "ue-sensor-03",
  "target_component": "switch-core-01",
  "intensity": 2.5
}
```

---

### 3.5 Multi-Tier Mitigation & Recovery

#### `GET /api/twin/mitigation/actions`
Catalog of supported mitigation actions:
- `RATE_LIMITING`
- `TRAFFIC_RESTRICTION`
- `SUSPICIOUS_SOURCE_ISOLATION`
- `SESSION_TERMINATION`
- `COMPONENT_ISOLATION`
- `SLICE_PROTECTION`
- `POLICY_UPDATE`

#### `POST /api/twin/mitigation/apply`
- **Request Body:**
```json
{
  "action_type": "RATE_LIMITING",
  "target_component": "upf-01",
  "target_slice": "sst-1-sd-010203",
  "parameters": {
    "rate_ceiling_mbps": 50.0
  },
  "auto_verify": true
}
```
- **Response:** `200 OK`
```json
{
  "status": "APPLIED",
  "action_id": "mit-rate_limiting-1732190000",
  "action_type": "RATE_LIMITING",
  "target_component": "upf-01",
  "lifecycle_state": "MITIGATING"
}
```

#### `GET /api/twin/mitigation/status`
Returns active mitigations, recovery status (`VERIFYING` $\rightarrow$ `VERIFIED`), and historical actions.

---

### 3.6 What-If Digital Twin Sandbox

#### `GET /api/twin/what-if/templates`
Returns pre-configured hypothetical questions:
1. Complete UPF Outage & User Plane Loss
2. Perimeter Gateway Exfiltration Breach
3. 5x Volumetric Traffic Surge on eMBB
4. Impact of 60-Second Mitigation Delay
5. Mitigation Failure & Fallback Escalation

#### `POST /api/twin/what-if/simulate`
Simulates hypothetical experiment against an isolated clone without altering active twin state:
- **Request Body:**
```json
{
  "name": "Evaluation of UPF Crash",
  "hypothesis": "User plane collapses while control plane remains operational",
  "scenario_type": "UPF_OUTAGE",
  "target_component": "upf-01",
  "parameters": {
    "failover_available": false
  }
}
```
- **Response:** `200 OK`
```json
{
  "experiment_id": "exp-whatif-1732190000",
  "name": "Evaluation of UPF Crash",
  "baseline_metrics": {
    "overall_health": 100.0,
    "average_latency_ms": 2.14,
    "average_packet_loss_pct": 0.005,
    "service_availability_pct": 100.0,
    "throughput_mbps": 154.2
  },
  "predicted_metrics": {
    "overall_health": 45.0,
    "average_latency_ms": 47.14,
    "average_packet_loss_pct": 22.505,
    "service_availability_pct": 65.0,
    "throughput_mbps": 15.42
  },
  "impact_delta": {
    "health_drop": 55.0,
    "latency_increase_ms": 45.0,
    "packet_loss_increase_pct": 22.5,
    "availability_loss_pct": 35.0,
    "throughput_change_mbps": -138.78
  },
  "affected_components": ["upf-01", "gnb-01", "switch-core-01", "router-edge-01", "ue-camera-01"],
  "assumptions": ["3GPP Release 16 slicing isolation parameters hold for control plane."],
  "limitations": ["Simulation models logical network queue dynamics."],
  "recommendation": "Deploy redundant N9/N3 multi-homed UPF instance with automatic PFCP session transfer."
}
```

---

### 3.7 Quantitative Resilience & Audit Events

#### `GET /api/twin/resilience`
Returns quantitative resilience score and documented formula:
```json
{
  "time_to_detect_sec": 3.8,
  "time_to_mitigate_sec": 3.2,
  "time_to_recover_sec": 4.0,
  "service_availability_pct": 98.5,
  "network_degradation_pct": 5.2,
  "affected_components_count": 2,
  "affected_slices_count": 1,
  "residual_impact_pct": 0.0,
  "resilience_score": 93.68,
  "formula_documentation": "Resilience = 100 * [0.40 * (Availability / 100) + 0.40 * (1 - Degradation / 100) + 0.20 * exp(-0.01 * (TTD + TTM + TTR))] * (1 - ResidualImpact)",
  "assessment_grade": "EXCELLENT",
  "timestamp": "2026-11-21T14:00:00Z"
}
```

#### `GET /api/twin/events`
Returns immutable ledger of timestamped security and operational events.

---

## 4. WebSocket Real-Time Synchronization Protocol

- **Endpoint:** `ws://<host>:8000/api/twin/ws`
- **Connection Handshake:** Automatic upon WebSocket accept.

### 4.1 Server-to-Client Messages

#### 1. Initial State Snapshot (On Connect)
```json
{
  "event_type": "INITIAL_SNAPSHOT",
  "version": 42,
  "timestamp": "2026-11-21T14:00:00Z",
  "data": { ... full DigitalTwinStateSnapshot ... }
}
```

#### 2. Incremental Mutation Events
Whenever a component, connection, threat, mitigation, or lifecycle changes:
```json
{
  "version": 43,
  "event_type": "COMPONENT_UPDATED",
  "timestamp": "2026-11-21T14:00:02Z",
  "data": {
    "component_id": "upf-01",
    "updates": {
      "health_score": 35.0,
      "security_status": "ATTACKED",
      "packet_loss_pct": 18.5
    }
  }
}
```
Supported event types:
- `LIFECYCLE_STATE_CHANGED`: Data: `{"state": "THREAT_DETECTED"}`
- `COMPONENT_UPDATED`: Data: `{"component_id": "...", "updates": {...}}`
- `CONNECTION_UPDATED`: Data: `{"connection_id": "...", "updates": {...}}`
- `THREAT_DETECTED`: Data: `ThreatDetectionResult` object
- `MITIGATION_APPLIED`: Data: `MitigationActionRecord` object
- `PROPAGATION_UPDATED`: Data: `AttackPropagationResult` object
- `RESILIENCE_UPDATED`: Data: `ResilienceMetrics` object
- `STATE_RESET`: Data: `{"version": 1}`

### 4.2 Client-to-Server Commands
Clients may send JSON commands over the socket:
- Ping: `{"action": "PING"}` $\rightarrow$ Server responds: `{"event_type": "PONG", "timestamp": "..."}`
- Refresh Snapshot: `{"action": "GET_SNAPSHOT"}` $\rightarrow$ Server responds: `{"event_type": "SNAPSHOT_RESPONSE", "data": ...}`
