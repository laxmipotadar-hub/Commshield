"""Deterministic synthetic 5G core telemetry generator.

Simulates per-second 5G Core counters (AMF, SMF, UPF) across network slices (eMBB, URLLC, mMTC)
with realistic diurnal waves, noise, organic proportional growth, and stealth attacks.
"""

from datetime import datetime, timedelta, timezone
import json
import math
from pathlib import Path
import random
from typing import Any, Dict, List, Optional

from .adapters.synthetic import SyntheticAdapter


SLICE_PROFILES: Dict[str, Dict[str, Any]] = {
    "eMBB": {
        "slice_id": "sst-1-sd-010203",
        "nf_id": "UPF-01",
        "base_ues": 1400,
        "base_pdu_per_ue": 0.99,
        "base_bytes_per_ue": 730000,
        "uplink_ratio": 0.15,
        "nas_rate_per_sec": 7.5,
        "nas_fail_rate": 0.004,
        "pfcp_rate_per_sec": 1.4,
        "pfcp_fail_rate": 0.001,
        "ue_entropy_mean": 7.42,
    },
    "URLLC": {
        "slice_id": "sst-2-sd-020304",
        "nf_id": "UPF-02",
        "base_ues": 350,
        "base_pdu_per_ue": 1.0,
        "base_bytes_per_ue": 120000,
        "uplink_ratio": 0.45,
        "nas_rate_per_sec": 3.0,
        "nas_fail_rate": 0.0005,
        "pfcp_rate_per_sec": 4.5,
        "pfcp_fail_rate": 0.0001,
        "ue_entropy_mean": 6.85,
    },
    "mMTC": {
        "slice_id": "sst-3-sd-030405",
        "nf_id": "UPF-03",
        "base_ues": 8500,
        "base_pdu_per_ue": 0.95,
        "base_bytes_per_ue": 45000,
        "uplink_ratio": 0.85,
        "nas_rate_per_sec": 25.0,
        "nas_fail_rate": 0.008,
        "pfcp_rate_per_sec": 5.0,
        "pfcp_fail_rate": 0.002,
        "ue_entropy_mean": 9.15,
    },
}


class SyntheticGenerator:
    """Deterministic, seeded synthetic 5G telemetry generator."""

    def __init__(self, seed: int = 42):
        self.seed = seed
        self.rng = random.Random(seed)
        self.adapter = SyntheticAdapter()

    def _get_diurnal_factor(self, second_of_day: int) -> float:
        """Realistic diurnal day/night traffic wave."""
        # Minimum at 04:00 (factor ~0.7), peak at 16:00 (factor ~1.3)
        angle = 2.0 * math.pi * ((second_of_day - 14400) / 86400.0)
        return 1.0 + 0.3 * math.sin(angle)

    def generate_raw_second(
        self,
        slice_name: str,
        timestamp: datetime,
        scale_k: float = 1.0,
        attack_intensity: float = 0.0,
        attack_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Generate counters for a single 1-second interval."""
        prof = SLICE_PROFILES[slice_name]
        sec_of_day = (timestamp.hour * 3600) + (timestamp.minute * 60) + timestamp.second
        diurnal = self._get_diurnal_factor(sec_of_day)

        noise = self.rng.gauss(1.0, 0.03)
        combined_scale = max(0.2, scale_k * diurnal * noise)

        # Baseline proportional scaling
        active_ues = int(prof["base_ues"] * combined_scale)
        pdu_established = int(active_ues * prof["base_pdu_per_ue"] * self.rng.uniform(0.98, 1.02))
        
        # Bytes volume
        total_bytes = int(active_ues * (prof["base_bytes_per_ue"] / 60.0) * self.rng.uniform(0.95, 1.05))
        ul_ratio = prof["uplink_ratio"]
        ul_bytes = int(total_bytes * ul_ratio)
        dl_bytes = total_bytes - ul_bytes
        packets = max(1, int(total_bytes / self.rng.uniform(1200, 1500)))

        # Control plane
        reg_attempts = max(1, int((prof["nas_rate_per_sec"] * 0.1) * combined_scale))
        reg_failures = int(reg_attempts * prof["nas_fail_rate"] * self.rng.uniform(0.5, 1.5))

        nas_total = max(1, int(prof["nas_rate_per_sec"] * combined_scale))
        nas_failures = int(nas_total * prof["nas_fail_rate"])

        pfcp_total = max(1, int(prof["pfcp_rate_per_sec"] * combined_scale))
        pfcp_failures = int(pfcp_total * prof["pfcp_fail_rate"])

        ue_entropy = prof["ue_entropy_mean"] + self.rng.gauss(0.0, 0.05)
        new_ues = max(0, int(active_ues * 0.001 * self.rng.uniform(0.8, 1.2)))

        is_attack = attack_intensity > 0.0

        # Inject attack modifications if active
        if is_attack:
            if attack_type == "slow_attack_ramp":
                # Gradual failure ramp and entropy drop
                nas_failures += int(nas_total * (0.05 + 0.35 * attack_intensity))
                reg_failures += int(reg_attempts * (0.05 + 0.25 * attack_intensity))
                pfcp_failures += int(pfcp_total * (0.02 + 0.15 * attack_intensity))
                ue_entropy = max(2.0, ue_entropy - (2.5 * attack_intensity))
            elif attack_type == "mimicry_attack":
                # Perfectly mimics ratio composition, but volume surges with unauthenticated sessions
                extra_vol = int(total_bytes * (0.5 + 1.5 * attack_intensity))
                ul_bytes += int(extra_vol * ul_ratio)
                dl_bytes += extra_vol - int(extra_vol * ul_ratio)
                packets += int(extra_vol / 1400)
                # Subtle entropy reduction
                ue_entropy = max(4.0, ue_entropy - (0.8 * attack_intensity))
            elif attack_type == "attack_in_growth":
                # Hidden inside legitimate growth
                nas_failures += int(nas_total * (0.04 + 0.20 * attack_intensity))
                ue_entropy = max(3.5, ue_entropy - (1.8 * attack_intensity))

        return {
            "timestamp": timestamp,
            "active_ue_count": active_ues,
            "registration_attempts": reg_attempts,
            "registration_failures": reg_failures,
            "pdu_sessions_established": pdu_established,
            "nas_messages_total": nas_total,
            "nas_failures": nas_failures,
            "pfcp_association_messages": pfcp_total,
            "pfcp_failures": pfcp_failures,
            "total_bytes_uplink": ul_bytes,
            "total_bytes_downlink": dl_bytes,
            "total_packets": packets,
            "gtpu_teid_count": pdu_established,
            "new_ue_count": new_ues,
            "ue_hash_entropy": ue_entropy,
            "ground_truth": {
                "is_attack": is_attack,
                "attack_type": attack_type if is_attack else None,
                "is_growth": scale_k > 1.05,
                "scale_factor_k": round(scale_k, 2),
            },
        }

    def generate_scenario_windows(
        self,
        scenario_name: str,
        slice_name: str = "eMBB",
        num_windows: int = 60,
        window_duration_sec: int = 60,
        start_time: Optional[datetime] = None,
    ) -> List[Dict[str, Any]]:
        """Generate a complete series of canonical windows for a scenario."""
        if start_time is None:
            start_time = datetime(2026, 11, 15, 8, 0, 0, tzinfo=timezone.utc)

        prof = SLICE_PROFILES[slice_name]
        slice_id = prof["slice_id"]
        nf_id = prof["nf_id"]

        all_windows: List[Dict[str, Any]] = []
        current_time = start_time

        for w_idx in range(num_windows):
            window_start = current_time
            window_end = window_start + timedelta(seconds=window_duration_sec)

            # Determine scenario dynamics for this window
            scale_k = 1.0
            attack_intensity = 0.0
            attack_type = None

            progress = w_idx / max(num_windows - 1, 1)

            if scenario_name == "stable_benign":
                scale_k = 1.0
            elif scenario_name == "legitimate_growth":
                # Growth factor increases smoothly from 1.0 to 2.8
                scale_k = 1.0 + 1.8 * (w_idx / max(num_windows, 1))
            elif scenario_name == "slow_attack_ramp":
                # First 30% clean, next 70% ramps attack
                if progress >= 0.30:
                    ramp_prog = (progress - 0.30) / 0.70
                    attack_intensity = min(1.0, ramp_prog)
                    attack_type = "slow_attack_ramp"
            elif scenario_name == "attack_in_growth":
                # Growth occurs throughout
                scale_k = 1.0 + 1.5 * progress
                # Attack injected starting at 40%
                if progress >= 0.40:
                    ramp_prog = (progress - 0.40) / 0.60
                    attack_intensity = min(1.0, ramp_prog)
                    attack_type = "attack_in_growth"
            elif scenario_name == "mimicry_attack":
                # Attack active in middle window segment [35% - 85%]
                if 0.35 <= progress <= 0.85:
                    attack_intensity = 0.85
                    attack_type = "mimicry_attack"
            elif scenario_name == "clean_training":
                scale_k = 1.0

            # Generate per-second events in this window
            second_events: List[Dict[str, Any]] = []
            for s in range(window_duration_sec):
                sec_time = window_start + timedelta(seconds=s)
                sec_event = self.generate_raw_second(
                    slice_name=slice_name,
                    timestamp=sec_time,
                    scale_k=scale_k,
                    attack_intensity=attack_intensity,
                    attack_type=attack_type,
                )
                second_events.append(sec_event)

            # Aggregate into canonical window
            window = self.adapter.aggregate_window(
                events=second_events,
                slice_id=slice_id,
                nf_id=nf_id,
                window_duration_sec=window_duration_sec,
                window_start=window_start,
                window_end=window_end,
            )
            all_windows.append(window)
            current_time = window_end

        return all_windows


def generate_and_save_all_scenarios(
    output_dir: str = "data/synthetic",
    seed: int = 42,
    num_windows: int = 60,
    window_duration_sec: int = 60,
) -> Dict[str, Any]:
    """Generates all 5 core scenarios and training sets, saving files and metadata.json."""
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    generator = SyntheticGenerator(seed=seed)

    scenarios = [
        "stable_benign",
        "legitimate_growth",
        "slow_attack_ramp",
        "attack_in_growth",
        "mimicry_attack",
    ]

    metadata: Dict[str, Any] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "seed": seed,
        "window_duration_sec": window_duration_sec,
        "scenarios": {},
        "training_periods": {},
    }

    # Generate the 5 core test scenarios
    for sc_name in scenarios:
        windows = generator.generate_scenario_windows(
            scenario_name=sc_name,
            slice_name="eMBB",
            num_windows=num_windows,
            window_duration_sec=window_duration_sec,
        )
        file_path = out_path / f"{sc_name}.json"
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump({"scenario": sc_name, "windows": windows}, f, indent=2)

        attack_windows_count = sum(1 for w in windows if w["ground_truth"]["is_attack"])
        metadata["scenarios"][sc_name] = {
            "file": file_path.name,
            "slice_id": SLICE_PROFILES["eMBB"]["slice_id"],
            "total_windows": len(windows),
            "attack_windows": attack_windows_count,
            "has_growth": any(w["ground_truth"]["is_growth"] for w in windows),
        }

    # Generate clean training periods for all 3 slices
    for slice_key, prof in SLICE_PROFILES.items():
        train_windows = generator.generate_scenario_windows(
            scenario_name="clean_training",
            slice_name=slice_key,
            num_windows=num_windows,
            window_duration_sec=window_duration_sec,
        )
        file_path = out_path / f"training_{slice_key.lower()}.json"
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump({"scenario": "clean_training", "slice": slice_key, "windows": train_windows}, f, indent=2)

        metadata["training_periods"][slice_key] = {
            "file": file_path.name,
            "slice_id": prof["slice_id"],
            "nf_id": prof["nf_id"],
            "total_windows": len(train_windows),
            "attack_windows": 0,
        }

    meta_file = out_path / "metadata.json"
    with open(meta_file, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    return metadata


if __name__ == "__main__":
    generate_and_save_all_scenarios()
