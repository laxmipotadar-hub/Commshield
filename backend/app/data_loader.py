"""5G-NIDD Real Data Loader and Window Aggregator.

Loads flow-level records from 5G-NIDD NetFlow/Argus captures (Samarakoon et al. 2022,
arXiv 2212.01298), maps attack signatures to canonical internal enums, assigns slices
by port/protocol pattern, and aggregates flows into 60-second canonical TelemetryWindow
data models.
"""

from collections import Counter
import csv
from datetime import datetime, timezone
from enum import Enum
import json
import math
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union
import uuid

from pydantic import BaseModel, Field

# Canonical S-NSSAI Slice Identifiers
SLICE_EMBB = "sst-1-sd-010203"   # Enhanced Mobile Broadband (Web/streaming/high bandwidth)
SLICE_URLLC = "sst-2-sd-010203"  # Ultra-Reliable Low-Latency Communication (DNS/NTP/RTP/Voice)
SLICE_MMTC = "sst-3-sd-010203"   # Massive Machine-Type Communication (IoT/Sensors/ICMP)

# Standard Port Mappings for Slice Assignment
URLLC_PORTS = {53, 123, 5004, 5005, 51820}
MMTC_PORTS = {1883, 8883, 5683, 5684}
EMBB_PORTS = {80, 443, 8080, 8443}


class AttackLabel(str, Enum):
    """The 8 canonical 5G-NIDD attack classes."""
    NORMAL = "normal"
    UDP_FLOOD = "udp_flood"
    HTTP_FLOOD = "http_flood"
    SYN_FLOOD = "syn_flood"
    TCP_CONNECT = "tcp_connect"
    SYN_SCAN = "syn_scan"
    SLOWLORIS = "slowloris"
    TORSHAMMER = "torshammer"


class TelemetryWindow(BaseModel):
    """Aggregated 60-second canonical telemetry window from 5G-NIDD flows."""
    window_id: str = Field(..., description="Unique window identifier (UUID)")
    timestamp: str = Field(..., description="ISO 8601 window start timestamp")
    slice_id: str = Field(..., description="Network slice ID (e.g. sst-1-sd-010203)")
    uplink_mb: float = Field(..., description="Uplink volume in megabytes")
    downlink_mb: float = Field(..., description="Downlink volume in megabytes")
    total_packets: int = Field(..., description="Total packet count in window")
    udp_ratio: float = Field(..., description="Proportion of UDP flows/traffic (0.0 to 1.0)")
    tcp_ratio: float = Field(..., description="Proportion of TCP flows/traffic (0.0 to 1.0)")
    icmp_ratio: float = Field(..., description="Proportion of ICMP flows/traffic (0.0 to 1.0)")
    unique_src_ips: int = Field(..., description="Number of distinct source IP addresses")
    unique_dst_ports: int = Field(..., description="Number of distinct destination ports")
    syn_flag_ratio: float = Field(..., description="Proportion of flows with SYN flag set")
    rst_flag_ratio: float = Field(..., description="Proportion of flows with RST flag set")
    avg_inter_arrival_ms: float = Field(..., description="Mean flow inter-arrival time in milliseconds")
    inter_arrival_cv: float = Field(..., description="Coefficient of variation of inter-arrival times (std/mean)")
    attack_label: str = Field(..., description="Canonical ground-truth class (AttackLabel enum value)")


def assign_slice_by_port_protocol(proto: str, sport: Any = 0, dport: Any = 0) -> str:
    """Assign network slice ID based on port and protocol patterns:
    - URLLC (sst-2-sd-010203): UDP DNS (53), NTP (123), RTP media (5004-5005), WireGuard (51820)
    - mMTC (sst-3-sd-010203): ICMP protocol, MQTT (1883/8883), CoAP (5683/5684)
    - eMBB (sst-1-sd-010203): HTTP (80), HTTPS (443), general TCP streaming and bulk traffic
    """
    proto_clean = str(proto or "").strip().lower()
    try:
        dp = int(dport) if dport else 0
    except (ValueError, TypeError):
        dp = 0
    try:
        sp = int(sport) if sport else 0
    except (ValueError, TypeError):
        sp = 0

    ports = {dp, sp}

    # mMTC: ICMP or IoT message protocols
    if proto_clean == "icmp" or bool(ports & MMTC_PORTS):
        return SLICE_MMTC

    # URLLC: low-latency UDP services
    if proto_clean == "udp" and (bool(ports & URLLC_PORTS) or (5000 <= dp <= 5100)):
        return SLICE_URLLC

    # eMBB: web and default broadband traffic
    return SLICE_EMBB


def map_attack_label(
    label: str,
    attack_type: Optional[str] = None,
    attack_tool: Optional[str] = None,
) -> AttackLabel:
    """Map raw 5G-NIDD label and attack fields to the 8 canonical internal classes."""
    combined = f"{label or ''} {attack_type or ''} {attack_tool or ''}".lower()

    if "udp" in combined and "flood" in combined:
        return AttackLabel.UDP_FLOOD
    if "http" in combined and "flood" in combined or "goldeneye" in combined:
        return AttackLabel.HTTP_FLOOD
    if "syn" in combined and "flood" in combined:
        return AttackLabel.SYN_FLOOD
    if "tcp" in combined and ("connect" in combined or "tcpconnect" in combined):
        return AttackLabel.TCP_CONNECT
    if "syn" in combined and "scan" in combined or "portscan" in combined:
        return AttackLabel.SYN_SCAN
    if "slowloris" in combined or "slowrate" in combined:
        return AttackLabel.SLOWLORIS
    if "torshammer" in combined or ("tor" in combined and "hammer" in combined):
        return AttackLabel.TORSHAMMER

    # Check general malicious/attack indicators
    is_malicious = (
        "malicious" in combined
        or "attack" in combined
        or str(label).strip() == "1"
    ) and not ("benign" in combined or "normal" in combined)

    if is_malicious:
        if "udp" in combined:
            return AttackLabel.UDP_FLOOD
        if "http" in combined:
            return AttackLabel.HTTP_FLOOD
        if "scan" in combined:
            return AttackLabel.SYN_SCAN
        return AttackLabel.SYN_FLOOD

    return AttackLabel.NORMAL


def _parse_flow_timestamp(row: Dict[str, Any], base_epoch: float = 1663272000.0) -> float:
    """Parse timestamp into unix epoch seconds."""
    # 1. Direct timestamp field
    ts_val = row.get("timestamp") or row.get("Time")
    if ts_val is not None:
        try:
            return float(ts_val)
        except ValueError:
            try:
                dt = datetime.fromisoformat(str(ts_val).replace("Z", "+00:00"))
                return dt.timestamp()
            except Exception:
                pass

    # 2. IdleTime base epoch
    idle_val = row.get("IdleTime")
    if idle_val:
        try:
            parsed_idle = float(idle_val)
            if parsed_idle > 1000000000:
                base_epoch = parsed_idle
        except ValueError:
            pass

    # 3. StartTime offset (e.g., "12:34.5", "1:23:45.6", or float seconds)
    start_val = str(row.get("StartTime") or "").strip()
    if start_val:
        try:
            if ":" in start_val:
                parts = start_val.split(":")
                if len(parts) == 2:
                    offset = float(parts[0]) * 60.0 + float(parts[1])
                elif len(parts) == 3:
                    offset = float(parts[0]) * 3600.0 + float(parts[1]) * 60.0 + float(parts[2])
                else:
                    offset = float(parts[0])
                return base_epoch + offset
            else:
                return base_epoch + float(start_val)
        except ValueError:
            pass

    return base_epoch


def load_5g_nidd_csv(
    file_path: Union[str, Path],
    window_duration_sec: int = 60,
    attack_threshold: float = 0.05,
) -> List[TelemetryWindow]:
    """Load Argus flow records from 5G-NIDD CSV, assign slices, and aggregate into 60s windows."""
    path = Path(file_path)
    if not path.is_file():
        raise FileNotFoundError(f"5G-NIDD file not found at: {path}")

    # Read records and parse flows
    parsed_flows: List[Dict[str, Any]] = []
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if not row:
                continue

            ts = _parse_flow_timestamp(row)
            src_addr = str(row.get("SrcAddr") or row.get("src_addr") or "").strip()
            dst_addr = str(row.get("DstAddr") or row.get("dst_addr") or "").strip()
            proto = str(row.get("Proto") or row.get("proto") or "tcp").strip().lower()

            sport_raw = row.get("Sport") or row.get("sport") or 0
            dport_raw = row.get("Dport") or row.get("dport") or 0

            # TotPkts
            try:
                tot_pkts = int(float(row.get("TotPkts") or row.get("tot_pkts") or row.get("packets") or 1))
            except (ValueError, TypeError):
                tot_pkts = 1

            # Bytes
            try:
                tot_bytes = float(row.get("TotBytes") or row.get("tot_bytes") or 0)
            except (ValueError, TypeError):
                tot_bytes = 0.0

            try:
                src_bytes = float(row.get("SrcBytes") or row.get("src_bytes") or 0)
            except (ValueError, TypeError):
                src_bytes = 0.0

            try:
                dst_bytes = float(row.get("DstBytes") or row.get("dst_bytes") or 0)
            except (ValueError, TypeError):
                dst_bytes = 0.0

            if src_bytes == 0.0 and dst_bytes == 0.0 and tot_bytes > 0:
                src_bytes = tot_bytes * 0.4
                dst_bytes = tot_bytes * 0.6

            # Flags
            flgs = str(row.get("Flgs") or row.get("flags") or "").lower()
            state = str(row.get("State") or row.get("state") or "").lower()
            has_syn = ("s" in flgs) or ("syn" in state) or ("req" in state)
            has_rst = ("r" in flgs) or ("rst" in state)

            # Attack mapping
            label = str(row.get("Label") or row.get("label") or "Benign").strip()
            attack_type = row.get("Attack Type") or row.get("attack_type")
            attack_tool = row.get("Attack Tool") or row.get("attack_tool")
            flow_attack_label = map_attack_label(label, attack_type, attack_tool)

            slice_id = assign_slice_by_port_protocol(proto, sport_raw, dport_raw)

            parsed_flows.append({
                "timestamp": ts,
                "src_addr": src_addr,
                "dst_addr": dst_addr,
                "sport": sport_raw,
                "dport": dport_raw,
                "proto": proto,
                "tot_pkts": tot_pkts,
                "src_bytes": src_bytes,
                "dst_bytes": dst_bytes,
                "has_syn": has_syn,
                "has_rst": has_rst,
                "attack_label": flow_attack_label,
                "slice_id": slice_id,
            })

    if not parsed_flows:
        return []

    # Determine reference start time
    min_time = min(f["timestamp"] for f in parsed_flows)

    # Group flows by (slice_id, window_index)
    buckets: Dict[Tuple[str, int], List[Dict[str, Any]]] = {}
    for flow in parsed_flows:
        window_idx = int((flow["timestamp"] - min_time) // window_duration_sec)
        key = (flow["slice_id"], window_idx)
        if key not in buckets:
            buckets[key] = []
        buckets[key].append(flow)

    # Aggregate each bucket into a TelemetryWindow
    windows: List[TelemetryWindow] = []
    # Sort keys chronologically
    sorted_keys = sorted(buckets.keys(), key=lambda k: (k[1], k[0]))

    for slice_id, window_idx in sorted_keys:
        flows = buckets[(slice_id, window_idx)]
        flows.sort(key=lambda f: f["timestamp"])

        w_start_epoch = min_time + (window_idx * window_duration_sec)
        w_start_dt = datetime.fromtimestamp(w_start_epoch, tz=timezone.utc)
        w_timestamp = w_start_dt.isoformat()

        # Volume metrics
        uplink_bytes = sum(f["src_bytes"] for f in flows)
        downlink_bytes = sum(f["dst_bytes"] for f in flows)
        uplink_mb = round(uplink_bytes / (1024.0 * 1024.0), 2)
        downlink_mb = round(downlink_bytes / (1024.0 * 1024.0), 2)
        total_packets = sum(f["tot_pkts"] for f in flows)

        # Protocol ratios
        n_flows = len(flows)
        udp_count = sum(1 for f in flows if "udp" in f["proto"])
        tcp_count = sum(1 for f in flows if "tcp" in f["proto"])
        icmp_count = sum(1 for f in flows if "icmp" in f["proto"])

        udp_ratio = round(udp_count / n_flows, 4) if n_flows > 0 else 0.0
        tcp_ratio = round(tcp_count / n_flows, 4) if n_flows > 0 else 0.0
        icmp_ratio = round(icmp_count / n_flows, 4) if n_flows > 0 else 0.0

        # Unique addresses and ports
        unique_src_ips = len({f["src_addr"] for f in flows if f["src_addr"]})
        unique_dst_ports = len({f["dport"] for f in flows if f["dport"] is not None})

        # Flag ratios
        syn_count = sum(1 for f in flows if f["has_syn"])
        rst_count = sum(1 for f in flows if f["has_rst"])
        syn_flag_ratio = round(syn_count / n_flows, 4) if n_flows > 0 else 0.0
        rst_flag_ratio = round(rst_count / n_flows, 4) if n_flows > 0 else 0.0

        # Inter-arrival times (in milliseconds)
        if len(flows) > 1:
            diffs_ms = [
                (flows[i]["timestamp"] - flows[i - 1]["timestamp"]) * 1000.0
                for i in range(1, len(flows))
            ]
            avg_inter_arrival = float(sum(diffs_ms) / len(diffs_ms))
            var_ms = sum((d - avg_inter_arrival) ** 2 for d in diffs_ms) / len(diffs_ms)
            std_ms = math.sqrt(var_ms)
            cv = (std_ms / avg_inter_arrival) if avg_inter_arrival > 0 else 0.0
        else:
            avg_inter_arrival = 0.0
            cv = 0.0

        # Ground truth attack label
        attack_counts = Counter(f["attack_label"] for f in flows)
        malicious_flows = [f for f in flows if f["attack_label"] != AttackLabel.NORMAL]
        malicious_ratio = len(malicious_flows) / n_flows if n_flows > 0 else 0.0

        if malicious_ratio >= attack_threshold and malicious_flows:
            # Pick dominant malicious class
            dominant_attack = Counter(f["attack_label"] for f in malicious_flows).most_common(1)[0][0]
            verdict_label = dominant_attack.value
        else:
            verdict_label = AttackLabel.NORMAL.value

        window = TelemetryWindow(
            window_id=str(uuid.uuid4()),
            timestamp=w_timestamp,
            slice_id=slice_id,
            uplink_mb=max(0.01, uplink_mb),
            downlink_mb=max(0.01, downlink_mb),
            total_packets=max(1, total_packets),
            udp_ratio=udp_ratio,
            tcp_ratio=tcp_ratio,
            icmp_ratio=icmp_ratio,
            unique_src_ips=max(1, unique_src_ips),
            unique_dst_ports=max(1, unique_dst_ports),
            syn_flag_ratio=syn_flag_ratio,
            rst_flag_ratio=rst_flag_ratio,
            avg_inter_arrival_ms=round(avg_inter_arrival, 2),
            inter_arrival_cv=round(cv, 3),
            attack_label=verdict_label,
        )
        windows.append(window)

    return windows


def generate_manifest(
    windows: List[TelemetryWindow],
    output_path: Optional[Union[str, Path]] = None,
) -> Dict[str, Any]:
    """Generate and optionally save manifest metadata for a list of TelemetryWindow instances."""
    attack_dist = Counter(w.attack_label for w in windows)

    # Ensure all 8 classes are represented in distribution dictionary
    distribution_dict: Dict[str, int] = {}
    for label in AttackLabel:
        distribution_dict[label.value] = attack_dist.get(label.value, 0)

    time_span = {}
    if windows:
        time_span = {
            "start": min(w.timestamp for w in windows),
            "end": max(w.timestamp for w in windows),
        }

    unique_slices = sorted(list({w.slice_id for w in windows}))

    manifest = {
        "dataset": "5G-NIDD",
        "version": "1.0",
        "total_windows": len(windows),
        "attack_distribution": distribution_dict,
        "slices": unique_slices,
        "window_duration_sec": 60,
        "time_span": time_span,
        "features": [
            "window_id",
            "timestamp",
            "slice_id",
            "uplink_mb",
            "downlink_mb",
            "total_packets",
            "udp_ratio",
            "tcp_ratio",
            "icmp_ratio",
            "unique_src_ips",
            "unique_dst_ports",
            "syn_flag_ratio",
            "rst_flag_ratio",
            "avg_inter_arrival_ms",
            "inter_arrival_cv",
            "attack_label",
        ],
    }

    if output_path:
        out_p = Path(output_path)
        out_p.parent.mkdir(parents=True, exist_ok=True)
        with open(out_p, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2)

    return manifest
# CommShield AI Core
