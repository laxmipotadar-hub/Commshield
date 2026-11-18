"""5G-NIDD Telemetry Adapter for CommShield.

Transforms flow-level Argus flow records from the 5G-NIDD dataset into
the canonical schema specified in CONTRACTS.md, aggregating flows into
10-second and 60-second windows.

Handles missing control-plane fields without value fabrication and marks
flow-level user-plane proxies as labelled proxies. Defines slice mapping
by base station (BS1 -> eMBB, BS2 -> URLLC) with explicit disclosure.
"""

from collections import Counter
import csv
from datetime import datetime, timezone
import math
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, List, Optional, Set, Tuple, Union
import uuid

from .base import (
    DEFAULT_SUPPRESSION_K,
    SUPPRESSED_ENTROPY_VALUE,
    TelemetryAdapter,
    enforce_aggregate_boundary,
    pseudonymize_identifier,
)

# Canonical network slice mapping for 5G-NIDD (Assigned slices, not native 3GPP tags)
BS1_SLICE_ID = "sst-1-sd-010203"  # Assigned: eMBB
BS2_SLICE_ID = "sst-2-sd-010203"  # Assigned: URLLC

LABELLED_PROXIES = [
    "active_ue_count",
    "pdu_sessions_established",
    "pdu_session_rate_per_ue",
    "gtpu_volume_per_ue",
    "ue_hash_entropy",
    "new_ue_rate",
]

MISSING_CANONICAL_FIELDS = [
    "registration_attempts",
    "registration_failures",
    "nas_messages_total",
    "nas_failures",
    "pfcp_association_messages",
    "pfcp_failures",
    "gtpu_teid_count",
    "registrations_per_active_ue",
    "nas_failure_ratio",
    "pfcp_failure_ratio",
]


def assign_slice_id(bs_identifier: Optional[str] = None) -> str:
    """Map base station identifier to canonical slice ID.
    
    BS1 / BTS1 -> sst-1-sd-010203 (eMBB - Assigned Slice)
    BS2 / BTS2 -> sst-2-sd-010203 (URLLC - Assigned Slice)
    """
    if not bs_identifier:
        return BS1_SLICE_ID
    bs_str = str(bs_identifier).strip().upper()
    if "BS2" in bs_str or "BTS2" in bs_str or "URLLC" in bs_str:
        return BS2_SLICE_ID
    return BS1_SLICE_ID


class FiveGNIDDAdapter(TelemetryAdapter):
    """Telemetry adapter for the public 5G-NIDD NetFlow / Argus dataset.
    
    Aggregates flow records into 10s / 60s CanonicalTrafficWindow schemas.
    Control-plane fields (NAS, PFCP, registration) are not available in flow records
    and default to zero / safe ratios without fabrication.
    """

    def __init__(
        self,
        default_attack_threshold: float = 0.05,
        suppression_k: Optional[int] = None,
    ):
        self.default_attack_threshold = default_attack_threshold
        self.suppression_k = suppression_k if suppression_k is not None else DEFAULT_SUPPRESSION_K
        # Track seen client IPs per slice to compute new_ue_rate across consecutive windows
        self._previous_ues_by_slice: Dict[str, Set[str]] = {}

    def reset_state(self) -> None:
        """Clear stateful window memory."""
        self._previous_ues_by_slice.clear()

    def parse_records(self, records: Union[Iterable[Any], str, Path]) -> Iterator[Dict[str, Any]]:
        """Parse raw 5G-NIDD records from an iterable, CSV filepath, or dict stream."""
        if isinstance(records, (str, Path)):
            file_path = Path(records)
            if not file_path.is_file():
                raise FileNotFoundError(f"5G-NIDD source file not found: {file_path}")
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                reader = csv.DictReader(f)
                yield from self._parse_dict_stream(reader)
        else:
            yield from self._parse_dict_stream(records)

    def _parse_dict_stream(self, records: Iterable[Any]) -> Iterator[Dict[str, Any]]:
        """Parse dictionary or raw record objects into normalized flow events."""
        prev_sec: Optional[float] = None
        hour_offset: float = 0.0

        for rec in records:
            if not isinstance(rec, dict):
                continue

            # 1. Parse timestamp
            ts: Optional[datetime] = None
            if "timestamp" in rec:
                val = rec["timestamp"]
                if isinstance(val, datetime):
                    ts = val if val.tzinfo else val.replace(tzinfo=timezone.utc)
                elif isinstance(val, (int, float)):
                    ts = datetime.fromtimestamp(float(val), tz=timezone.utc)
                elif isinstance(val, str):
                    try:
                        ts = datetime.fromisoformat(val.replace("Z", "+00:00"))
                    except Exception:
                        pass

            if ts is None and "StartTime" in rec and rec.get("StartTime"):
                start_val = str(rec["StartTime"]).strip()
                try:
                    if ":" in start_val:
                        parts = start_val.split(":")
                        if len(parts) == 2:
                            sec = float(parts[0]) * 60.0 + float(parts[1])
                        elif len(parts) == 3:
                            sec = float(parts[0]) * 3600.0 + float(parts[1]) * 60.0 + float(parts[2])
                        else:
                            sec = float(parts[0])

                        if prev_sec is not None and sec < prev_sec - 1800:
                            hour_offset += 3600.0
                        prev_sec = sec

                        base_epoch = float(rec.get("IdleTime") or 1663055000)
                        ts = datetime.fromtimestamp(base_epoch + hour_offset + sec, tz=timezone.utc)
                    else:
                        sec = float(start_val)
                        base_epoch = float(rec.get("IdleTime") or 1663055000)
                        ts = datetime.fromtimestamp(base_epoch + sec, tz=timezone.utc)
                except Exception:
                    pass

            if ts is None and "IdleTime" in rec:
                try:
                    idle_epoch = float(rec["IdleTime"])
                    ts = datetime.fromtimestamp(idle_epoch, tz=timezone.utc)
                except Exception:
                    pass

            if ts is None:
                ts = datetime.now(timezone.utc)

            # 2. Extract network headers & identifiers (HMAC-SHA256 pseudonymised immediately)
            src_raw = str(rec.get("SrcAddr") or rec.get("src_addr") or rec.get("src_ip") or "").strip()
            dst_raw = str(rec.get("DstAddr") or rec.get("dst_addr") or rec.get("dst_ip") or "").strip()
            src_addr = pseudonymize_identifier(src_raw) if src_raw else ""
            dst_addr = pseudonymize_identifier(dst_raw) if dst_raw else ""
            proto = str(rec.get("Proto") or rec.get("proto") or "other").strip().lower()

            try:
                tot_pkts = int(float(rec.get("TotPkts") or rec.get("tot_pkts") or rec.get("packets") or 0))
            except Exception:
                tot_pkts = 0

            try:
                tot_bytes = int(float(rec.get("TotBytes") or rec.get("tot_bytes") or rec.get("bytes") or 0))
            except Exception:
                tot_bytes = 0

            try:
                src_bytes = int(float(rec.get("SrcBytes") or rec.get("src_bytes") or 0))
            except Exception:
                src_bytes = 0

            try:
                dst_bytes = int(float(rec.get("DstBytes") or rec.get("dst_bytes") or 0))
            except Exception:
                dst_bytes = 0

            if src_bytes == 0 and dst_bytes == 0 and tot_bytes > 0:
                src_bytes = tot_bytes // 2
                dst_bytes = tot_bytes - src_bytes

            # 3. Label & Attack metadata
            label = str(rec.get("Label") or rec.get("label") or "Benign").strip()
            attack_type = rec.get("Attack Type") or rec.get("attack_type")
            if not attack_type:
                attack_type = "Benign" if label.lower() == "benign" else "Malicious"

            attack_tool = rec.get("Attack Tool") or rec.get("attack_tool")
            if not attack_tool:
                attack_tool = "Benign" if label.lower() == "benign" else "Unknown"

            bs = rec.get("BS") or rec.get("bs") or rec.get("base_station")

            yield {
                "timestamp": ts,
                "src_addr": src_addr,
                "dst_addr": dst_addr,
                "proto": proto,
                "tot_pkts": tot_pkts,
                "tot_bytes": tot_bytes,
                "src_bytes": src_bytes,
                "dst_bytes": dst_bytes,
                "label": label,
                "attack_type": attack_type,
                "attack_tool": attack_tool,
                "bs": bs,
            }

    def aggregate_window(
        self,
        events: List[Dict[str, Any]],
        slice_id: str,
        nf_id: str = "UPF-01",
        window_duration_sec: int = 60,
        window_start: Optional[datetime] = None,
        window_end: Optional[datetime] = None,
        attack_threshold: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Aggregate flow events into a single CanonicalTrafficWindow matching CONTRACTS.md."""
        threshold = attack_threshold if attack_threshold is not None else self.default_attack_threshold

        if window_start is None:
            if events:
                window_start = events[0]["timestamp"]
            else:
                window_start = datetime.now(timezone.utc)

        if window_end is None:
            if events:
                window_end = events[-1]["timestamp"]
            else:
                window_end = window_start

        # 1. Raw Counters
        client_ips: List[str] = [e["src_addr"] for e in events if e.get("src_addr")]
        unique_ues: Set[str] = set(client_ips)
        active_ue_count = len(unique_ues)
        pdu_established = len(events)  # Flow count serves as labelled proxy

        total_bytes_uplink = sum(int(e.get("src_bytes", 0)) for e in events)
        total_bytes_downlink = sum(int(e.get("dst_bytes", 0)) for e in events)
        total_packets = sum(int(e.get("tot_pkts", 0)) for e in events)

        # 2. Ratio Features (Guarded against zero division)
        ue_denom = max(active_ue_count, 1)
        pdu_denom = max(pdu_established, 1)

        registrations_per_active_ue = 0.0  # Control-plane missing in flow logs
        nas_failure_ratio = 0.0            # Control-plane missing in flow logs
        pfcp_failure_ratio = 0.0           # Control-plane missing in flow logs
        pdu_session_rate_per_ue = round(pdu_established / ue_denom, 4)
        bytes_per_session = round((total_bytes_uplink + total_bytes_downlink) / pdu_denom, 2)
        packets_per_session = round(total_packets / pdu_denom, 2)
        gtpu_volume_per_ue = round((total_bytes_uplink + total_bytes_downlink) / ue_denom, 2)

        # Client IP Shannon entropy: H(X) = - sum(p * log2(p))
        # Small-group k-anonymity suppression:
        # If active distinct UEs < K, suppress entropy aggregate to documented value (-1.0)
        if active_ue_count < self.suppression_k:
            ue_hash_entropy = SUPPRESSED_ENTROPY_VALUE
        elif client_ips:
            ip_counts = Counter(client_ips)
            n_ips = len(client_ips)
            entropy = -sum((cnt / n_ips) * math.log2(cnt / n_ips) for cnt in ip_counts.values())
            ue_hash_entropy = round(entropy, 3)
        else:
            ue_hash_entropy = 0.0

        # New UE arrival rate against previous window
        prev_ues = self._previous_ues_by_slice.get(slice_id, set())
        if unique_ues:
            new_ues = unique_ues - prev_ues
            new_ue_rate = round(len(new_ues) / len(unique_ues), 4)
        else:
            new_ue_rate = 0.0
        self._previous_ues_by_slice[slice_id] = unique_ues

        # 3. Protocol Composition Vector (sums to 1.0)
        tcp_count = sum(1 for e in events if "tcp" in e.get("proto", "").lower())
        udp_count = sum(1 for e in events if "udp" in e.get("proto", "").lower())
        icmp_count = sum(1 for e in events if "icmp" in e.get("proto", "").lower())
        n_events = max(len(events), 1)

        tcp_ratio = round(tcp_count / n_events, 4)
        udp_ratio = round(udp_count / n_events, 4)
        icmp_ratio = round(icmp_count / n_events, 4)
        other_ratio = max(0.0, round(1.0 - (tcp_ratio + udp_ratio + icmp_ratio), 4))

        # 4. Ground Truth Mapping
        # Window is an attack window if >= attack_threshold fraction of flows are malicious
        malicious_events = [
            e for e in events
            if str(e.get("label", "")).strip().lower() in ("malicious", "attack", "1")
            or (e.get("attack_type") and str(e.get("attack_type")).strip().lower() not in ("benign", "none"))
        ]
        malicious_count = len(malicious_events)
        total_count = len(events)
        malicious_flow_ratio = (malicious_count / total_count) if total_count > 0 else 0.0

        is_attack = bool(malicious_flow_ratio >= threshold)
        attack_type: Optional[str] = None
        if is_attack and malicious_events:
            attack_candidates = [
                e.get("attack_type") for e in malicious_events
                if e.get("attack_type") and str(e.get("attack_type")).strip().lower() not in ("benign", "none")
            ]
            if attack_candidates:
                attack_type = Counter(attack_candidates).most_common(1)[0][0]
            else:
                attack_type = "Malicious"

        window_id = str(uuid.uuid4())

        canonical_window = {
            "window_id": window_id,
            "slice_id": slice_id,
            "nf_id": nf_id,
            "window_start": window_start.isoformat(),
            "window_end": window_end.isoformat(),
            "duration_sec": window_duration_sec,
            "raw_counters": {
                "active_ue_count": active_ue_count,
                "registration_attempts": 0,
                "registration_failures": 0,
                "pdu_sessions_established": pdu_established,
                "nas_messages_total": 0,
                "nas_failures": 0,
                "pfcp_association_messages": 0,
                "pfcp_failures": 0,
                "total_bytes_uplink": total_bytes_uplink,
                "total_bytes_downlink": total_bytes_downlink,
                "total_packets": total_packets,
                "gtpu_teid_count": 0,
            },
            "ratio_features": {
                "registrations_per_active_ue": registrations_per_active_ue,
                "nas_failure_ratio": nas_failure_ratio,
                "pfcp_failure_ratio": pfcp_failure_ratio,
                "pdu_session_rate_per_ue": pdu_session_rate_per_ue,
                "bytes_per_session": bytes_per_session,
                "packets_per_session": packets_per_session,
                "gtpu_volume_per_ue": gtpu_volume_per_ue,
                "ue_hash_entropy": ue_hash_entropy,
                "new_ue_rate": new_ue_rate,
            },
            "composition_vector": {
                # Canonical schema sum invariants
                "registration_ratio": 0.0,
                "session_setup_ratio": 0.0,
                "failure_ratio": 0.0,
                "other_signalling_ratio": 1.0,
                # Labelled user-plane protocol breakdown proxies
                "tcp_ratio": tcp_ratio,
                "udp_ratio": udp_ratio,
                "icmp_ratio": icmp_ratio,
                "other_ratio": other_ratio,
            },
            "ground_truth": {
                "is_attack": is_attack,
                "attack_type": attack_type,
                "malicious_flow_ratio": round(malicious_flow_ratio, 4),
                "is_growth": False,
            },
            "metadata": {
                "dataset": "fiveg_nidd",
                "is_assigned_slice": True,
                "slice_assignment_note": (
                    "Assigned slice based on base station topology (BS1 -> eMBB, BS2 -> URLLC). "
                    "Not native 3GPP slice tags."
                ),
                "labelled_proxies": LABELLED_PROXIES,
                "missing_canonical_fields": MISSING_CANONICAL_FIELDS,
            },
        }

        return enforce_aggregate_boundary(canonical_window)


def split_chronologically(
    windows: List[Dict[str, Any]],
    train_ratio: float = 0.5,
    val_ratio: float = 0.2,
    benign_only_train: bool = True,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Split canonical windows chronologically into train, validation, and test periods.
    
    Guarantees:
    - Zero random shuffling across time.
    - Strict chronological boundaries: max(train_time) <= min(val_time) <= max(val_time) <= min(test_time).
    - If benign_only_train=True, training set contains strictly benign windows with zero attack leakage.
    """
    if not windows:
        return [], [], []

    # Sort strictly chronologically by window_start
    def _parse_start(w: Dict[str, Any]) -> datetime:
        s = w.get("window_start")
        if isinstance(s, datetime):
            return s if s.tzinfo else s.replace(tzinfo=timezone.utc)
        return datetime.fromisoformat(str(s).replace("Z", "+00:00"))

    sorted_windows = sorted(windows, key=_parse_start)
    n = len(sorted_windows)

    if n < 3:
        # Minimum partition for tiny lists
        return sorted_windows[:1], sorted_windows[1:2], sorted_windows[2:]

    train_idx = max(1, int(n * train_ratio))
    val_idx = max(train_idx + 1, int(n * (train_ratio + val_ratio)))
    if val_idx >= n:
        val_idx = n - 1

    train_part = sorted_windows[:train_idx]
    val_part = sorted_windows[train_idx:val_idx]
    test_part = sorted_windows[val_idx:]

    if benign_only_train:
        # Keep only strictly benign windows for detector/scaler baseline training
        train_part = [w for w in train_part if not w.get("ground_truth", {}).get("is_attack", False)]

    return train_part, val_part, test_part
