# CommShield AI — Digital Twin Architecture & Technical Specification

**Version:** 2.0.0  
**Authors:** Senior 5G Network Architect & Digital Twin Engineering Team  
**Scope:** Private 5G Core, Radio Access Network, Edge Infrastructure, and Security Engine  

---

## 1. Executive Architecture Summary

CommShield AI is an intelligent cybersecurity Digital Twin for Private 5G networks. It couples a 3GPP Release 16/17 compliant topological graph engine with multi-engine AI threat detection, causal graph propagation, closed-loop mitigation verification, and an isolated What-If experimentation sandbox.

```
                           +-------------------------------------+
                           |      Windows 3D Frontend / UI       |
                           |   (Three.js, WebGL, Real-Time HUD)  |
                           +-------------------------------------+
                                      ^                 |
                               REST   |                 | WebSocket
                               APIs   |                 | Stream (/ws)
                                      v                 v
+-----------------------------------------------------------------------------------+
|                        COMMShield Digital Twin Core (FastAPI)                     |
|                                                                                   |
|  +-----------------------------------------------------------------------------+  |
|  |                 Central Digital Twin State Engine (Thread-Safe)             |  |
|  |  * Single Source of Truth        * Versioned Snapshots (v1, v2, ...)        |  |
|  |  * Canonical 3GPP Topology Graph * Telemetry Ring Buffers (120 ticks)       |  |
|  |  * Real-Time Subscriber Pub/Sub  * Immutable Audit Event Ledger             |  |
|  +-----------------------------------------------------------------------------+  |
|         ^                          ^                            ^                 |
|         |                          |                            |                 |
|  +---------------+        +------------------+        +--------------------+      |
|  | Scenario &    |        | Blast Radius &   |        | Mitigation &       |      |
|  | Cyber Attack  |------->| Causal Attack    |------->| Verifiable         |      |
|  | Simulation    |        | Propagation      |        | Recovery Engine    |      |
|  +---------------+        +------------------+        +--------------------+      |
|         |                          |                            |                 |
|         v                          v                            v                 |
|  +---------------+        +------------------+        +--------------------+      |
|  | AI Threat     |        | Decoupled What-If|        | Quantitative       |      |
|  | Detection     |        | Simulation       |        | Resilience Scoring |      |
|  | (IF/AE/Fusion)|        | Sandbox (Cloned) |        | Intelligence       |      |
|  +---------------+        +------------------+        +--------------------+      |
+-----------------------------------------------------------------------------------+
```

---

## 2. Core Architectural Pillars

### Pillar 1: Single Source of Truth (`CentralDigitalTwinStateEngine`)
- **Authoritative Topology:** 28 network entities (RAN, 10 Core Control Plane NFs, UPF, MEC Edge Host, Perimeter Gateway, Core Switch, Security SOC, 13 UEs across 3 slices) and 33 separated User Plane & Control Plane links.
- **Thread Safety:** Protected by recursive reentrant locks (`threading.RLock`) preventing race conditions during concurrent WebSocket broadcasts, background simulation ticks, and operator REST commands.
- **Monotonic Versioning:** Every state mutation increments `state_version`.
- **Classification Transparency:** Strict provenance metadata (`LIVE`, `BACKEND`, `SIMULATED`, `DERIVED`, `PREDICTED`).

### Pillar 2: Graph-Based Causal Blast Radius Engine (`AttackPropagationEngine`)
Unlike simplistic simulations that indiscriminately mark nodes as red, CommShield employs **Breadth-First Search (BFS) shortest path and topological dependency traversal**:
1. **Directly Targeted:** Ingress entry point and primary target component.
2. **Indirectly Affected (1-Hop):** Immediately adjacent nodes and links carrying user-plane or signaling traffic to the target.
3. **Potentially Affected (2-Hop):** Secondary downstream nodes experiencing queue delay or connection saturation.
4. **Unaffected:** Strictly isolated control/user plane functions maintaining 100% nominal health and SLA guarantees.
5. **Containment Boundaries:** Autonomous boundary nodes (e.g. Edge Router, Core Switch, gNodeB) identified for packet filtering and policy enforcement.
6. **Quantitative Blast Radius Formula:**
   $$\text{BlastRadius} = \frac{N_{\text{direct}} \times 1.0 + N_{\text{indirect}} \times 0.5 + N_{\text{potential}} \times 0.2}{N_{\text{total}}} \times 100\%$$

### Pillar 3: Realistic Attack Simulation & Lifecycle State Machine (`ScenarioSimulationEngine`)
Governs 6 cyber attack scenarios with strict state machine transitions:

```
[ NORMAL ]
    |
    v (Operator starts attack scenario)
[ ATTACK_INITIATED ]
    |
    v (Ingress traffic spikes, entry link utilization surges)
[ SUSPICIOUS_ACTIVITY ]
    |
    v (Latency increases, buffer queue fills, CUSUM/ADWIN registers drift)
[ ANALYSING ]
    |
    v (Anomaly score crosses calibrated threshold: 99.6th percentile)
[ THREAT_DETECTED ]
    |
    +-----> [ Auto / Operator Applies Mitigation ]
    |
    v
[ MITIGATING ]
    |
    v (Enacting rate limiting, ACL filtering, or UE isolation)
[ VERIFYING_MITIGATION ]
    |
    v (Telemetry stabilizes: loss < 0.1%, latency normalized)
[ RECOVERED ]
```

### Pillar 4: Closed-Loop Verifiable Mitigation Engine (`MitigationEngine`)
Enacts 7 multi-tier mitigations:
- `RATE_LIMITING`: Dynamic token bucket throttling on affected GTP-U/SCTP tunnels.
- `TRAFFIC_RESTRICTION`: Layer-3/4 packet dropping matching attack vector signatures.
- `SUSPICIOUS_SOURCE_ISOLATION`: Radio access revocation and device quarantine.
- `SESSION_TERMINATION`: 3GPP N11 PDU session release via SMF.
- `COMPONENT_ISOLATION`: Redundant failover and subsystem isolation.
- `SLICE_PROTECTION`: PCF QoS AMBR ceiling re-enforcement.
- `POLICY_UPDATE`: Ingestion of Packet Detection Rules (PDR) and Forwarding Action Rules (FAR) into UPF.

### Pillar 5: Decoupled What-If Experimentation Sandbox (`WhatIfExperimentEngine`)
- Employs deep memory cloning (`deepcopy`) of the active network graph snapshot.
- Evaluates hypothetical disruptions (e.g. "What if UPF fails?", "What if mitigation is delayed by 60s?", "What if traffic surges 5x?") without perturbing the operational twin.
- Calculates delta metrics: health drops, packet loss increases, availability loss, and produces structured recommendations.

### Pillar 6: Quantitative Resilience Intelligence (`ResilienceIntelligenceEngine`)
Calculates resilience using the mathematically documented formula:
$$R = 100 \times \left( 0.40 \cdot \frac{\text{Availability}}{100} + 0.40 \cdot \left(1 - \frac{\text{Degradation}}{100}\right) + 0.20 \cdot e^{-0.01 \cdot (TTD + TTM + TTR)} \right) \cdot (1 - \text{ResidualImpact})$$

---

## 3. Real-Time Synchronization Architecture

The backend provides full duplex WebSocket streaming over `/api/twin/ws`:
- On connection, clients receive an `INITIAL_SNAPSHOT` containing all nodes, links, slices, active threats, and resilience metrics.
- As the simulation ticks or mitigations occur, lightweight delta events (`COMPONENT_UPDATED`, `CONNECTION_UPDATED`, `THREAT_DETECTED`, `RESILIENCE_UPDATED`) are broadcast to all connected 3D dashboards.
- Thread-safe queues bridge synchronous simulation workers with FastAPI's asynchronous event loop.
<!-- CommShield AI Core -->
