"""Cross-Platform Open5GS & AMF Metrics Lab Adapter.

Transforms Open5GS control-plane (AMF/SMF) logs, user-plane (UPF) flow records,
and AMF telemetry metrics into canonical slice-level and per-device windows
conforming to CANONICAL_WINDOW_SCHEMA.md with source="lab".

Enforces cryptographic pseudonymisation of subscriber identities (IMSI) using HMAC-SHA256,
guaranteeing zero raw identifier leakage. Runs fully offline on sample logs.
"""

import argparse
from datetime import datetime, timezone, timedelta
import json
import math
import os
from pathlib import Path
import re
import sys
from typing import Any, Dict, List, Optional, Set, Tuple
import uuid

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ml_engine.provisioning.loader import hash_sim_id, get_twin_hmac_secret
from ml_engine.provisioning.schema import (
    validate_window,
    validate_slice_window,
    validate_device_window,
    parse_iso_timestamp,
    HEX_64_REGEX,
)

# S-NSSAI mappings
SLICE_CLASS_MAP = {
    "sst-1-sd-010203": "camera",
    "sst-2-sd-020304": "AGV",
    "sst-3-sd-030405": "sensor",
}


class LabAdapter:
    """Reads Open5GS logs and metrics and produces validated canonical windows with source='lab'."""

    def __init__(
        self,
        sample_logs_dir: Optional[Path] = None,
        output_file: Optional[Path] = None,
        hmac_key: Optional[bytes] = None,
    ):
        self.sample_logs_dir = sample_logs_dir or (ROOT / "lab" / "sample_logs")
        self.output_file = output_file or (ROOT / "data" / "lab" / "windows.jsonl")
        self.hmac_key = hmac_key or get_twin_hmac_secret()

    def _hash_imsi(self, raw_imsi: str) -> str:
        """Hash an IMSI using HMAC-SHA256, ensuring 64-character lowercase hex."""
        clean_imsi = raw_imsi.strip().lower()
        return hash_sim_id(clean_imsi, self.hmac_key)

    def parse_amf_logs(self, log_path: Path) -> List[Dict[str, Any]]:
        """Parse Open5GS AMF log file into structured event records."""
        events = []
        if not log_path.is_file():
            return events

        # Regex patterns for Open5GS AMF log lines
        line_re = re.compile(
            r"^(?P<date>\d{2}/\d{2})\s+(?P<time>\d{2}:\d{2}:\d{2}\.\d{3}):?\s+\[(?P<comp>\w+)\]\s+(?P<level>\w+):\s+(?:\[(?P<imsi>[^:\]]+)(?::\d+)?\])?\s*(?P<msg>.*)$"
        )
        slice_re = re.compile(r"S-NSSAI:\s+SST:(\d+)\s+SD:0x([0-9a-fA-F]+)")

        year = 2026
        with open(log_path, "r", encoding="utf-8", newline="\n") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                m = line_re.match(line)
                if not m:
                    continue
                d_str = m.group("date")
                t_str = m.group("time")
                level = m.group("level").upper()
                raw_imsi = m.group("imsi")
                msg = m.group("msg")

                # Parse timestamp into UTC datetime
                month, day = [int(x) for x in d_str.split("/")]
                hh, mm, ss = t_str.split(":")
                sec, msec = ss.split(".")
                dt = datetime(year, month, day, int(hh), int(mm), int(sec), int(msec) * 1000, tzinfo=timezone.utc)

                # Slice detection
                slice_id = None
                sm = slice_re.search(msg)
                if sm:
                    sst = int(sm.group(1))
                    sd = sm.group(2).lower()
                    slice_id = f"sst-{sst}-sd-{sd}"
                elif raw_imsi:
                    # Infer slice from IMSI convention if not explicitly logged on line
                    if "00001" in raw_imsi or "00002" in raw_imsi or "00003" in raw_imsi or "00004" in raw_imsi:
                        slice_id = "sst-1-sd-010203"
                    elif "00011" in raw_imsi or "00012" in raw_imsi:
                        slice_id = "sst-2-sd-020304"
                    else:
                        slice_id = "sst-3-sd-030405"

                events.append({
                    "timestamp": dt,
                    "component": m.group("comp"),
                    "level": level,
                    "raw_imsi": raw_imsi,
                    "slice_id": slice_id,
                    "msg": msg,
                    "is_failure": bool(level in ("ERROR", "WARNING") or "failed" in msg.lower() or "rejected" in msg.lower()),
                })
        return events

    def parse_upf_logs(self, log_path: Path) -> List[Dict[str, Any]]:
        """Parse Open5GS UPF flow log records."""
        flows = []
        if not log_path.is_file():
            return flows

        line_re = re.compile(
            r"^(?P<date>\d{2}/\d{2})\s+(?P<time>\d{2}:\d{2}:\d{2}\.\d{3}):?\s+\[(?P<comp>\w+)\]\s+(?P<level>\w+):\s+(?:\[(?P<imsi>[^:\]]+)\])?\s*(?P<msg>.*)$"
        )
        flow_stats_re = re.compile(
            r"packets_ul=(?P<pul>\d+),\s+bytes_ul=(?P<bul>\d+),\s+packets_dl=(?P<pdl>\d+),\s+bytes_dl=(?P<bdl>\d+)"
        )
        slice_re = re.compile(r"slice=(?P<slc>sst-\d+-sd-[0-9a-fA-F]+)")

        year = 2026
        with open(log_path, "r", encoding="utf-8", newline="\n") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                m = line_re.match(line)
                if not m:
                    continue
                d_str = m.group("date")
                t_str = m.group("time")
                raw_imsi = m.group("imsi")
                msg = m.group("msg")

                month, day = [int(x) for x in d_str.split("/")]
                hh, mm, ss = t_str.split(":")
                sec, msec = ss.split(".")
                dt = datetime(year, month, day, int(hh), int(mm), int(sec), int(msec) * 1000, tzinfo=timezone.utc)

                sl_m = slice_re.search(msg)
                slice_id = sl_m.group("slc") if sl_m else "sst-1-sd-010203"

                f_m = flow_stats_re.search(msg)
                pul = int(f_m.group("pul")) if f_m else 0
                bul = int(f_m.group("bul")) if f_m else 0
                pdl = int(f_m.group("pdl")) if f_m else 0
                bdl = int(f_m.group("bdl")) if f_m else 0

                flows.append({
                    "timestamp": dt,
                    "raw_imsi": raw_imsi,
                    "slice_id": slice_id,
                    "packets_ul": pul,
                    "bytes_ul": bul,
                    "packets_dl": pdl,
                    "bytes_dl": bdl,
                })
        return flows

    def load_amf_metrics(self, metrics_path: Path) -> List[Dict[str, Any]]:
        """Load JSON snapshots of AMF counters."""
        if not metrics_path.is_file():
            return []
        with open(metrics_path, "r", encoding="utf-8", newline="\n") as f:
            return json.load(f)

    def process_and_emit(self) -> int:
        """Run adapter: ingest sample logs & metrics, generate canonical windows, validate, and write data/lab/windows.jsonl."""
        amf_log_file = self.sample_logs_dir / "open5gs_amf.log"
        upf_log_file = self.sample_logs_dir / "open5gs_upf.log"
        metrics_file = self.sample_logs_dir / "amf_metrics.json"

        amf_events = self.parse_amf_logs(amf_log_file)
        upf_flows = self.parse_upf_logs(upf_log_file)
        metrics_snapshots = self.load_amf_metrics(metrics_file)

        self.output_file.parent.mkdir(parents=True, exist_ok=True)

        emitted_count = 0
        written_windows: List[Dict[str, Any]] = []

        # Process each metrics snapshot (represents a 60s window for a specific slice)
        for snap in metrics_snapshots:
            start_dt = parse_iso_timestamp(snap["timestamp"])
            duration = snap.get("duration_sec", 60)
            end_dt = start_dt + timedelta(seconds=duration)
            slice_id = snap["slice_id"]
            nf_id = snap.get("nf_id", "AMF-01")

            # Filter relevant events and flows inside this window and slice
            win_amf_events = [
                e for e in amf_events
                if e["slice_id"] == slice_id and start_dt <= e["timestamp"] < end_dt
            ]
            win_upf_flows = [
                f for f in upf_flows
                if f["slice_id"] == slice_id and start_dt <= f["timestamp"] < end_dt
            ]

            active_raw_imsis = set()
            for e in win_amf_events:
                if e["raw_imsi"]:
                    active_raw_imsis.add(e["raw_imsi"])
            for f in win_upf_flows:
                if f["raw_imsi"]:
                    active_raw_imsis.add(f["raw_imsi"])

            active_ue_count = max(len(active_raw_imsis), snap.get("active_ue_count", 1))

            # Raw Counters
            tot_pkts = snap.get("total_packets", sum(f["packets_ul"] + f["packets_dl"] for f in win_upf_flows))
            bytes_ul = snap.get("total_bytes_uplink", sum(f["bytes_ul"] for f in win_upf_flows))
            bytes_dl = snap.get("total_bytes_downlink", sum(f["bytes_dl"] for f in win_upf_flows))
            reg_att = snap.get("registration_attempts", max(1, sum(1 for e in win_amf_events if "registration" in e["msg"].lower())))
            reg_fail = snap.get("registration_failures", sum(1 for e in win_amf_events if e["is_failure"]))
            pdu_estab = snap.get("pdu_sessions_established", active_ue_count)
            nas_tot = snap.get("nas_messages_total", max(active_ue_count * 10, len(win_amf_events)))
            nas_fail = snap.get("nas_failures", reg_fail)
            pfcp_msgs = snap.get("pfcp_association_messages", active_ue_count * 2)
            pfcp_fail = snap.get("pfcp_failures", 0)
            gtpu_teids = snap.get("gtpu_teid_count", active_ue_count)

            raw_counters = {
                "active_ue_count": active_ue_count,
                "total_packets": tot_pkts,
                "total_bytes_uplink": bytes_ul,
                "total_bytes_downlink": bytes_dl,
                "registration_attempts": reg_att,
                "registration_failures": reg_fail,
                "pdu_sessions_established": pdu_estab,
                "nas_messages_total": nas_tot,
                "nas_failures": nas_fail,
                "pfcp_association_messages": pfcp_msgs,
                "pfcp_failures": pfcp_fail,
                "gtpu_teid_count": gtpu_teids,
            }

            # Ratio Features
            tot_bytes = max(1, bytes_ul + bytes_dl)
            reg_per_ue = round(reg_att / float(max(1, active_ue_count)), 4)
            nas_fail_ratio = round(nas_fail / float(max(1, nas_tot)), 4)
            pfcp_fail_ratio = round(pfcp_fail / float(max(1, pfcp_msgs)), 4)
            pdu_rate = round(pdu_estab / float(max(1, active_ue_count)), 4)
            b_per_sess = round(tot_bytes / float(max(1, pdu_estab)), 2)
            p_per_sess = round(tot_pkts / float(max(1, pdu_estab)), 2)
            gtpu_vol_ue = round(tot_bytes / float(max(1, active_ue_count)), 2)

            # Shannon entropy of active hashed UE traffic distribution
            if len(active_raw_imsis) > 1:
                ue_counts = [1 for _ in active_raw_imsis]
                tot_c = float(len(ue_counts))
                entropy = -sum((c / tot_c) * math.log2(c / tot_c) for c in ue_counts)
            else:
                entropy = 0.0

            ratio_features = {
                "registrations_per_active_ue": reg_per_ue,
                "nas_failure_ratio": nas_fail_ratio,
                "pfcp_failure_ratio": pfcp_fail_ratio,
                "pdu_session_rate_per_ue": pdu_rate,
                "bytes_per_session": b_per_sess,
                "packets_per_session": p_per_sess,
                "gtpu_volume_per_ue": gtpu_vol_ue,
                "ue_hash_entropy": round(entropy, 4),
                "new_ue_rate": round(reg_att / float(max(1, active_ue_count)), 4),
            }

            # Composition Vector (signaling distribution)
            tot_sig = float(max(1, reg_att + pdu_estab + nas_fail + pfcp_msgs))
            composition_vector = {
                "registration_ratio": round(reg_att / tot_sig, 4),
                "session_setup_ratio": round(pdu_estab / tot_sig, 4),
                "failure_ratio": round((nas_fail + reg_fail + pfcp_fail) / tot_sig, 4),
                "other_signalling_ratio": round(pfcp_msgs / tot_sig, 4),
            }

            # Device classes
            dev_classes = snap.get("device_classes", {})
            device_count_by_class = {
                "sensor": dev_classes.get("sensor", active_ue_count if "030405" in slice_id else 0),
                "camera": dev_classes.get("camera", active_ue_count if "010203" in slice_id else 0),
                "AGV": dev_classes.get("AGV", active_ue_count if "020304" in slice_id else 0),
            }

            # Ground truth
            ground_truth = {
                "is_attack": False,
                "label": "benign",
                "attack_type": None,
            }

            # 1. Emit Slice-Level Canonical Window
            slice_window = {
                "source": "lab",
                "window_id": str(uuid.uuid4()),
                "slice_id": slice_id,
                "nf_id": nf_id,
                "window_start": start_dt.isoformat(),
                "window_end": end_dt.isoformat(),
                "duration_sec": duration,
                "raw_counters": raw_counters,
                "ratio_features": ratio_features,
                "composition_vector": composition_vector,
                "ground_truth": ground_truth,
                "device_count_by_class": device_count_by_class,
            }

            validate_slice_window(slice_window)
            written_windows.append(slice_window)
            emitted_count += 1

            # 2. Emit Per-Device Canonical Windows for each active UE in this window
            target_class = SLICE_CLASS_MAP.get(slice_id, "sensor")
            for raw_ue in active_raw_imsis:
                h_id = self._hash_imsi(raw_ue)
                ue_flows = [f for f in win_upf_flows if f["raw_imsi"] == raw_ue]
                ue_pkts_ul = sum(f["packets_ul"] for f in ue_flows) or (tot_pkts // max(1, active_ue_count))
                ue_pkts_dl = sum(f["packets_dl"] for f in ue_flows) or (tot_pkts // max(1, active_ue_count * 10))
                ue_tot_pkts = max(1, ue_pkts_ul + ue_pkts_dl)
                ue_bytes_ul = sum(f["bytes_ul"] for f in ue_flows) or (bytes_ul // max(1, active_ue_count))
                ue_bytes_dl = sum(f["bytes_dl"] for f in ue_flows) or (bytes_dl // max(1, active_ue_count))
                ue_tot_bytes = max(1, ue_bytes_ul + ue_bytes_dl)

                ue_events = [e for e in win_amf_events if e["raw_imsi"] == raw_ue]
                msg_cnt = max(1, len(ue_events))
                fail_cnt = sum(1 for e in ue_events if e["is_failure"])

                dev_window = {
                    "source": "lab",
                    "window_id": str(uuid.uuid4()),
                    "device_id_hash": h_id,
                    "device_class": target_class,
                    "slice_id": slice_id,
                    "window_start": start_dt.isoformat(),
                    "window_end": end_dt.isoformat(),
                    "duration_sec": duration,
                    "rate_features": {
                        "packets_per_sec": round(ue_tot_pkts / float(duration), 4),
                        "bytes_uplink_per_sec": round(ue_bytes_ul / float(duration), 2),
                        "bytes_downlink_per_sec": round(ue_bytes_dl / float(duration), 2),
                        "events_per_sec": round(msg_cnt / float(duration), 4),
                    },
                    "ratio_features": {
                        "bytes_per_packet": round(ue_tot_bytes / float(ue_tot_pkts), 2),
                        "uplink_byte_ratio": round(ue_bytes_ul / float(ue_tot_bytes), 4),
                        "failure_ratio": round(fail_cnt / float(msg_cnt), 6),
                    },
                    "raw_counters": {
                        "total_packets": ue_tot_pkts,
                        "packets_uplink": ue_pkts_ul,
                        "packets_downlink": ue_pkts_dl,
                        "total_bytes_uplink": ue_bytes_ul,
                        "total_bytes_downlink": ue_bytes_dl,
                        "message_count": msg_cnt,
                        "failure_count": fail_cnt,
                    },
                    "provisioning_status": {
                        "is_provisioned": True,
                        "event_id": None,
                    },
                    "ground_truth": {
                        "is_attack": False,
                        "label": "benign",
                        "attack_type": None,
                    },
                }

                validate_device_window(dev_window)
                written_windows.append(dev_window)
                emitted_count += 1

        # Write to output file data/lab/windows.jsonl
        with open(self.output_file, "w", encoding="utf-8", newline="\n") as f:
            for win in written_windows:
                f.write(json.dumps(win) + "\n")

        return emitted_count


def main():
    parser = argparse.ArgumentParser(description="Open5GS & AMF Metrics Lab Adapter")
    parser.add_argument(
        "--sample-logs-dir",
        type=Path,
        default=ROOT / "lab" / "sample_logs",
        help="Path to directory containing sample Open5GS logs and metrics",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "data" / "lab" / "windows.jsonl",
        help="Destination path for canonical windows (default: data/lab/windows.jsonl)",
    )
    args = parser.parse_args()

    adapter = LabAdapter(sample_logs_dir=args.sample_logs_dir, output_file=args.output)
    count = adapter.process_and_emit()
    print(f"Successfully processed lab telemetry. Emitted {count} validated canonical windows to {args.output}")


if __name__ == "__main__":
    main()
