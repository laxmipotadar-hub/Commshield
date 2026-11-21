"""Generate initial digital twin provisioning and change event data."""

from datetime import datetime, timezone
import json
from pathlib import Path
import random

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "twin"
DATA_DIR.mkdir(parents=True, exist_ok=True)


def generate_twin_data(seed: int = 42):
    rng = random.Random(seed)

    classes_config = [
        {"device_class": "sensor", "slice": "sst-3-sd-030405", "count": 100, "prefix": "sim_sensor_"},
        {"device_class": "camera", "slice": "sst-1-sd-010203", "count": 50, "prefix": "sim_camera_"},
        {"device_class": "AGV", "slice": "sst-2-sd-020304", "count": 50, "prefix": "sim_agv_"},
    ]

    sims = []
    sims_by_class = {"sensor": [], "camera": [], "AGV": []}

    base_time = datetime(2026, 11, 1, 0, 0, 0, tzinfo=timezone.utc)

    for cfg in classes_config:
        cls_name = cfg["device_class"]
        slc = cfg["slice"]
        pfx = cfg["prefix"]
        cnt = cfg["count"]
        for i in range(cnt):
            # Generate random 12-character hex suffix (clearly non-IMSI string id)
            rand_hex = f"{rng.getrandbits(48):012x}"
            sim_id = f"{pfx}{rand_hex}"
            sim_record = {
                "sim_id": sim_id,
                "device_class": cls_name,
                "slice": slc,
                "status": "provisioned",
                "provisioned_at": base_time.isoformat(),
            }
            sims.append(sim_record)
            sims_by_class[cls_name].append(sim_id)

    # Change events (onboarding batches)
    # Batch 1: 30 sensors onboarded between 08:10 and 08:35 UTC
    # Batch 2: 20 cameras onboarded between 08:20 and 08:50 UTC
    # Batch 3: 15 AGVs onboarded between 09:00 and 09:30 UTC
    batches = [
        {
            "batch_id": "BATCH-OB-20261115-01",
            "start": "2026-11-15T08:10:00Z",
            "end": "2026-11-15T08:35:00Z",
            "count": 30,
            "slice": "sst-3-sd-030405",
            "device_class": "sensor",
            "sim_ids": sims_by_class["sensor"][:30],
        },
        {
            "batch_id": "BATCH-OB-20261115-02",
            "start": "2026-11-15T08:20:00Z",
            "end": "2026-11-15T08:50:00Z",
            "count": 20,
            "slice": "sst-1-sd-010203",
            "device_class": "camera",
            "sim_ids": sims_by_class["camera"][:20],
        },
        {
            "batch_id": "BATCH-OB-20261115-03",
            "start": "2026-11-15T09:00:00Z",
            "end": "2026-11-15T09:30:00Z",
            "count": 15,
            "slice": "sst-2-sd-020304",
            "device_class": "AGV",
            "sim_ids": sims_by_class["AGV"][:15],
        },
    ]

    prov_file = DATA_DIR / "provisioning.json"
    with open(prov_file, "w", encoding="utf-8", newline="\n") as f:
        json.dump({"total_sims": len(sims), "sims": sims}, f, indent=2)

    events_file = DATA_DIR / "change_events.json"
    with open(events_file, "w", encoding="utf-8", newline="\n") as f:
        json.dump({"total_batches": len(batches), "batches": batches}, f, indent=2)

    print(f"Generated {len(sims)} SIMs in {prov_file}")
    print(f"Generated {len(batches)} batches in {events_file}")


if __name__ == "__main__":
    generate_twin_data()
