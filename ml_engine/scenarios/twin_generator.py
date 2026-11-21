"""Deterministic Digital Twin Scenario Telemetry Generator.

Generates slice-level and per-device canonical windows across four labelled streams:
(a) approved_onboarding
(b) unprovisioned_burst
(c) provisioned_burst_no_event
(d) slow_ramp_in_onboarding

Enforces strict HMAC-SHA256 pseudonymisation so that no raw SIM identifiers ever escape.
"""

from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import math
from pathlib import Path
import random
from typing import Any, Dict, List, Optional, Set, Tuple, Union
import uuid

from ml_engine.provisioning.loader import ProvisioningLoader, hash_sim_id
from ml_engine.provisioning.schema import (
    validate_slice_window,
    validate_device_window,
    VALID_SOURCES,
    VALID_DEVICE_CLASSES,
)

# Seeds configuration: strict separation of tuning and test seeds
TUNING_SEED: int = 42
TEST_SEEDS: List[int] = [101, 102, 103, 104, 105, 106, 107, 108, 109, 110]

STREAM_NAMES: List[str] = [
    "approved_onboarding",
    "unprovisioned_burst",
    "provisioned_burst_no_event",
    "slow_ramp_in_onboarding",
]

# Per-device-class baseline rate distributions
DEVICE_CLASS_PROFILES: Dict[str, Dict[str, Any]] = {
    "sensor": {
        "slice_id": "sst-3-sd-030405",
        "nf_id": "UPF-03",
        "mean_packets_per_sec": 0.25,      # ~15 packets / 60s
        "std_packets_per_sec": 0.05,
        "mean_bytes_per_packet": 128.0,
        "uplink_ratio": 0.90,
        "mean_events_per_sec": 0.25,
        "failure_rate": 0.002,
    },
    "camera": {
        "slice_id": "sst-1-sd-010203",
        "nf_id": "UPF-01",
        "mean_packets_per_sec": 40.0,       # ~2400 packets / 60s
        "std_packets_per_sec": 4.0,
        "mean_bytes_per_packet": 1250.0,
        "uplink_ratio": 0.95,
        "mean_events_per_sec": 5.0,
        "failure_rate": 0.001,
    },
    "AGV": {
        "slice_id": "sst-2-sd-020304",
        "nf_id": "UPF-02",
        "mean_packets_per_sec": 15.0,       # ~900 packets / 60s
        "std_packets_per_sec": 1.5,
        "mean_bytes_per_packet": 380.0,
        "uplink_ratio": 0.55,
        "mean_events_per_sec": 15.0,
        "failure_rate": 0.0002,
    },
}

SLICE_TO_NF: Dict[str, str] = {
    "sst-1-sd-010203": "UPF-01",
    "sst-2-sd-020304": "UPF-02",
    "sst-3-sd-030405": "UPF-03",
}


class TwinScenarioGenerator:
    """Deterministic generator for Digital Twin slice and per-device canonical windows."""

    def __init__(
        self,
        seed: int = 42,
        loader: Optional[ProvisioningLoader] = None,
        source: str = "simulated_twin",
    ):
        self.seed = seed
        self.rng = random.Random(seed)
        self.source = source
        if self.source not in VALID_SOURCES:
            raise ValueError(f"Invalid source: {self.source}")

        self.loader = loader or ProvisioningLoader()

        # Partition provisioned SIMs by class (using hashed IDs only)
        self.sensors_hashed = self.loader.get_hashed_ids_for_class("sensor")
        self.cameras_hashed = self.loader.get_hashed_ids_for_class("camera")
        self.agvs_hashed = self.loader.get_hashed_ids_for_class("AGV")

        # Nominal active subsets (baseline pre-onboarding)
        self.base_sensors = self.sensors_hashed[:40]
        self.base_cameras = self.cameras_hashed[:20]
        self.base_agvs = self.agvs_hashed[:20]

        # Onboarding candidates (from batches)
        self.onboard_sensors = self.sensors_hashed[40:70]  # 30 sensors for Batch 1
        self.onboard_cameras = self.cameras_hashed[20:40]  # 20 cameras for Batch 2

        # Generate deterministic synthetic unprovisioned IDs for attack stream
        self.unprovisioned_hashed: List[str] = []
        unprov_rng = random.Random(seed + 9999)
        for i in range(30):
            fake_raw = f"unprov_rogue_sim_{unprov_rng.getrandbits(48):012x}"
            self.unprovisioned_hashed.append(hash_sim_id(fake_raw))

    def _generate_device_window(
        self,
        device_id_hash: str,
        device_class: str,
        slice_id: str,
        window_start: datetime,
        window_end: datetime,
        duration_sec: int,
        is_attack: bool,
        attack_type: Optional[str] = None,
        rate_multiplier: float = 1.0,
        fail_multiplier: float = 1.0,
    ) -> Dict[str, Any]:
        """Generate a single per-device canonical window."""
        prof = DEVICE_CLASS_PROFILES[device_class]

        pkt_rate = max(0.01, self.rng.gauss(prof["mean_packets_per_sec"], prof["std_packets_per_sec"]) * rate_multiplier)
        total_packets = max(1, int(round(pkt_rate * duration_sec)))

        ul_ratio = min(0.99, max(0.01, prof["uplink_ratio"] + self.rng.gauss(0.0, 0.02)))
        packets_ul = max(1, int(round(total_packets * ul_ratio)))
        packets_dl = max(0, total_packets - packets_ul)

        b_per_pkt = max(40.0, prof["mean_bytes_per_packet"] * self.rng.uniform(0.95, 1.05))
        total_bytes = int(round(total_packets * b_per_pkt))
        bytes_ul = int(round(total_bytes * ul_ratio))
        bytes_dl = max(0, total_bytes - bytes_ul)

        ev_rate = max(0.01, prof["mean_events_per_sec"] * rate_multiplier)
        msg_count = max(1, int(round(ev_rate * duration_sec)))

        base_fail_rate = min(0.95, prof["failure_rate"] * fail_multiplier)
        if is_attack and attack_type == "slow_ramp_in_onboarding":
            base_fail_rate = min(0.40, base_fail_rate + 0.15 * fail_multiplier)
        fail_count = int(self.rng.binomialvariate(msg_count, min(1.0, base_fail_rate))) if hasattr(self.rng, "binomialvariate") else int(msg_count * base_fail_rate)

        # Lookup provisioning info
        prov_info = self.loader.lookup(device_id_hash, window_start)

        label = "attack" if is_attack else "benign"

        dev_window = {
            "source": self.source,
            "window_id": str(uuid.uuid4()),
            "device_id_hash": device_id_hash,
            "device_class": device_class,
            "slice_id": slice_id,
            "window_start": window_start.isoformat(),
            "window_end": window_end.isoformat(),
            "duration_sec": duration_sec,
            "rate_features": {
                "packets_per_sec": round(total_packets / float(duration_sec), 4),
                "bytes_uplink_per_sec": round(bytes_ul / float(duration_sec), 2),
                "bytes_downlink_per_sec": round(bytes_dl / float(duration_sec), 2),
                "events_per_sec": round(msg_count / float(duration_sec), 4),
            },
            "ratio_features": {
                "bytes_per_packet": round(total_bytes / float(total_packets), 2),
                "uplink_byte_ratio": round(bytes_ul / float(max(1, total_bytes)), 4),
                "failure_ratio": round(fail_count / float(max(1, msg_count)), 6),
            },
            "raw_counters": {
                "total_packets": total_packets,
                "packets_uplink": packets_ul,
                "packets_downlink": packets_dl,
                "total_bytes_uplink": bytes_ul,
                "total_bytes_downlink": bytes_dl,
                "message_count": msg_count,
                "failure_count": fail_count,
            },
            "provisioning_status": {
                "is_provisioned": prov_info["provisioned"],
                "event_id": prov_info["event_id"],
            },
            "ground_truth": {
                "is_attack": is_attack,
                "label": label,
                "attack_type": attack_type if is_attack else None,
            },
        }

        validate_device_window(dev_window)
        return dev_window

    def _aggregate_slice_window(
        self,
        slice_id: str,
        window_start: datetime,
        window_end: datetime,
        duration_sec: int,
        device_windows: List[Dict[str, Any]],
        is_attack: bool,
        attack_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Aggregate per-device telemetry into a slice-level canonical window."""
        nf_id = SLICE_TO_NF.get(slice_id, "UPF-01")

        active_ues = len(device_windows)
        total_packets = sum(w["raw_counters"]["total_packets"] for w in device_windows)
        bytes_ul = sum(w["raw_counters"]["total_bytes_uplink"] for w in device_windows)
        bytes_dl = sum(w["raw_counters"]["total_bytes_downlink"] for w in device_windows)
        total_msgs = sum(w["raw_counters"]["message_count"] for w in device_windows)
        total_failures = sum(w["raw_counters"]["failure_count"] for w in device_windows)

        # 3GPP counters
        reg_attempts = max(1, int(active_ues * 0.12 * self.rng.uniform(0.9, 1.1)))
        reg_failures = max(0, int(reg_attempts * (0.01 if not is_attack else 0.08)))
        pdu_established = max(1, int(active_ues * 0.98))
        nas_total = max(1, total_msgs)
        nas_failures = total_failures
        pfcp_total = max(1, int(active_ues * 0.45 * self.rng.uniform(0.95, 1.05)))
        pfcp_failures = max(0, int(pfcp_total * (0.001 if not is_attack else 0.04)))

        # Device counts by class in this slice
        dev_counts = {"sensor": 0, "camera": 0, "AGV": 0}
        for w in device_windows:
            cls = w["device_class"]
            if cls in dev_counts:
                dev_counts[cls] += 1

        # Entropy calculation over device traffic distribution
        if active_ues > 1:
            pkt_counts = [w["raw_counters"]["total_packets"] for w in device_windows]
            sum_pkts = float(max(1, sum(pkt_counts)))
            entropy = -sum((p / sum_pkts) * math.log2(p / sum_pkts) for p in pkt_counts if p > 0)
        else:
            entropy = 0.0

        label = "attack" if is_attack else "benign"

        raw_counters = {
            "active_ue_count": active_ues,
            "total_packets": total_packets,
            "total_bytes_uplink": bytes_ul,
            "total_bytes_downlink": bytes_dl,
            "registration_attempts": reg_attempts,
            "registration_failures": reg_failures,
            "pdu_sessions_established": pdu_established,
            "nas_messages_total": nas_total,
            "nas_failures": nas_failures,
            "pfcp_association_messages": pfcp_total,
            "pfcp_failures": pfcp_failures,
            "gtpu_teid_count": pdu_established,
        }

        ratio_features = {
            "registrations_per_active_ue": round(reg_attempts / float(max(1, active_ues)), 4),
            "nas_failure_ratio": round(nas_failures / float(max(1, nas_total)), 4),
            "pfcp_failure_ratio": round(pfcp_failures / float(max(1, pfcp_total)), 4),
            "pdu_session_rate_per_ue": round(pdu_established / float(max(1, active_ues)), 4),
            "bytes_per_session": round((bytes_ul + bytes_dl) / float(max(1, pdu_established)), 2),
            "packets_per_session": round(total_packets / float(max(1, pdu_established)), 2),
            "gtpu_volume_per_ue": round((bytes_ul + bytes_dl) / float(max(1, active_ues)), 2),
            "ue_hash_entropy": round(entropy, 4),
            "new_ue_rate": round(0.02 if not is_attack else 0.25, 4),
        }

        tot_sig = float(max(1, reg_attempts + pdu_established + nas_failures + pfcp_total))
        composition_vector = {
            "registration_ratio": round(reg_attempts / tot_sig, 4),
            "session_setup_ratio": round(pdu_established / tot_sig, 4),
            "failure_ratio": round((nas_failures + reg_failures + pfcp_failures) / tot_sig, 4),
            "other_signalling_ratio": round(pfcp_total / tot_sig, 4),
        }

        slice_window = {
            "source": self.source,
            "window_id": str(uuid.uuid4()),
            "slice_id": slice_id,
            "nf_id": nf_id,
            "window_start": window_start.isoformat(),
            "window_end": window_end.isoformat(),
            "duration_sec": duration_sec,
            "raw_counters": raw_counters,
            "ratio_features": ratio_features,
            "composition_vector": composition_vector,
            "ground_truth": {
                "is_attack": is_attack,
                "label": label,
                "attack_type": attack_type if is_attack else None,
            },
            "device_count_by_class": dev_counts,
        }

        validate_slice_window(slice_window)
        return slice_window

    def generate_stream(
        self,
        stream_name: str,
        num_windows: int = 30,
        window_duration_sec: int = 60,
        start_time: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """Generate a complete labelled stream with slice-level and per-device windows."""
        if stream_name not in STREAM_NAMES:
            raise ValueError(f"Unknown stream_name '{stream_name}'. Must be one of {STREAM_NAMES}")

        if start_time is None:
            # Anchor start at 2026-11-15 08:00:00 UTC
            start_time = datetime(2026, 11, 15, 8, 0, 0, tzinfo=timezone.utc)

        slice_windows: List[Dict[str, Any]] = []
        device_windows: List[Dict[str, Any]] = []

        window_counts_by_class = {"sensor": 0, "camera": 0, "AGV": 0}

        cur_time = start_time

        for w_idx in range(num_windows):
            w_start = cur_time
            w_end = w_start + timedelta(seconds=window_duration_sec)

            # Active devices for this window
            active_devices: List[Tuple[str, str, str, bool, Optional[str], float, float]] = []
            # tuple: (hashed_id, class, slice, is_dev_attack, dev_attack_type, rate_mult, fail_mult)

            # Determine scenario dynamics for this window
            is_slice_attack = False
            stream_attack_type = None

            if stream_name == "approved_onboarding":
                # Clean approved onboarding: 100% benign
                # Windows 0-9: Baseline active
                # Windows 10-24: Batch 1 sensors join (time matches BATCH-OB-20261115-01)
                # Windows 20-29: Batch 2 cameras join (time matches BATCH-OB-20261115-02)
                is_slice_attack = False
                stream_attack_type = None

                for hid in self.base_sensors:
                    active_devices.append((hid, "sensor", "sst-3-sd-030405", False, None, 1.0, 1.0))
                for hid in self.base_cameras:
                    active_devices.append((hid, "camera", "sst-1-sd-010203", False, None, 1.0, 1.0))
                for hid in self.base_agvs:
                    active_devices.append((hid, "AGV", "sst-2-sd-020304", False, None, 1.0, 1.0))

                if w_idx >= 10:
                    for hid in self.onboard_sensors:
                        active_devices.append((hid, "sensor", "sst-3-sd-030405", False, None, 1.0, 1.0))
                if w_idx >= 20:
                    for hid in self.onboard_cameras:
                        active_devices.append((hid, "camera", "sst-1-sd-010203", False, None, 1.0, 1.0))

            elif stream_name == "unprovisioned_burst":
                # Windows 0-9: Benign baseline
                # Windows 10-24: Unprovisioned IDs burst into mMTC and eMBB slices (Attack)
                # Windows 25-29: Post-attack recovery (Benign)
                for hid in self.base_sensors:
                    active_devices.append((hid, "sensor", "sst-3-sd-030405", False, None, 1.0, 1.0))
                for hid in self.base_cameras:
                    active_devices.append((hid, "camera", "sst-1-sd-010203", False, None, 1.0, 1.0))
                for hid in self.base_agvs:
                    active_devices.append((hid, "AGV", "sst-2-sd-020304", False, None, 1.0, 1.0))

                if 10 <= w_idx <= 24:
                    is_slice_attack = True
                    stream_attack_type = "unprovisioned_burst"
                    for unprov_hid in self.unprovisioned_hashed:
                        # Unprovisioned devices burst at 4x rate and high failure
                        active_devices.append((
                            unprov_hid,
                            "sensor",
                            "sst-3-sd-030405",
                            True,
                            "unprovisioned_burst",
                            4.5,
                            12.0,
                        ))

            elif stream_name == "provisioned_burst_no_event":
                # Windows 0-9: Benign baseline
                # Windows 10-24: Provisioned SIMs burst without any scheduled event (Attack)
                # Windows 25-29: Benign baseline
                for hid in self.base_sensors:
                    active_devices.append((hid, "sensor", "sst-3-sd-030405", False, None, 1.0, 1.0))

                if 10 <= w_idx <= 24:
                    is_slice_attack = True
                    stream_attack_type = "provisioned_burst_no_event"
                    # Provisioned cameras suddenly surge 6x
                    for hid in self.base_cameras:
                        active_devices.append((
                            hid,
                            "camera",
                            "sst-1-sd-010203",
                            True,
                            "provisioned_burst_no_event",
                            6.0,
                            5.0,
                        ))
                else:
                    for hid in self.base_cameras:
                        active_devices.append((hid, "camera", "sst-1-sd-010203", False, None, 1.0, 1.0))

                for hid in self.base_agvs:
                    active_devices.append((hid, "AGV", "sst-2-sd-020304", False, None, 1.0, 1.0))

            elif stream_name == "slow_ramp_in_onboarding":
                # Windows 0-14: Approved onboarding begins cleanly (Benign)
                # Windows 15-29: A subset of provisioned SIMs slowly ramps anomalous rate/failures inside onboarding (Attack)
                for hid in self.base_cameras:
                    active_devices.append((hid, "camera", "sst-1-sd-010203", False, None, 1.0, 1.0))
                for hid in self.base_agvs:
                    active_devices.append((hid, "AGV", "sst-2-sd-020304", False, None, 1.0, 1.0))

                # Sensors baseline + onboarding
                for hid in self.base_sensors:
                    active_devices.append((hid, "sensor", "sst-3-sd-030405", False, None, 1.0, 1.0))

                if w_idx >= 8:
                    # Legitimate onboarding joined
                    if w_idx >= 15:
                        is_slice_attack = True
                        stream_attack_type = "slow_ramp_in_onboarding"
                        ramp_progress = (w_idx - 15) / 14.0  # 0.0 to 1.0
                        ramp_mult = 1.0 + 3.5 * ramp_progress
                        fail_mult = 1.0 + 8.0 * ramp_progress

                        # First 15 onboarded sensors are normal, second 15 are ramping attack
                        for hid in self.onboard_sensors[:15]:
                            active_devices.append((hid, "sensor", "sst-3-sd-030405", False, None, 1.0, 1.0))
                        for hid in self.onboard_sensors[15:]:
                            active_devices.append((
                                hid,
                                "sensor",
                                "sst-3-sd-030405",
                                True,
                                "slow_ramp_in_onboarding",
                                ramp_mult,
                                fail_mult,
                            ))
                    else:
                        for hid in self.onboard_sensors:
                            active_devices.append((hid, "sensor", "sst-3-sd-030405", False, None, 1.0, 1.0))

            # Generate device windows for this interval
            curr_dev_windows_by_slice: Dict[str, List[Dict[str, Any]]] = {
                "sst-1-sd-010203": [],
                "sst-2-sd-020304": [],
                "sst-3-sd-030405": [],
            }

            for hid, cls_name, slc_id, dev_atk, dev_atk_type, r_mult, f_mult in active_devices:
                dw = self._generate_device_window(
                    device_id_hash=hid,
                    device_class=cls_name,
                    slice_id=slc_id,
                    window_start=w_start,
                    window_end=w_end,
                    duration_sec=window_duration_sec,
                    is_attack=dev_atk,
                    attack_type=dev_atk_type,
                    rate_multiplier=r_mult,
                    fail_multiplier=f_mult,
                )
                device_windows.append(dw)
                curr_dev_windows_by_slice[slc_id].append(dw)
                window_counts_by_class[cls_name] += 1

            # Generate slice-level windows for all active slices
            for slc_id, dev_list in curr_dev_windows_by_slice.items():
                if dev_list:
                    # Slice is attacked if the stream is in attack phase AND this slice contains attack devices
                    slice_has_attack = any(d["ground_truth"]["is_attack"] for d in dev_list) or (is_slice_attack and slc_id in ["sst-3-sd-030405", "sst-1-sd-010203"])
                    sw = self._aggregate_slice_window(
                        slice_id=slc_id,
                        window_start=w_start,
                        window_end=w_end,
                        duration_sec=window_duration_sec,
                        device_windows=dev_list,
                        is_attack=slice_has_attack,
                        attack_type=stream_attack_type if slice_has_attack else None,
                    )
                    slice_windows.append(sw)

            cur_time = w_end

        benign_slice_cnt = sum(1 for w in slice_windows if not w["ground_truth"]["is_attack"])
        attack_slice_cnt = sum(1 for w in slice_windows if w["ground_truth"]["is_attack"])
        benign_dev_cnt = sum(1 for w in device_windows if not w["ground_truth"]["is_attack"])
        attack_dev_cnt = sum(1 for w in device_windows if w["ground_truth"]["is_attack"])

        return {
            "stream_name": stream_name,
            "seed": self.seed,
            "source": self.source,
            "num_windows": num_windows,
            "window_duration_sec": window_duration_sec,
            "total_slice_windows": len(slice_windows),
            "total_device_windows": len(device_windows),
            "slice_windows": slice_windows,
            "device_windows": device_windows,
            "counts": {
                "slice_benign": benign_slice_cnt,
                "slice_attack": attack_slice_cnt,
                "device_benign": benign_dev_cnt,
                "device_attack": attack_dev_cnt,
                "device_by_class": window_counts_by_class,
            },
        }
