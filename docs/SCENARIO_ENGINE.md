# CommShield AI — Scenario Engine & Attack Simulation Specification

**Specification Version:** 2.0.0  
**Authors:** Senior Cybersecurity Simulation Engineer & Private 5G Network Architect  
**Scope:** Cyber Attack Modeling, Blast Radius Propagation, AI Detection, and Multi-Tier Mitigation  

---

## 1. Overview of the Scenario Engine

The CommShield Scenario Engine (`backend/app/twin/scenarios.py`) simulates realistic, multi-stage cyber attacks against Private 5G networks. Unlike naive simulations that introduce random metric jitter, every attack in CommShield models:
1. **Specific 3GPP Protocols & Interfaces:** N2 (NGAP), N3 (GTP-U), N4 (PFCP), N6 (IP), N12 (5G-AKA), and Uu radio links.
2. **Causal Blast Radius:** Multi-hop topological BFS traversal that distinguishes directly targeted entities from indirectly affected dependencies and completely unaffected network functions.
3. **AI Threat Detection Evidence:** Integrates calibrated Isolation Forest, Deep Autoencoders, ADWIN drift monitoring, and CUSUM accumulators to generate explainable detection verdicts.
4. **Verifiable Closed-Loop Mitigation:** Enacts operator or autonomous mitigation policies and monitors telemetry recovery back to nominal baseline.

---

## 2. The 6 Cyber Attack Scenarios

### Scenario 1: DDoS Volumetric Traffic Flood (`DDOS_TRAFFIC_FLOOD`)
- **Category:** Distributed Denial of Service (User Plane)
- **Primary Target:** `upf-01` (User Plane Function)
- **Ingress Entry Point:** `ue-camera-01` (via `gnb-01`)
- **Affected Network Slice:** `sst-1-sd-010203` (eMBB)
- **Attack Mechanism:** Compromised high-resolution cameras generate high-volume UDP packet floods encapsulated inside GTP-U tunnels over the N3 interface, overwhelming UPF ingress queue buffers and saturating the N6 link to the edge router.
- **Degraded Metrics:**
  - `upf-01` CPU: climbs to 94.5%
  - N3 GTP-U Latency: surges from 2.1 ms to 68.0 ms
  - Packet Loss: escalates to 18.5%
  - eMBB Slice Throughput: saturates at 820 Mbps (exceeding 500 Mbps quota)
- **Unaffected Components:** 5G Core control plane functions (`amf-01`, `udm-01`, `ausf-01`, `pcf-01`) and URLLC mission-critical AGVs remain isolated and operational.
- **AI Detection Method:** `AI_ISOLATION_FOREST` & `AI_FUSION` (Confidence: 0.96, Severity: `CRITICAL`).
- **Optimal Mitigation:** `RATE_LIMITING` on N3 ingress + `POLICY_UPDATE` (dynamic UPF PDR rule to drop malicious UDP port flows).

---

### Scenario 2: Signaling Storm & Authentication Anomaly (`AUTH_ANOMALY`)
- **Category:** Control Plane Exhaustion & Identity Replay
- **Primary Target:** `amf-01` and `ausf-01`
- **Ingress Entry Point:** `ue-sensor-01` (via `gnb-01`)
- **Affected Network Slice:** `sst-3-sd-030405` (mMTC)
- **Attack Mechanism:** Rogue IoT devices generate rapid bursts of spoofed 5G-AKA authentication requests and registration updates over N2 (NGAP), flooding the AMF and forcing continuous cryptographic verification cycles on AUSF and UDM over N12/N13.
- **Degraded Metrics:**
  - `amf-01` CPU: climbs to 89.0%
  - `ausf-01` CPU: climbs to 84.0%
  - N2 Signaling Latency: jumps to 42.0 ms
  - Signaling Request Rate: peaks at 1,450 requests/sec
- **Unaffected Components:** User-plane throughput on UPF is completely unaffected (latency < 2.5 ms, packet loss 0%).
- **AI Detection Method:** `RULE_BASED_ADWIN` & `CUSUM_ACCUMULATOR` (Confidence: 0.91, Severity: `HIGH`).
- **Optimal Mitigation:** `RATE_LIMITING` on N2 NGAP connection + `SUSPICIOUS_SOURCE_ISOLATION` (quarantine rogue sensor UE).

---

### Scenario 3: Network Slice Resource Abuse (`SLICE_RESOURCE_ABUSE`)
- **Category:** Multi-Tenant SLA & Bandwidth Quota Violation
- **Primary Target:** `sst-1-sd-010203` (eMBB Slice)
- **Ingress Entry Point:** `ue-camera-02`
- **Affected Network Slice:** `sst-1-sd-010203` (eMBB)
- **Attack Mechanism:** Unauthorized high-bitrate raw video streaming surges through eMBB, exceeding the 500 Mbps allocated quota and causing packet buffer queue bloat on the shared gNodeB scheduler.
- **Degraded Metrics:**
  - eMBB Bandwidth: peaks at 640.0 Mbps
  - eMBB Latency: rises to 36.0 ms
  - eMBB Packet Loss: rises to 11.2%
- **Unaffected Components:** 3GPP slicing isolation holds — URLLC AGVs (`sst-2-sd-020304`) and mMTC sensors (`sst-3-sd-030405`) maintain strict SLA latency (< 2.0 ms) and zero packet loss.
- **AI Detection Method:** `AI_AUTOENCODER` (Reconstruction error anomaly, Confidence: 0.92, Severity: `MEDIUM`).
- **Optimal Mitigation:** `SLICE_PROTECTION` (enforce strict PCF AMBR bandwidth quota clamping).

---

### Scenario 4: UPF Core Processing Exhaustion (`UPF_OVERLOAD`)
- **Category:** Core Infrastructure Exhaustion
- **Primary Target:** `upf-01`
- **Ingress Entry Point:** `gnb-01`
- **Affected Network Slice:** `ALL`
- **Attack Mechanism:** High-packet-rate micro-bursts exhaust the UPF hardware packet processing queues and PFCP session memory tables, degrading packet forwarding across all slices simultaneously.
- **Degraded Metrics:**
  - `upf-01` CPU: reaches 98.5%
  - Global User-Plane Latency: jumps to 78.0 ms
  - Packet Loss: escalates to 24.5%
  - Links `conn-n3-gnb-upf` and `conn-n6-upf-router` marked `CONGESTED`
- **AI Detection Method:** `AI_FUSION` (Consensus between Isolation Forest and Autoencoder, Confidence: 0.98, Severity: `CRITICAL`).
- **Optimal Mitigation:** `TRAFFIC_RESTRICTION` + `SESSION_TERMINATION` on anomalous PDU sessions via SMF.

---

### Scenario 5: Suspicious UE Lateral Reconnaissance (`SUSPICIOUS_UE_ACTIVITY`)
- **Category:** Insider Threat & Lateral Movement
- **Primary Target:** `switch-core-01`
- **Ingress Entry Point:** `ue-sensor-03`
- **Affected Network Slice:** `sst-3-sd-030405` (mMTC)
- **Attack Mechanism:** A compromised industrial temperature sensor executes unauthorized TCP SYN port sweeps and ARP scans across the internal private 5G core subnet to map management interfaces and open ports.
- **Degraded Metrics:**
  - `ue-sensor-03` Traffic Rate: surges 10x
  - Abnormal SYN/RST Flag Ratio detected by zero-trust monitor
  - `conn-uu-sns-03` marked `SUSPICIOUS_TRAFFIC`
- **AI Detection Method:** `AI_ISOLATION_FOREST` (Feature flags: `syn_flag_ratio`, `unique_dst_ports`, Confidence: 0.88, Severity: `HIGH`).
- **Optimal Mitigation:** `SUSPICIOUS_SOURCE_ISOLATION` (revoke 5G-NR Uu radio connection and isolate `ue-sensor-03`).

---

### Scenario 6: Edge Gateway Intrusion & Exfiltration (`GATEWAY_COMPROMISE`)
- **Category:** Perimeter Breach & Unauthorized Data Exfiltration
- **Primary Target:** `router-edge-01`
- **Ingress Entry Point:** `router-edge-01` / `data-network-01`
- **Affected Network Slice:** `ALL`
- **Attack Mechanism:** An external attacker exploits an unpatched ingress vulnerability on the perimeter boundary router, establishing an unauthorized encrypted tunnel to exfiltrate cached factory data from the MEC edge host.
- **Degraded Metrics:**
  - `router-edge-01` CPU: 86.0%, Security Status: `COMPROMISED`
  - Egress Exfiltration Bandwidth: 320.0 Mbps
  - N6 Interface Latency: 52.0 ms
- **AI Detection Method:** `AI_FUSION` (Confidence: 0.95, Severity: `CRITICAL`).
- **Optimal Mitigation:** `COMPONENT_ISOLATION` (failover to secondary gateway) + `POLICY_UPDATE` (stateful firewall egress block).

---

## 3. Attack Progression Lifecycle State Machine

The scenario engine advances through 8 discrete lifecycle states:

```
[ NORMAL ]
    |
    v (start_scenario called)
[ ATTACK_INITIATED ]  ---> Ingress connection utilization begins spiking
    |
    v (Step 1)
[ SUSPICIOUS_ACTIVITY ] -> Telemetry registers localized latency/throughput elevation
    |
    v (Step 2)
[ ANALYSING ] ---------> Anomaly accumulators (CUSUM, ADWIN) indicate persistent drift
    |
    v (Step 3)
[ THREAT_DETECTED ] ----> AI engine triggers alarm, flags component as ATTACKED
    |
    v (Operator or Auto Mitigation applied)
[ MITIGATING ] ---------> Mitigation rules injected (rate limit, ACL, isolation)
    |
    v
[ VERIFYING_MITIGATION ] -> Closed-loop feedback tests metric recovery
    |
    v
[ RECOVERED ] ----------> Latency < 5ms, loss < 0.1%, health >= 95%, threats cleared
```

---

## 4. Blast Radius & Causal Propagation Algorithm

The blast radius calculation uses deterministic graph traversal:

```python
# 1. Build adjacency list of all 3GPP components and connections
adj = {cid: [] for cid in components}
for conn in connections.values():
    adj[conn.source].append(conn.destination)
    adj[conn.destination].append(conn.source)

# 2. Find shortest attack path (BFS)
attack_path = bfs_shortest_path(adj, entry_point, target_component)

# 3. Classify components causally:
# - Directly targeted: target_component and entry_point
# - Indirectly affected (1-hop): immediate neighbors of target
# - Potentially affected (2-hop): neighbors of 1-hop nodes
# - Unaffected: all remaining network functions

# 4. Compute Blast Radius Score:
blast_radius_score = 100.0 * (
    len(directly_targeted) * 1.0 +
    len(indirectly_affected) * 0.5 +
    len(potentially_affected) * 0.2
) / max(1, len(components))
```

---

## 5. Mitigation Verification & Recovery Metrics

When a mitigation is applied via `/api/twin/mitigation/apply`:
1. **Immediate Action:** The target node or interface undergoes immediate policy reconfiguration (e.g. throughput clamped, rogue UE isolated).
2. **Verification Stage (`VERIFYING_MITIGATION`):** Telemetry is evaluated for 2 consecutive observation windows:
   - Target packet loss must drop below $0.1\%$.
   - Target latency must drop below $5.0$ ms.
   - Core CPU utilization must normalize below $35.0\%$.
3. **Recovery Completion (`RECOVERED`):**
   - Active threats are marked `is_mitigated = True`.
   - Node security status is reset to `SECURE` (or `QUARANTINED` if isolated).
   - Resilience Intelligence recomputes the global resilience score and issues a verifiable recovery event in the immutable ledger.
<!-- CommShield AI Core -->
