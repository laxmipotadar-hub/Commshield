import json
from pathlib import Path
from typing import List
from fastapi import APIRouter

from ..schemas import DatasetInfo, DatasetListResponse

router = APIRouter(tags=["Datasets"])

SYNTHETIC_DIR = Path(__file__).resolve().parent.parent.parent.parent / "data" / "synthetic"

SCENARIO_DISPLAY = {
    "5g_nidd": {
        "name": "5G-NIDD Real 5G Testbed Traffic",
        "description": "Real 5G testbed traffic from 5G-NIDD dataset with assigned slices (BS1: eMBB, BS2: URLLC).",
        "data_source": "5g_nidd",
        "attack_types": ["port_scan", "icmp_flood", "udp_flood"],
        "default_windows": 80,
    },
    "5g_nidd_portscan_growth": {
        "name": "5G-NIDD Port Scan with Growth",
        "description": "Port scan intrusion concurrent with high-rate organic session expansion (semi-synthetic).",
        "data_source": "5g_nidd",
        "attack_types": ["port_scan", "signalling_flood"],
        "default_windows": 60,
    },
    "stable_benign": {
        "name": "Stable Benign Core Telemetry",
        "description": "Clean operational 5G telemetry across slices with stationary diurnal variations.",
        "data_source": "synthetic",
        "attack_types": [],
        "default_windows": 60,
    },
    "legitimate_growth": {
        "name": "Organic Marketing Campaign Expansion",
        "description": "Proportional 2.5x volume scaling with stable per-UE packet rates and composition.",
        "data_source": "synthetic",
        "attack_types": [],
        "default_windows": 60,
    },
    "slow_attack_ramp": {
        "name": "Stealth Low-and-Slow Attack Ramp",
        "description": "Sub-threshold stealth signalling manipulation gradually expanding over time.",
        "data_source": "synthetic",
        "attack_types": ["slow_pfcp_exhaustion", "nas_rate_drift"],
        "default_windows": 60,
    },
    "attack_in_growth": {
        "name": "Concealed Attack Inside Volume Surge",
        "description": "Reconnaissance port scan concealed inside high-volume flash crowd expansion.",
        "data_source": "synthetic",
        "attack_types": ["port_scan", "syn_flood"],
        "default_windows": 60,
    },
    "mimicry_attack": {
        "name": "Evasive Compositional Mimicry Attack",
        "description": "Adversarial traffic designed to match benign aggregate packet rates with shifted protocol ratios.",
        "data_source": "synthetic",
        "attack_types": ["mimicry_dos", "ue_entropy_collapse"],
        "default_windows": 60,
    },
}


@router.get("/datasets", response_model=DatasetListResponse)
def list_datasets() -> DatasetListResponse:
    """List available public and synthetic testbed traces from filesystem."""
    datasets: List[DatasetInfo] = []

    # Check for metadata.json in synthetic dir
    meta_path = SYNTHETIC_DIR / "metadata.json"
    meta_data = {}
    if meta_path.is_file():
        try:
            with open(meta_path, "r", encoding="utf-8") as f:
                meta_data = json.load(f).get("scenarios", {})
        except Exception:
            pass

    for dataset_id, info in SCENARIO_DISPLAY.items():
        lookup_id = "attack_in_growth" if dataset_id == "5g_nidd_portscan_growth" else dataset_id
        scenario_meta = meta_data.get(lookup_id, {})
        total_windows = scenario_meta.get("total_windows", info.get("default_windows", 60))
        duration_sec = total_windows * 60

        datasets.append(
            DatasetInfo(
                dataset_id=dataset_id,
                name=info["name"],
                description=info["description"],
                data_source=info.get("data_source", "synthetic"),
                total_windows=total_windows,
                duration_sec=duration_sec,
                attack_types=info["attack_types"],
            )
        )

    return DatasetListResponse(
        datasets=datasets,
        total=len(datasets),
    )
