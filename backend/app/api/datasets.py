import json
from pathlib import Path
from typing import List
from fastapi import APIRouter

from ..schemas import DatasetInfo, DatasetListResponse

router = APIRouter(tags=["Datasets"])

SYNTHETIC_DIR = Path(__file__).resolve().parent.parent.parent.parent / "data" / "synthetic"

SCENARIO_DISPLAY = {
    "5g_nidd_portscan_growth": {
        "name": "5G-NIDD Port Scan with Growth",
        "description": "Port scan intrusion concurrent with high-rate organic session expansion.",
        "attack_types": ["port_scan", "signalling_flood"],
    },
    "stable_benign": {
        "name": "Stable Benign Core Telemetry",
        "description": "Clean operational 5G telemetry across slices with stationary diurnal variations.",
        "attack_types": [],
    },
    "legitimate_growth": {
        "name": "Organic Marketing Campaign Expansion",
        "description": "Proportional 2.5x volume scaling with stable per-UE packet rates and composition.",
        "attack_types": [],
    },
    "slow_attack_ramp": {
        "name": "Stealth Low-and-Slow Attack Ramp",
        "description": "Sub-threshold stealth signalling manipulation gradually expanding over time.",
        "attack_types": ["slow_pfcp_exhaustion", "nas_rate_drift"],
    },
    "attack_in_growth": {
        "name": "Concealed Attack Inside Volume Surge",
        "description": "Reconnaissance port scan concealed inside high-volume flash crowd expansion.",
        "attack_types": ["port_scan", "syn_flood"],
    },
    "mimicry_attack": {
        "name": "Evasive Compositional Mimicry Attack",
        "description": "Adversarial traffic designed to match benign aggregate packet rates with shifted protocol ratios.",
        "attack_types": ["mimicry_dos", "ue_entropy_collapse"],
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
        total_windows = scenario_meta.get("total_windows", 60)
        duration_sec = total_windows * 60

        datasets.append(
            DatasetInfo(
                dataset_id=dataset_id,
                name=info["name"],
                description=info["description"],
                total_windows=total_windows,
                duration_sec=duration_sec,
                attack_types=info["attack_types"],
            )
        )

    return DatasetListResponse(
        datasets=datasets,
        total=len(datasets),
    )
