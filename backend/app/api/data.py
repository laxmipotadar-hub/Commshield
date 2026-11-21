"""CommShield Data Access and Telemetry Export API.

Provides secure, anonymized data export and preview capabilities:
1. GET /api/data/datasets: lists available datasets with structured metadata block,
   record count, size, seed, config version, source tag, and assigned slice indicator.
2. GET /api/data/{name}/preview?limit=20: returns top 20 windows with hashed IDs and
   aggregates (strictly no raw IPs or payloads).
3. GET /api/data/{name}/download: downloads JSON attachment named
   commshield_<name>_<source>_seed<seed>.json (capped at 20MB) starting with a
   structured "metadata" block.
4. POST /api/data/generate: runs deterministic in-memory generator for one stream
   with seed bounds without altering stored files.
"""

from datetime import datetime, timezone
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import uuid

from fastapi import APIRouter, HTTPException, Query, Response
from pydantic import BaseModel, Field

from ml_engine.preprocessing.adapters.fiveg_nidd import (
    BS1_SLICE_ID,
    FiveGNIDDAdapter,
)
from ml_engine.preprocessing.synthetic_generator import SyntheticGenerator
from ml_engine.scenarios.real_ramp_generator import RealBackboneHiddenRampScenario

logger = logging.getLogger("commshield.api.data")

router = APIRouter(prefix="/data", tags=["Data Export & Telemetry"])

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
SYNTHETIC_DIR = PROJECT_ROOT / "data" / "synthetic"
SNAPSHOT_DIR = PROJECT_ROOT / "experiments" / "snapshot"
LAB_DIR = PROJECT_ROOT / "data" / "lab"
FIXTURE_PATH = PROJECT_ROOT / "backend" / "tests" / "fixtures" / "nidd_sample.csv"

MAX_DOWNLOAD_SIZE_BYTES = 20 * 1024 * 1024  # 20 MB limit

DATASET_CATALOG = {
    "stable_benign": {
        "display_name": "Stable Benign Core Telemetry",
        "source": "simulated_twin",
        "default_seed": 42,
        "config_version": "v1.0.0",
        "slices_assigned": False,
        "description": "Clean operational 5G telemetry across slices with stationary diurnal variations.",
    },
    "legitimate_growth": {
        "display_name": "Legitimate Growth Telemetry",
        "source": "simulated_twin",
        "default_seed": 42,
        "config_version": "v1.0.0",
        "slices_assigned": False,
        "description": "Proportional volume scaling (2.5x) with stable per-UE packet rates and composition.",
    },
    "slow_attack_ramp": {
        "display_name": "Stealth Slow Attack Ramp",
        "source": "simulated_twin",
        "default_seed": 42,
        "config_version": "v1.0.0",
        "slices_assigned": False,
        "description": "Sub-threshold stealth signalling manipulation gradually expanding over time.",
    },
    "attack_in_growth": {
        "display_name": "Attack Inside Volume Surge",
        "source": "simulated_twin",
        "default_seed": 42,
        "config_version": "v1.0.0",
        "slices_assigned": False,
        "description": "Reconnaissance scan concealed inside high-volume flash crowd expansion.",
    },
    "mimicry_attack": {
        "display_name": "Evasive Mimicry Attack",
        "source": "simulated_twin",
        "default_seed": 42,
        "config_version": "v1.0.0",
        "slices_assigned": False,
        "description": "Adversarial traffic designed to match benign aggregate packet rates with shifted protocol ratios.",
    },
    "semi_synthetic_real_ramp": {
        "display_name": "Real-Backbone Hidden Ramp (Semi-Synthetic)",
        "source": "semi_synthetic",
        "default_seed": 42,
        "config_version": "v1.0.0-real-ramp",
        "slices_assigned": True,
        "description": "Semi-synthetic stream combining real 5G-NIDD test benign traffic with real SYNFlood attack injection.",
    },
    "fiveg_nidd": {
        "display_name": "Real 5G-NIDD Testbed Telemetry",
        "source": "real_recorded",
        "default_seed": 42,
        "config_version": "v1.0.0",
        "slices_assigned": True,
        "description": "Real recorded 5G testbed traffic from 5G-NIDD NetFlow capture with topology-assigned slices (BS1: eMBB, BS2: URLLC).",
    },
}


class GenerateDataRequest(BaseModel):
    stream: str = Field(..., description="Scenario or stream name to generate deterministically")
    seed: int = Field(..., ge=0, le=1_000_000, description="Random seed (bounded between 0 and 1,000,000)")


def _sanitize_window(window: Dict[str, Any]) -> Dict[str, Any]:
    """Ensure no raw identifiers or IP payloads exist in output windows."""
    sanitized = json.loads(json.dumps(window))
    # Strip any potential raw fields if present
    forbidden_keys = ["src_ip", "dst_ip", "src_addr", "dst_addr", "imsi", "supi", "payload", "raw_payload"]
    for k in forbidden_keys:
        sanitized.pop(k, None)
    if "raw_counters" in sanitized and isinstance(sanitized["raw_counters"], dict):
        for k in forbidden_keys:
            sanitized["raw_counters"].pop(k, None)
    return sanitized


def _load_or_generate_dataset(
    name: str,
    seed: Optional[int] = None,
) -> Tuple[List[Dict[str, Any]], str, str, int, bool]:
    """Load canonical windows for a dataset, falling back to snapshots or generator."""
    if name not in DATASET_CATALOG and name != "lab":
        raise HTTPException(status_code=404, detail=f"Dataset '{name}' not found in catalog.")

    # Lab dataset special handling
    if name == "lab":
        lab_file = LAB_DIR / "windows.jsonl"
        if not lab_file.is_file():
            raise HTTPException(status_code=404, detail="Lab dataset not found on disk.")
        windows = []
        with open(lab_file, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    windows.append(json.loads(line))
        return [_sanitize_window(w) for w in windows], "lab", "v1.0.0-lab", 42, True

    info = DATASET_CATALOG[name]
    used_seed = seed if seed is not None else info["default_seed"]
    source = info["source"]
    config_version = info["config_version"]
    slices_assigned = info["slices_assigned"]

    # 1. Real 5G-NIDD fixture
    if name == "fiveg_nidd":
        if FIXTURE_PATH.is_file():
            adapter = FiveGNIDDAdapter()
            records = list(adapter.parse_records(FIXTURE_PATH))
            windows = adapter.adapt(records, slice_id=BS1_SLICE_ID)
            return [_sanitize_window(w) for w in windows], source, config_version, used_seed, slices_assigned
        else:
            raise HTTPException(status_code=404, detail="5G-NIDD fixture not found.")

    # 2. Semi-synthetic real ramp
    if name == "semi_synthetic_real_ramp":
        sc = RealBackboneHiddenRampScenario()
        windows = sc.generate(seed=used_seed)
        return [_sanitize_window(w) for w in windows], source, config_version, used_seed, slices_assigned

    # 3. Synthetic streams: stable_benign, legitimate_growth, slow_attack_ramp, attack_in_growth, mimicry_attack
    if used_seed == info["default_seed"]:
        json_file = SYNTHETIC_DIR / f"{name}.json"
        if json_file.is_file():
            try:
                with open(json_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    windows = data.get("windows", [])
                    if windows:
                        return [_sanitize_window(w) for w in windows], source, config_version, used_seed, slices_assigned
            except Exception as e:
                logger.warning("Error reading %s: %s; falling back to generator", json_file, e)

        # Fallback to snapshot if synthetic dir unavailable
        snap_file = SNAPSHOT_DIR / f"{name}.json"
        if snap_file.is_file():
            try:
                with open(snap_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    windows = data.get("windows", [])
                    if windows:
                        return [_sanitize_window(w) for w in windows], source, config_version, used_seed, slices_assigned
            except Exception as e:
                logger.warning("Error reading snapshot %s: %s", snap_file, e)

    # 4. Deterministic synthetic generator
    gen = SyntheticGenerator(seed=used_seed)
    windows = gen.generate_scenario_windows(scenario_name=name, slice_name="eMBB", num_windows=60)
    for idx, w in enumerate(windows):
        w["window_id"] = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{name}_{used_seed}_{idx}"))
    return [_sanitize_window(w) for w in windows], source, config_version, used_seed, slices_assigned


@router.get("/datasets")
def list_available_datasets() -> Dict[str, Any]:
    """List available datasets with structured metadata blocks and export specifications."""
    datasets = []

    for name, info in DATASET_CATALOG.items():
        # Quick estimate of record count and size
        rec_count = 60
        size_bytes = 84000
        if name == "semi_synthetic_real_ramp":
            rec_count = 40
            size_bytes = 58000
        elif name == "fiveg_nidd":
            rec_count = 80
            size_bytes = 110000

        json_file = SYNTHETIC_DIR / f"{name}.json"
        if json_file.is_file():
            size_bytes = json_file.stat().st_size

        entry = {
            "name": name,
            "display_name": info["display_name"],
            "source": info["source"],
            "seed": info["default_seed"],
            "config_version": info["config_version"],
            "record_count": rec_count,
            "size_bytes": size_bytes,
            "slices_assigned": info["slices_assigned"],
            "description": info["description"],
            "metadata": {
                "dataset_name": name,
                "source": info["source"],
                "seed": info["default_seed"],
                "config_version": info["config_version"],
                "record_count": rec_count,
                "window_duration_sec": 60,
                "slices_assigned": info["slices_assigned"],
                "anonymized": True,
                "no_raw_identifiers": True,
            },
        }
        datasets.append(entry)

    # Check if live lab data exists
    lab_file = LAB_DIR / "windows.jsonl"
    if lab_file.is_file():
        try:
            line_count = 0
            with open(lab_file, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        line_count += 1
            datasets.append({
                "name": "lab",
                "display_name": "Live Open5GS Lab Telemetry",
                "source": "lab",
                "seed": 42,
                "config_version": "v1.0.0-lab",
                "record_count": line_count,
                "size_bytes": lab_file.stat().st_size,
                "slices_assigned": True,
                "description": "Live Open5GS testbed telemetry canonical windows from physical radio or emulated core.",
                "metadata": {
                    "dataset_name": "lab",
                    "source": "lab",
                    "seed": 42,
                    "config_version": "v1.0.0-lab",
                    "record_count": line_count,
                    "window_duration_sec": 60,
                    "slices_assigned": True,
                    "anonymized": True,
                    "no_raw_identifiers": True,
                },
            })
        except Exception:
            pass

    return {
        "datasets": datasets,
        "total": len(datasets),
    }


@router.get("/{name}/preview")
def preview_dataset(
    name: str,
    limit: int = Query(20, ge=1, le=100, description="Max windows to return in preview (default 20)"),
) -> Dict[str, Any]:
    """Return top windows with hashed IDs and aggregates (strictly no raw IPs or payloads)."""
    windows, source, config_version, seed, slices_assigned = _load_or_generate_dataset(name)
    preview_slice = windows[:limit]

    metadata = {
        "dataset_name": name,
        "source": source,
        "seed": seed,
        "config_version": config_version,
        "total_records": len(windows),
        "preview_records": len(preview_slice),
        "window_duration_sec": 60,
        "slices_assigned": slices_assigned,
        "anonymized": True,
        "no_raw_identifiers": True,
    }

    return {
        "name": name,
        "source": source,
        "seed": seed,
        "config_version": config_version,
        "limit": limit,
        "total_records": len(windows),
        "metadata": metadata,
        "windows": preview_slice,
    }


@router.get("/{name}/download")
def download_dataset(
    name: str,
    seed: Optional[int] = Query(None, ge=0, le=1_000_000, description="Optional custom seed"),
) -> Response:
    """Download JSON attachment named commshield_<name>_<source>_seed<seed>.json (capped at 20MB)."""
    windows, source, config_version, used_seed, slices_assigned = _load_or_generate_dataset(name, seed=seed)

    metadata = {
        "dataset_name": name,
        "source": source,
        "seed": used_seed,
        "config_version": config_version,
        "record_count": len(windows),
        "window_duration_sec": 60,
        "slices_assigned": slices_assigned,
        "anonymized": True,
        "no_raw_identifiers": True,
        "exported_at": datetime.now(timezone.utc).isoformat(),
    }

    export_payload = {
        "metadata": metadata,
        "windows": windows,
    }

    content_str = json.dumps(export_payload, indent=2)
    content_bytes = content_str.encode("utf-8")

    if len(content_bytes) > MAX_DOWNLOAD_SIZE_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"Export payload exceeds maximum allowed size ({MAX_DOWNLOAD_SIZE_BYTES} bytes).",
        )

    filename = f"commshield_{name}_{source}_seed{used_seed}.json"
    headers = {
        "Content-Disposition": f'attachment; filename="{filename}"',
        "Content-Type": "application/json; charset=utf-8",
    }

    return Response(content=content_bytes, media_type="application/json", headers=headers)


@router.post("/generate")
def generate_telemetry_stream(req: GenerateDataRequest) -> Dict[str, Any]:
    """Run deterministic generator for one stream with seed bounds without altering stored files."""
    if req.stream not in DATASET_CATALOG:
        valid_streams = list(DATASET_CATALOG.keys())
        raise HTTPException(
            status_code=400,
            detail=f"Unknown stream '{req.stream}'. Supported streams: {valid_streams}",
        )

    windows, source, config_version, seed, slices_assigned = _load_or_generate_dataset(req.stream, seed=req.seed)

    metadata = {
        "stream": req.stream,
        "seed": seed,
        "source": source,
        "config_version": config_version,
        "record_count": len(windows),
        "slices_assigned": slices_assigned,
        "anonymized": True,
        "no_raw_identifiers": True,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "storage_altered": False,
    }

    return {
        "stream": req.stream,
        "seed": seed,
        "source": source,
        "record_count": len(windows),
        "config_version": config_version,
        "metadata": metadata,
        "preview": windows[:20],
        "message": f"Successfully generated {len(windows)} deterministic windows for {req.stream} with seed {seed} in-memory without altering stored files.",
    }
