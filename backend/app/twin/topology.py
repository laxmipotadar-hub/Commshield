"""Canonical Private 5G Network Topology Factory.

Builds the complete 3GPP Release 16/17 private 5G network model:
- Radio Access Network (gNodeB, UEs across 3 slices)
- 5G Core Control Plane (AMF, SMF, UDM, AUSF, PCF, NRF, NSSF, NEF, UDR)
- 5G Core User Plane (UPF)
- Supporting Infrastructure (Core Switch, Edge Router, MEC Node, Data Network, Security Monitor)
- Network Slices (eMBB, URLLC, mMTC)
- Explicitly separated Control-Plane and User-Plane connections with 3GPP interface references.
"""

from typing import Dict, List, Tuple
from .models import (
    ConnectionType,
    ConnectionStatus,
    DataClassification,
    NetworkComponent,
    NetworkConnection,
    NetworkSliceInfo,
    OperationalStatus,
    SecurityStatus,
)


def build_canonical_slices() -> Dict[str, NetworkSliceInfo]:
    """Construct standard 3GPP S-NSSAI network slices."""
    return {
        "sst-1-sd-010203": NetworkSliceInfo(
            slice_id="sst-1-sd-010203",
            name="eMBB High-Throughput (4K Surveillance & AR)",
            sst=1,
            sd="010203",
            description="Enhanced Mobile Broadband allocated for high-bitrate video surveillance and remote inspection.",
            allocated_bandwidth_mbps=500.0,
            current_throughput_mbps=45.2,
            max_latency_ms=20.0,
            current_latency_ms=8.5,
            target_packet_loss_pct=0.1,
            current_packet_loss_pct=0.01,
            active_ues_count=4,
            security_state="NOMINAL",
            isolation_guarantee="Dedicated UPF Session & VLAN 100",
        ),
        "sst-2-sd-020304": NetworkSliceInfo(
            slice_id="sst-2-sd-020304",
            name="URLLC Ultra-Reliable Low-Latency (Robotics & AGVs)",
            sst=2,
            sd="020304",
            description="Mission-critical control slice for autonomous vehicles and synchronized shop-floor robotics.",
            allocated_bandwidth_mbps=200.0,
            current_throughput_mbps=24.0,
            max_latency_ms=5.0,
            current_latency_ms=1.8,
            target_packet_loss_pct=0.001,
            current_packet_loss_pct=0.0001,
            active_ues_count=3,
            security_state="NOMINAL",
            isolation_guarantee="Priority Preemption & VLAN 200",
        ),
        "sst-3-sd-030405": NetworkSliceInfo(
            slice_id="sst-3-sd-030405",
            name="mMTC Massive IoT (Industrial Telemetry Mesh)",
            sst=3,
            sd="030405",
            description="High-density, low-power telemetry reporting across factory vibration, temperature, and environmental sensors.",
            allocated_bandwidth_mbps=100.0,
            current_throughput_mbps=8.5,
            max_latency_ms=50.0,
            current_latency_ms=14.2,
            target_packet_loss_pct=1.0,
            current_packet_loss_pct=0.05,
            active_ues_count=6,
            security_state="NOMINAL",
            isolation_guarantee="Rate-Limited Ingress & VLAN 300",
        ),
    }


def build_canonical_components() -> Dict[str, NetworkComponent]:
    """Construct all logical 5G network components with initial healthy state."""
    comps: Dict[str, NetworkComponent] = {}

    # 1. Radio Access Network (gNodeB)
    comps["gnb-01"] = NetworkComponent(
        id="gnb-01",
        name="gNodeB-Cell-01",
        component_type="gNodeB",
        network_role="Radio Access Network",
        operational_status=OperationalStatus.ACTIVE,
        health_score=100.0,
        cpu_utilization_pct=22.4,
        memory_utilization_pct=34.1,
        traffic_volume_mbps=77.7,
        latency_ms=1.8,
        packet_loss_pct=0.01,
        connected_components=["amf-01", "upf-01", "switch-core-01"],
        network_slice="ALL",
        security_status=SecurityStatus.SECURE,
        provenance=DataClassification.SIMULATED,
        coordinates_3d={"x": 0.0, "y": 0.0, "z": 0.0},
        metadata={"carrier_freq": "3.5GHz N78", "tx_power_dbm": 30, "connected_ues": 13},
    )

    # 2. 5G Core Control Plane Functions
    core_cps = [
        ("amf-01", "AMF-01", "AMF", "Access & Mobility Management", 18.0, 32.0, 1.2, ["gnb-01", "smf-01", "ausf-01", "pcf-01", "nssf-01", "nrf-01"]),
        ("smf-01", "SMF-01", "SMF", "Session Management Function", 21.5, 38.0, 1.4, ["amf-01", "upf-01", "pcf-01", "udm-01", "nrf-01"]),
        ("udm-01", "UDM-01", "UDM", "Unified Data Management", 14.0, 28.0, 1.1, ["ausf-01", "smf-01", "udr-01", "nrf-01"]),
        ("ausf-01", "AUSF-01", "AUSF", "Authentication Server Function", 15.2, 26.5, 1.3, ["amf-01", "udm-01", "nrf-01"]),
        ("pcf-01", "PCF-01", "PCF", "Policy Control Function", 16.0, 30.0, 1.2, ["amf-01", "smf-01", "udr-01", "nrf-01"]),
        ("nrf-01", "NRF-01", "NRF", "Network Repository Function", 12.0, 24.0, 0.8, ["amf-01", "smf-01", "udm-01", "ausf-01", "pcf-01"]),
        ("nssf-01", "NSSF-01", "NSSF", "Network Slice Selection Function", 11.5, 22.0, 0.9, ["amf-01", "nrf-01"]),
        ("nef-01", "NEF-01", "NEF", "Network Exposure Function", 14.5, 27.0, 1.5, ["amf-01", "smf-01", "udr-01"]),
        ("udr-01", "UDR-01", "UDR", "Unified Data Repository", 17.0, 35.0, 1.0, ["udm-01", "pcf-01", "nef-01"]),
    ]

    for cid, cname, ctype, crole, cpu, mem, lat, conn in core_cps:
        comps[cid] = NetworkComponent(
            id=cid,
            name=cname,
            component_type=ctype,
            network_role=crole,
            operational_status=OperationalStatus.ACTIVE,
            health_score=100.0,
            cpu_utilization_pct=cpu,
            memory_utilization_pct=mem,
            traffic_volume_mbps=5.0,
            latency_ms=lat,
            packet_loss_pct=0.0,
            connected_components=conn,
            network_slice="ALL",
            security_status=SecurityStatus.SECURE,
            provenance=DataClassification.SIMULATED,
            coordinates_3d={"x": 5.0, "y": 2.0, "z": 0.0},
            metadata={"sbi_binding": "HTTP/2", "3gpp_spec": "TS 29.500"},
        )

    # 3. 5G Core User Plane Function (UPF)
    comps["upf-01"] = NetworkComponent(
        id="upf-01",
        name="UPF-01",
        component_type="UPF",
        network_role="Core User Plane Gateway",
        operational_status=OperationalStatus.ACTIVE,
        health_score=100.0,
        cpu_utilization_pct=28.5,
        memory_utilization_pct=42.0,
        traffic_volume_mbps=75.5,
        latency_ms=2.1,
        packet_loss_pct=0.01,
        connected_components=["gnb-01", "smf-01", "router-edge-01", "switch-core-01", "edge-node-01"],
        network_slice="ALL",
        security_status=SecurityStatus.SECURE,
        provenance=DataClassification.SIMULATED,
        coordinates_3d={"x": 8.0, "y": 0.0, "z": 0.0},
        metadata={"gtpu_port": 2152, "pfcp_port": 8805, "capacity_gbps": 10.0},
    )

    # 4. Supporting Infrastructure
    infra = [
        ("switch-core-01", "SpineSwitch-01", "Switch", "Core Fabric Switch", 18.0, 25.0, 0.4, ["gnb-01", "upf-01", "router-edge-01"]),
        ("router-edge-01", "EdgeRouter-01", "Gateway", "Edge Boundary Gateway", 22.0, 31.0, 1.2, ["upf-01", "switch-core-01", "data-network-01", "edge-node-01"]),
        ("edge-node-01", "MEC-Host-01", "EdgeNode", "Multi-Access Edge Computing", 34.0, 48.0, 1.5, ["router-edge-01", "upf-01"]),
        ("data-network-01", "Enterprise-DN", "DataNetwork", "Corporate Intranet / Internet", 15.0, 20.0, 3.5, ["router-edge-01"]),
        ("sec-monitor-01", "CommShield-SOC-01", "SecurityMonitoring", "Zero-Trust Security Monitor", 25.0, 40.0, 0.5, ["amf-01", "smf-01", "upf-01", "router-edge-01"]),
    ]

    for iid, iname, itype, irole, cpu, mem, lat, conn in infra:
        comps[iid] = NetworkComponent(
            id=iid,
            name=iname,
            component_type=itype,
            network_role=irole,
            operational_status=OperationalStatus.ACTIVE,
            health_score=100.0,
            cpu_utilization_pct=cpu,
            memory_utilization_pct=mem,
            traffic_volume_mbps=75.0,
            latency_ms=lat,
            packet_loss_pct=0.0,
            connected_components=conn,
            network_slice="ALL",
            security_status=SecurityStatus.SECURE,
            provenance=DataClassification.SIMULATED,
            coordinates_3d={"x": 12.0, "y": 0.0, "z": 0.0},
            metadata={"redundancy": "Active-Standby", "mtu": 9000},
        )

    # 5. Connected Devices (User Equipment across the 3 slices)
    ues = [
        # eMBB Slice Cameras
        ("ue-camera-01", "Camera-North-Gate", "Camera", "sst-1-sd-010203", 11.2, 5.5, 0.01),
        ("ue-camera-02", "Camera-Loading-Dock", "Camera", "sst-1-sd-010203", 11.5, 5.8, 0.01),
        ("ue-camera-03", "Camera-Assembly-Line", "Camera", "sst-1-sd-010203", 11.0, 5.2, 0.01),
        ("ue-camera-04", "Camera-Robotics-Bay", "Camera", "sst-1-sd-010203", 11.5, 5.9, 0.01),
        # URLLC Slice AGVs
        ("ue-agv-01", "AGV-Transporter-Alpha", "AGV", "sst-2-sd-020304", 8.0, 1.8, 0.0001),
        ("ue-agv-02", "AGV-Transporter-Bravo", "AGV", "sst-2-sd-020304", 8.0, 1.7, 0.0001),
        ("ue-agv-03", "AGV-Palletizer-Gamma", "AGV", "sst-2-sd-020304", 8.0, 1.9, 0.0001),
        # mMTC Slice Sensors
        ("ue-sensor-01", "Vibration-Motor-01", "Sensor", "sst-3-sd-030405", 1.4, 12.5, 0.02),
        ("ue-sensor-02", "Vibration-Motor-02", "Sensor", "sst-3-sd-030405", 1.4, 13.0, 0.02),
        ("ue-sensor-03", "Temp-Furnace-01", "Sensor", "sst-3-sd-030405", 1.4, 14.1, 0.02),
        ("ue-sensor-04", "Pressure-Valve-01", "Sensor", "sst-3-sd-030405", 1.4, 12.8, 0.02),
        ("ue-sensor-05", "AirQuality-Hall-A", "Sensor", "sst-3-sd-030405", 1.5, 14.5, 0.02),
        ("ue-sensor-06", "FlowMeter-Chiller-01", "Sensor", "sst-3-sd-030405", 1.4, 13.2, 0.02),
    ]

    for uid, uname, utype, uslice, tput, lat, ploss in ues:
        comps[uid] = NetworkComponent(
            id=uid,
            name=uname,
            component_type="UE",
            network_role=f"Private 5G Terminal ({utype})",
            operational_status=OperationalStatus.ACTIVE,
            health_score=100.0,
            cpu_utilization_pct=15.0,
            memory_utilization_pct=20.0,
            traffic_volume_mbps=tput,
            latency_ms=lat,
            packet_loss_pct=ploss,
            connected_components=["gnb-01"],
            network_slice=uslice,
            security_status=SecurityStatus.SECURE,
            provenance=DataClassification.SIMULATED,
            coordinates_3d={"x": -10.0, "y": 0.0, "z": 0.0},
            metadata={"device_type": utype, "auth_state": "AUTHENTICATED", "imei": f"86123404{uid.split('-')[-1]}"},
        )

    return comps


def build_canonical_connections() -> Dict[str, NetworkConnection]:
    """Construct all control-plane and user-plane connections with standard 3GPP protocols."""
    conns: Dict[str, NetworkConnection] = {}

    link_specs = [
        # --- Control Plane Connections ---
        ("conn-n2-gnb-amf", "gnb-01", "amf-01", ConnectionType.CONTROL_PLANE, "N2 (SCTP/NGAP)", 1000.0, 12.5, 1.2, 0.0, "ALL"),
        ("conn-n11-amf-smf", "amf-01", "smf-01", ConnectionType.CONTROL_PLANE, "N11 (HTTP/2 SBI)", 2000.0, 18.0, 1.1, 0.0, "ALL"),
        ("conn-n4-smf-upf", "smf-01", "upf-01", ConnectionType.CONTROL_PLANE, "N4 (PFCP UDP 8805)", 1000.0, 8.4, 1.3, 0.0, "ALL"),
        ("conn-n12-amf-ausf", "amf-01", "ausf-01", ConnectionType.CONTROL_PLANE, "N12 (HTTP/2 SBI)", 1000.0, 5.0, 1.0, 0.0, "ALL"),
        ("conn-n13-ausf-udm", "ausf-01", "udm-01", ConnectionType.CONTROL_PLANE, "N13 (HTTP/2 SBI)", 1000.0, 4.5, 1.0, 0.0, "ALL"),
        ("conn-n10-smf-udm", "smf-01", "udm-01", ConnectionType.CONTROL_PLANE, "N10 (HTTP/2 SBI)", 1000.0, 6.2, 1.1, 0.0, "ALL"),
        ("conn-n7-smf-pcf", "smf-01", "pcf-01", ConnectionType.CONTROL_PLANE, "N7 (HTTP/2 SBI)", 1000.0, 5.5, 1.2, 0.0, "ALL"),
        ("conn-n15-amf-pcf", "amf-01", "pcf-01", ConnectionType.CONTROL_PLANE, "N15 (HTTP/2 SBI)", 1000.0, 4.0, 1.0, 0.0, "ALL"),
        ("conn-n22-amf-nssf", "amf-01", "nssf-01", ConnectionType.CONTROL_PLANE, "N22 (HTTP/2 SBI)", 1000.0, 3.2, 0.9, 0.0, "ALL"),
        ("conn-nrf-amf", "amf-01", "nrf-01", ConnectionType.CONTROL_PLANE, "Nnrf (HTTP/2 SBI)", 1000.0, 2.0, 0.8, 0.0, "ALL"),
        ("conn-nrf-smf", "smf-01", "nrf-01", ConnectionType.CONTROL_PLANE, "Nnrf (HTTP/2 SBI)", 1000.0, 2.0, 0.8, 0.0, "ALL"),
        ("conn-udr-udm", "udm-01", "udr-01", ConnectionType.CONTROL_PLANE, "Nudr (HTTP/2 Database)", 2000.0, 8.0, 0.9, 0.0, "ALL"),
        ("conn-udr-pcf", "pcf-01", "udr-01", ConnectionType.CONTROL_PLANE, "Nudr (HTTP/2 Database)", 2000.0, 6.0, 0.9, 0.0, "ALL"),
        ("conn-nef-amf", "nef-01", "amf-01", ConnectionType.CONTROL_PLANE, "Nnef (HTTP/2 API)", 1000.0, 2.5, 1.4, 0.0, "ALL"),
        ("conn-sec-mon", "upf-01", "sec-monitor-01", ConnectionType.CONTROL_PLANE, "Telemetry Stream (gRPC)", 5000.0, 45.0, 0.5, 0.0, "ALL"),

        # --- User Plane Connections ---
        ("conn-n3-gnb-upf", "gnb-01", "upf-01", ConnectionType.USER_PLANE, "N3 (GTP-U UDP 2152)", 10000.0, 75.5, 2.1, 0.01, "ALL"),
        ("conn-n6-upf-router", "upf-01", "router-edge-01", ConnectionType.USER_PLANE, "N6 (IPv4/IPv6 Routed)", 10000.0, 72.0, 1.2, 0.01, "ALL"),
        ("conn-n9-upf-mec", "upf-01", "edge-node-01", ConnectionType.USER_PLANE, "N9 (Local Breakout GTP-U)", 10000.0, 25.0, 0.8, 0.0, "sst-2-sd-020304"),
        ("conn-router-dn", "router-edge-01", "data-network-01", ConnectionType.USER_PLANE, "Enterprise Transit (BGP/IP)", 10000.0, 47.0, 3.5, 0.01, "ALL"),
        ("conn-switch-fabric", "gnb-01", "switch-core-01", ConnectionType.USER_PLANE, "Optical Ethernet (10GbE)", 10000.0, 77.7, 0.4, 0.0, "ALL"),
        ("conn-switch-upf", "switch-core-01", "upf-01", ConnectionType.USER_PLANE, "Optical Ethernet (10GbE)", 10000.0, 75.5, 0.4, 0.0, "ALL"),

        # --- RAN Radio Uu Access Connections (One per UE) ---
        ("conn-uu-cam-01", "ue-camera-01", "gnb-01", ConnectionType.USER_PLANE, "3GPP 5G-NR Uu", 100.0, 11.2, 5.5, 0.01, "sst-1-sd-010203"),
        ("conn-uu-cam-02", "ue-camera-02", "gnb-01", ConnectionType.USER_PLANE, "3GPP 5G-NR Uu", 100.0, 11.5, 5.8, 0.01, "sst-1-sd-010203"),
        ("conn-uu-cam-03", "ue-camera-03", "gnb-01", ConnectionType.USER_PLANE, "3GPP 5G-NR Uu", 100.0, 11.0, 5.2, 0.01, "sst-1-sd-010203"),
        ("conn-uu-cam-04", "ue-camera-04", "gnb-01", ConnectionType.USER_PLANE, "3GPP 5G-NR Uu", 100.0, 11.5, 5.9, 0.01, "sst-1-sd-010203"),
        ("conn-uu-agv-01", "ue-agv-01", "gnb-01", ConnectionType.USER_PLANE, "3GPP 5G-NR Uu", 100.0, 8.0, 1.8, 0.0001, "sst-2-sd-020304"),
        ("conn-uu-agv-02", "ue-agv-02", "gnb-01", ConnectionType.USER_PLANE, "3GPP 5G-NR Uu", 100.0, 8.0, 1.7, 0.0001, "sst-2-sd-020304"),
        ("conn-uu-agv-03", "ue-agv-03", "gnb-01", ConnectionType.USER_PLANE, "3GPP 5G-NR Uu", 100.0, 8.0, 1.9, 0.0001, "sst-2-sd-020304"),
        ("conn-uu-sns-01", "ue-sensor-01", "gnb-01", ConnectionType.USER_PLANE, "3GPP 5G-NR Uu", 50.0, 1.4, 12.5, 0.02, "sst-3-sd-030405"),
        ("conn-uu-sns-02", "ue-sensor-02", "gnb-01", ConnectionType.USER_PLANE, "3GPP 5G-NR Uu", 50.0, 1.4, 13.0, 0.02, "sst-3-sd-030405"),
        ("conn-uu-sns-03", "ue-sensor-03", "gnb-01", ConnectionType.USER_PLANE, "3GPP 5G-NR Uu", 50.0, 1.4, 14.1, 0.02, "sst-3-sd-030405"),
        ("conn-uu-sns-04", "ue-sensor-04", "gnb-01", ConnectionType.USER_PLANE, "3GPP 5G-NR Uu", 50.0, 1.4, 12.8, 0.02, "sst-3-sd-030405"),
        ("conn-uu-sns-05", "ue-sensor-05", "gnb-01", ConnectionType.USER_PLANE, "3GPP 5G-NR Uu", 50.0, 1.5, 14.5, 0.02, "sst-3-sd-030405"),
        ("conn-uu-sns-06", "ue-sensor-06", "gnb-01", ConnectionType.USER_PLANE, "3GPP 5G-NR Uu", 50.0, 1.4, 13.2, 0.02, "sst-3-sd-030405"),
    ]

    for lid, src, dst, ctype, proto, cap, util, lat, ploss, slc in link_specs:
        util_pct = round((util / cap) * 100.0, 2)
        conns[lid] = NetworkConnection(
            id=lid,
            source=src,
            destination=dst,
            connection_type=ctype,
            direction="BIDIRECTIONAL",
            protocol=proto,
            capacity_mbps=cap,
            utilization_mbps=util,
            utilization_pct=util_pct,
            latency_ms=lat,
            packet_loss_pct=ploss,
            connection_status=ConnectionStatus.ACTIVE,
            associated_slice=slc,
            security_status="NORMAL",
            provenance=DataClassification.SIMULATED,
        )

    return conns
# CommShield AI Core
