# CommShield AI — 5G Network Data Model Specification

**Specification Version:** 2.0.0  
**Compliance Standard:** 3GPP Release 16 & Release 17 Standalone (SA) Private 5G Architecture  
**Document Purpose:** Structural definition of all topological entities, interfaces, protocol bindings, slices, and telemetry units consumed by the CommShield Digital Twin Core and 3D Visualizer.

---

## 1. Network Topology Overview

The CommShield Private 5G network model represents an enterprise factory deployment comprising:
1. **Radio Access Network (RAN):** 1 high-power gNodeB serving sub-6 GHz (Band n78, 3.5 GHz).
2. **User Equipment (UE):** 13 provisioned devices spanning 3 distinct 3GPP network slices.
3. **5G Core Control Plane (5GC CP):** Service-Based Architecture (SBA) with 9 standard Network Functions (AMF, SMF, UDM, AUSF, PCF, NRF, NSSF, NEF, UDR).
4. **5G Core User Plane (5GC UP):** High-throughput User Plane Function (UPF) handling GTP-U encapsulation.
5. **Edge & Supporting Infrastructure:** 10GbE optical spine switch, perimeter edge gateway, MEC edge host, enterprise data network, and zero-trust security monitoring station.

```
+--------------------------------------------------------------------------------------------------+
|                                    COMMShield 5G Topology                                       |
|                                                                                                  |
|   [4x eMBB Cameras]   ---\                                                                       |
|   [3x URLLC AGVs]     ---- (Uu) ---> [gNodeB-01] ======= (N3 GTP-U) ========> [UPF-01]           |
|   [6x mMTC Sensors]   ---/               |                                        ||             |
|                                         (N2)                                    (N6/N9)          |
|                                          v                                        ||             |
|                                      [AMF-01] <== (N11) ==> [SMF-01]             // \\           |
|                                       ||  ||                 ||                 //   \\          |
|                                  (N12)//  \\(N15)        (N7)//               [MEC]  [Edge GW]   |
|                                      v      v                v                          ||       |
|                                  [AUSF]   [PCF] <----------> |                       [DataNet]   |
|                                      ^      ^                                                    |
|                                  (N13)\    /(Nudr)                                               |
|                                        v  v                                                      |
|                                      [UDM/UDR]                                                   |
+--------------------------------------------------------------------------------------------------+
```

---

## 2. 3GPP Network Functions & Components

### 2.1 Radio Access Network (RAN)
| Component ID | Name | Role | Specs / Freq | Nominal Latency | Capacity | Slices Served |
|---|---|---|---|---|---|---|
| `gnb-01` | gNodeB-Cell-01 | Radio Access Point | 3.5 GHz (Band n78), 30 dBm Tx | 1.8 ms | 10 Gbps backhaul | ALL |

### 2.2 5G Core Control Plane (5GC CP)
All control-plane SBI interfaces communicate over HTTP/2 with JSON payloads according to 3GPP TS 29.500:
| Component ID | Name | Role | Primary 3GPP Interfaces | CPU Nominal | Mem Nominal | Latency |
|---|---|---|---|---|---|---|
| `amf-01` | AMF-01 | Access & Mobility Management | N2 (SCTP/NGAP), N11, N12, N15, N22, Nnrf | 18.0% | 32.0% | 1.2 ms |
| `smf-01` | SMF-01 | Session Management Function | N4 (PFCP UDP 8805), N11, N7, N10, Nnrf | 21.5% | 38.0% | 1.4 ms |
| `udm-01` | UDM-01 | Unified Data Management | N10, N13, Nudr, Nnrf | 14.0% | 28.0% | 1.1 ms |
| `ausf-01` | AUSF-01 | Authentication Server Function | N12 (5G-AKA), N13, Nnrf | 15.2% | 26.5% | 1.3 ms |
| `pcf-01` | PCF-01 | Policy Control Function | N7 (SM Policy), N15 (AM Policy), Nudr | 16.0% | 30.0% | 1.2 ms |
| `nrf-01` | NRF-01 | Network Repository Function | Nnrf Service Discovery | 12.0% | 24.0% | 0.8 ms |
| `nssf-01` | NSSF-01 | Network Slice Selection Function| N22 Slice Selection | 11.5% | 22.0% | 0.9 ms |
| `nef-01` | NEF-01 | Network Exposure Function | Nnef API Gateway | 14.5% | 27.0% | 1.5 ms |
| `udr-01` | UDR-01 | Unified Data Repository | Nudr Database Storage | 17.0% | 35.0% | 1.0 ms |

### 2.3 5G Core User Plane (5GC UP)
| Component ID | Name | Role | Protocols / Interfaces | Nominal Throughput | Latency | Packet Loss |
|---|---|---|---|---|---|---|
| `upf-01` | UPF-01 | User Plane Function | N3 (GTP-U UDP 2152), N4 (PFCP), N6, N9 | 75.5 Mbps (10 Gbps max) | 2.1 ms | 0.01% |

### 2.4 Supporting & Security Infrastructure
| Component ID | Name | Role | Connected Links | Hardware Spec |
|---|---|---|---|---|
| `switch-core-01` | SpineSwitch-01 | Core Fabric Switch | gnb-01, upf-01, router-edge-01 | 10GbE Optical Ethernet |
| `router-edge-01` | EdgeRouter-01 | Perimeter Boundary Gateway | upf-01, switch-core-01, data-network-01 | Stateful SPI & BGP Peering |
| `edge-node-01` | MEC-Host-01 | Multi-Access Edge Computing | router-edge-01, upf-01 (via N9) | Intel Xeon, NVMe cache |
| `data-network-01`| Enterprise-DN | Corporate Intranet / Cloud | router-edge-01 | 10 Gbps Enterprise Uplink |
| `sec-monitor-01` | CommShield-SOC-01 | Zero-Trust Telemetry Collector| amf-01, smf-01, upf-01, router-edge-01 | Real-time gRPC telemetry bus |

---

## 3. Network Slices (S-NSSAI)

The network partitions radio, transmission, and processing resources into 3 standardized slices:

### 3.1 eMBB — Enhanced Mobile Broadband (`sst-1-sd-010203`)
- **SST:** 1 | **SD:** `010203`
- **Application:** 4K video surveillance feeds and operator AR headsets.
- **Bandwidth Quota:** 500.0 Mbps allocated (nominal usage: 45.2 Mbps).
- **SLA Max Latency:** 20.0 ms (nominal: 8.5 ms).
- **Target Packet Loss:** $\le 0.1\%$ (nominal: 0.01%).
- **Isolation Mechanism:** Dedicated UPF PDU sessions and VLAN 100 encapsulation.

### 3.2 URLLC — Ultra-Reliable Low-Latency Communication (`sst-2-sd-020304`)
- **SST:** 2 | **SD:** `020304`
- **Application:** Autonomous Guided Vehicles (AGVs) and synchronized robotic palletizers.
- **Bandwidth Quota:** 200.0 Mbps allocated (nominal usage: 24.0 Mbps).
- **SLA Max Latency:** 5.0 ms (nominal: 1.8 ms).
- **Target Packet Loss:** $\le 0.001\%$ (nominal: 0.0001%).
- **Isolation Mechanism:** Priority preemption scheduling on gNB and VLAN 200 QoS reservation.

### 3.3 mMTC — Massive Machine-Type Communication (`sst-3-sd-030405`)
- **SST:** 3 | **SD:** `030405`
- **Application:** High-density telemetry mesh across factory vibration, temperature, and environmental sensors.
- **Bandwidth Quota:** 100.0 Mbps allocated (nominal usage: 8.5 Mbps).
- **SLA Max Latency:** 50.0 ms (nominal: 14.2 ms).
- **Target Packet Loss:** $\le 1.0\%$ (nominal: 0.05%).
- **Isolation Mechanism:** Rate-limited ingress policing and VLAN 300 encapsulation.

---

## 4. User Equipment (UE) Inventory

| UE ID | Device Name | Device Type | Slice ID | Throughput | Nominal Latency | 3D Coords (X, Y, Z) |
|---|---|---|---|---|---|---|
| `ue-camera-01` | Camera-North-Gate | Camera | `sst-1-sd-010203` | 11.2 Mbps | 5.5 ms | (-12.0, 4.0, 0.0) |
| `ue-camera-02` | Camera-Loading-Dock | Camera | `sst-1-sd-010203` | 11.5 Mbps | 5.8 ms | (-12.0, 2.0, 0.0) |
| `ue-camera-03` | Camera-Assembly-Line | Camera | `sst-1-sd-010203` | 11.0 Mbps | 5.2 ms | (-12.0, -2.0, 0.0) |
| `ue-camera-04` | Camera-Robotics-Bay | Camera | `sst-1-sd-010203` | 11.5 Mbps | 5.9 ms | (-12.0, -4.0, 0.0) |
| `ue-agv-01` | AGV-Transporter-Alpha | AGV | `sst-2-sd-020304` | 8.0 Mbps | 1.8 ms | (-8.0, 3.0, 0.0) |
| `ue-agv-02` | AGV-Transporter-Bravo | AGV | `sst-2-sd-020304` | 8.0 Mbps | 1.7 ms | (-8.0, 0.0, 0.0) |
| `ue-agv-03` | AGV-Palletizer-Gamma | AGV | `sst-2-sd-020304` | 8.0 Mbps | 1.9 ms | (-8.0, -3.0, 0.0) |
| `ue-sensor-01` | Vibration-Motor-01 | Sensor | `sst-3-sd-030405` | 1.4 Mbps | 12.5 ms | (-5.0, 5.0, 0.0) |
| `ue-sensor-02` | Vibration-Motor-02 | Sensor | `sst-3-sd-030405` | 1.4 Mbps | 13.0 ms | (-5.0, 3.0, 0.0) |
| `ue-sensor-03` | Temp-Furnace-01 | Sensor | `sst-3-sd-030405` | 1.4 Mbps | 14.1 ms | (-5.0, 1.0, 0.0) |
| `ue-sensor-04` | Pressure-Valve-01 | Sensor | `sst-3-sd-030405` | 1.4 Mbps | 12.8 ms | (-5.0, -1.0, 0.0) |
| `ue-sensor-05` | AirQuality-Hall-A | Sensor | `sst-3-sd-030405` | 1.5 Mbps | 14.5 ms | (-5.0, -3.0, 0.0) |
| `ue-sensor-06` | FlowMeter-Chiller-01 | Sensor | `sst-3-sd-030405` | 1.4 Mbps | 13.2 ms | (-5.0, -5.0, 0.0) |

---

## 5. Standardized 3GPP Reference Point Connections

| Link ID | Source | Destination | Plane | 3GPP Reference Interface | Capacity |
|---|---|---|---|---|---|
| `conn-n2-gnb-amf` | gnb-01 | amf-01 | CONTROL_PLANE | N2 (SCTP / NGAP TS 38.413) | 1,000 Mbps |
| `conn-n11-amf-smf`| amf-01 | smf-01 | CONTROL_PLANE | N11 (HTTP/2 SBI TS 29.502) | 2,000 Mbps |
| `conn-n4-smf-upf` | smf-01 | upf-01 | CONTROL_PLANE | N4 (PFCP UDP 8805 TS 29.244) | 1,000 Mbps |
| `conn-n12-amf-ausf`| amf-01 | ausf-01 | CONTROL_PLANE | N12 (HTTP/2 SBI TS 29.509) | 1,000 Mbps |
| `conn-n13-ausf-udm`| ausf-01 | udm-01 | CONTROL_PLANE | N13 (HTTP/2 SBI TS 29.503) | 1,000 Mbps |
| `conn-n10-smf-udm` | smf-01 | udm-01 | CONTROL_PLANE | N10 (HTTP/2 SBI TS 29.503) | 1,000 Mbps |
| `conn-n7-smf-pcf`  | smf-01 | pcf-01 | CONTROL_PLANE | N7 (HTTP/2 SBI TS 29.512) | 1,000 Mbps |
| `conn-n15-amf-pcf` | amf-01 | pcf-01 | CONTROL_PLANE | N15 (HTTP/2 SBI TS 29.507) | 1,000 Mbps |
| `conn-n22-amf-nssf`| amf-01 | nssf-01 | CONTROL_PLANE | N22 (HTTP/2 SBI TS 29.531) | 1,000 Mbps |
| `conn-nrf-amf`     | amf-01 | nrf-01 | CONTROL_PLANE | Nnrf (HTTP/2 SBI TS 29.510)| 1,000 Mbps |
| `conn-nrf-smf`     | smf-01 | nrf-01 | CONTROL_PLANE | Nnrf (HTTP/2 SBI TS 29.510)| 1,000 Mbps |
| `conn-udr-udm`     | udm-01 | udr-01 | CONTROL_PLANE | Nudr (HTTP/2 DB TS 29.504) | 2,000 Mbps |
| `conn-udr-pcf`     | pcf-01 | udr-01 | CONTROL_PLANE | Nudr (HTTP/2 DB TS 29.504) | 2,000 Mbps |
| `conn-nef-amf`     | nef-01 | amf-01 | CONTROL_PLANE | Nnef (HTTP/2 API TS 29.522)| 1,000 Mbps |
| `conn-sec-mon`     | upf-01 | sec-monitor-01| CONTROL_PLANE | Telemetry Stream (gRPC) | 5,000 Mbps |
| `conn-n3-gnb-upf`  | gnb-01 | upf-01 | USER_PLANE | N3 (GTP-U UDP 2152 TS 29.281) | 10,000 Mbps |
| `conn-n6-upf-router`| upf-01| router-edge-01| USER_PLANE | N6 (IPv4/IPv6 Routed) | 10,000 Mbps |
| `conn-n9-upf-mec`   | upf-01| edge-node-01  | USER_PLANE | N9 (Local Breakout GTP-U) | 10,000 Mbps |
| `conn-router-dn`   | router-edge-01| data-network-01| USER_PLANE | Enterprise Transit (BGP/IP) | 10,000 Mbps |
| `conn-switch-fabric`| gnb-01 | switch-core-01 | USER_PLANE | Optical Ethernet (10GbE) | 10,000 Mbps |
| `conn-switch-upf`  | switch-core-01| upf-01 | USER_PLANE | Optical Ethernet (10GbE) | 10,000 Mbps |
| `conn-uu-cam-01..04`| UEs | gnb-01 | USER_PLANE | 3GPP 5G-NR Uu | 100 Mbps ea |
| `conn-uu-agv-01..03`| UEs | gnb-01 | USER_PLANE | 3GPP 5G-NR Uu | 100 Mbps ea |
| `conn-uu-sns-01..06`| UEs | gnb-01 | USER_PLANE | 3GPP 5G-NR Uu | 50 Mbps ea |
<!-- CommShield AI Core -->
