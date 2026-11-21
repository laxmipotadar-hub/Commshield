# CommShield 3D Digital Twin - API Gaps & Missing Endpoints

The frontend requires the following backend endpoints to support complete real-time interactive 3D digital twin operations. In compliance with project rules, the UI displays "Backend not providing this yet" for these features and does not invent or fake responses.

---

### 1. Dynamic Component Telemetry
- **Desired Route**: `GET /api/v1/digital-twin/components/{component_id}/telemetry`
- **Purpose**: Fetch live hardware/system metrics (CPU utilization, memory usage, instantaneous packet loss, active sessions) for network functions and UEs.
- **Request Payload**: None (Query params: `window_sec=60`)
- **Desired Response Payload**:
```json
{
  "component_id": "upf_01",
  "timestamp": "2026-11-21T18:00:00Z",
  "cpu_percent": 34.2,
  "memory_percent": 48.6,
  "throughput_mbps": 412.5,
  "latency_ms": 1.45,
  "packet_loss_rate": 0.0001,
  "active_sessions": 284,
  "status": "healthy"
}
```

---

### 2. Attack Injection Command API
- **Desired Route**: `POST /api/v1/digital-twin/attack`
- **Purpose**: Dynamically trigger or stop targeted attacks (e.g. rogue burst, slow ramp, DDoS, unauthorized onboarding) against specific network functions or slice IDs.
- **Request Payload**:
```json
{
  "attack_type": "rogue_burst",
  "target_slice": "sst-3-sd-030405",
  "target_component": "upf_01",
  "intensity": 2.5,
  "duration_sec": 120
}
```
- **Desired Response Payload**:
```json
{
  "attack_id": "atk_20261121_001",
  "status": "ACTIVE",
  "started_at": "2026-11-21T18:00:05Z",
  "blast_radius": {
    "entry_point": "sst-3-sd-030405",
    "affected_nodes": ["upf_01", "gnb_01"],
    "affected_slices": ["sst-3-sd-030405"]
  }
}
```

---

### 3. Automated Mitigation Trigger
- **Desired Route**: `POST /api/v1/digital-twin/mitigate`
- **Purpose**: Issue automated or operator-confirmed containment actions (isolate UE, quarantine slice, rate-limit UPF, rotate key).
- **Request Payload**:
```json
{
  "incident_id": "INC-2026-0042",
  "action": "quarantine_slice",
  "target_slice": "sst-3-sd-030405",
  "enforce_zero_trust": true
}
```
- **Desired Response Payload**:
```json
{
  "action_id": "act_9941",
  "lifecycle_state": "IN_PROGRESS",
  "target": "sst-3-sd-030405",
  "verified_recovery": false,
  "timestamp": "2026-11-21T18:00:15Z"
}
```

---

### 4. What-If Scenario Prediction Engine
- **Desired Route**: `POST /api/v1/digital-twin/what-if`
- **Purpose**: Run isolated hypothetical failure/attack simulation without mutating active digital twin state.
- **Request Payload**:
```json
{
  "scenario_type": "upf_failure",
  "target_slice": "sst-1-sd-010203",
  "parameters": {
    "traffic_multiplier": 3.0,
    "dropped_packets_rate": 0.15
  }
}
```
- **Desired Response Payload**:
```json
{
  "experiment_id": "hypo_882",
  "predicted_availability": 82.4,
  "predicted_latency_ms": 14.8,
  "predicted_loss_rate": 0.12,
  "affected_components": ["upf_01", "cam_01", "cam_02"],
  "recovery_recommendation": "failover_secondary_upf",
  "simulation_tag": "PREDICTED"
}
```
