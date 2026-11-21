"""Demo Mode API Router for CommShield.

Provides pre-packaged deterministic four-scene presentation demo presets:
1. Baseline
2. Approved onboarding
3. Unprovisioned device flagged
4. Hidden ramp (where naive is poisoned and CommShield quarantines the excess)

Source tags on every scene. Scene 3 uses the lab clip only if it exists.
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

try:
    from fastapi import APIRouter
except ImportError:
    class APIRouter:
        def __init__(self, *args, **kwargs):
            pass
        def get(self, *args, **kwargs):
            def decorator(f):
                return f
            return decorator

router = APIRouter(prefix="/demo", tags=["Demo Mode"])
logger = logging.getLogger("commshield.demo")

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
DATA_LAB_DIR = PROJECT_ROOT / "data" / "lab"
RESULTS_TWIN_DIR = PROJECT_ROOT / "experiments" / "results" / "twin"
DATA_TWIN_DIR = PROJECT_ROOT / "data" / "twin"


def check_lab_validated() -> bool:
    """Check if data/lab/windows.jsonl exists and validates against schema."""
    lab_file = DATA_LAB_DIR / "windows.jsonl"
    if not lab_file.is_file():
        return False
    try:
        from ml_engine.provisioning.schema import validate_window
        with open(lab_file, "r", encoding="utf-8", newline="\n") as f:
            lines = [line.strip() for line in f if line.strip()]
            if not lines:
                return False
            for line in lines:
                win = json.loads(line)
                validate_window(win)
        return True
    except Exception as e:
        logger.warning("Lab validation check in demo: %s", e)
        return False


def load_saved_three_arm_summary() -> Dict[str, Any]:
    """Load benchmark summary from experiments/results/twin/three_arm_twin_summary.json."""
    summary_path = RESULTS_TWIN_DIR / "three_arm_twin_summary.json"
    if not summary_path.is_file():
        return {}
    with open(summary_path, "r", encoding="utf-8", newline="\n") as f:
        return json.load(f)


class KeyEvent(BaseModel):
    window_index: int = Field(..., description="0-based window index within scenario stream where event occurs")
    event_type: str = Field(..., description="Machine event code: first_alert, quarantine, etc.")
    caption: str = Field(..., description="One-line human readable presenter/judge caption explaining what occurred")


class WindowRange(BaseModel):
    start_index: int = 0
    end_index: int
    total_windows: int


class DemoPreset(BaseModel):
    id: str
    preset_number: int
    name: str
    description: str
    data_label: str  # "simulated_twin" or "lab"
    source: str      # "simulated_twin" | "lab" | "real_recorded"
    source_badge: str  # "Simulated twin" | "Live lab" | "Real recorded"
    dataset_id: str
    scenario: str
    best_attack_type: Optional[str] = None
    window_range: WindowRange
    key_events: List[KeyEvent]
    three_arm_summary: Optional[Dict[str, Any]] = None
    decision_trace: Optional[Dict[str, Any]] = None


class DemoScenariosResponse(BaseModel):
    scenarios: List[DemoPreset]
    source_attribution: str = "CommShield 5G Digital Twin & Lab Telemetry"
    fixed_seed: int = 42


def get_demo_presets() -> List[DemoPreset]:
    """Construct the canonical four-scene demo strictly in order."""
    lab_ok = check_lab_validated()
    summary_data = load_saved_three_arm_summary()
    streams = summary_data.get("streams", {})

    approved_m = streams.get("approved_onboarding", {})
    unprov_m = streams.get("unprovisioned_burst", {})
    ramp_m = streams.get("slow_ramp_in_onboarding", {})

    scene_1 = DemoPreset(
        id="baseline",
        preset_number=1,
        name="1. Baseline Steady-State Telemetry",
        description="Calibrated nominal baseline telemetry flowing across eMBB, URLLC, and mMTC slices with 100% catalog-provisioned SIMs.",
        data_label="simulated_twin",
        source="simulated_twin",
        source_badge="Simulated twin",
        scenario="approved_onboarding",
        dataset_id="baseline",
        best_attack_type=None,
        window_range=WindowRange(start_index=0, end_index=9, total_windows=10),
        key_events=[
            KeyEvent(
                window_index=0,
                event_type="nominal_start",
                caption="Replay started: Nominal 5G core telemetry flowing through calibrated baseline on all slices.",
            ),
            KeyEvent(
                window_index=5,
                event_type="periodic_audit",
                caption="Periodic audit: 200/200 devices catalog provisioned; JSD=0.000, zero drift, 0.0% false alarms.",
            ),
            KeyEvent(
                window_index=9,
                event_type="nominal_complete",
                caption="Baseline complete: Zero security alerts; contamination strictly 0.0%; nominal baseline sustained.",
            ),
        ],
        three_arm_summary={
            "scenario": "baseline",
            "source": "simulated_twin",
            "arms": {
                "naive": {"name": "Naive Retraining", "contamination": 0.0, "fpr": 0.0, "adaptations": 0, "quarantined": 0},
                "commshield_twin": {"name": "CommShield Twin", "contamination": 0.0, "fpr": 0.0, "adaptations": 0, "quarantined": 0},
            },
        },
        decision_trace={
            "status": "APPROVED",
            "conclusion": "Nominal baseline traffic verified; no adaptation required; all devices provisioned.",
            "checks": [
                {"name": "volume_scale", "status": "PASSED", "detail": "k = 1.00 nominal volume across all slices."},
                {"name": "composition_jsd", "status": "PASSED", "detail": "JSD = 0.000 <= 0.045 limit (Null hypothesis accepted)."},
                {"name": "provisioning_check", "status": "PASSED", "detail": "100.0% provisioned in catalog (200 SIMs verified)."},
            ],
        },
    )

    scene_2 = DemoPreset(
        id="approved_onboarding",
        preset_number=2,
        name="2. Approved Onboarding (Batch OB-01 & OB-02)",
        description="Legitimate onboarding surge matching scheduled change events (BATCH-OB-20261115-01) with 100% catalog-verified SIMs.",
        data_label="simulated_twin",
        source="simulated_twin",
        source_badge="Simulated twin",
        scenario="approved_onboarding",
        dataset_id="approved_onboarding",
        best_attack_type=None,
        window_range=WindowRange(start_index=0, end_index=19, total_windows=20),
        key_events=[
            KeyEvent(
                window_index=0,
                event_type="baseline_lead_in",
                caption="Replay started: Steady-state baseline telemetry before scheduled onboarding window.",
            ),
            KeyEvent(
                window_index=10,
                event_type="batch_arrival",
                caption="Batch Ingress: 30 new sensors join mMTC slice; traffic scales by k=1.48 matching BATCH-OB-20261115-01.",
            ),
            KeyEvent(
                window_index=14,
                event_type="governance_approval",
                caption="Governance Approved: JSD=0.018 <= 0.045, 100% provisioned, device anomalous share 0.0% -> Candidate promoted.",
            ),
        ],
        three_arm_summary={
            "scenario": "approved_onboarding",
            "source": "simulated_twin",
            "arms": {
                "naive": {
                    "name": "Naive Retraining",
                    "contamination": approved_m.get("naive", {}).get("contamination", {}).get("mean", 0.0),
                    "fpr": approved_m.get("naive", {}).get("fpr", {}).get("mean", 0.0),
                    "adaptations": approved_m.get("naive", {}).get("onboardings_adapted", 2.0),
                    "quarantined": 0,
                },
                "commshield_twin": {
                    "name": "CommShield Twin",
                    "contamination": approved_m.get("commshield_twin", {}).get("contamination", {}).get("mean", 0.0),
                    "fpr": approved_m.get("commshield_twin", {}).get("fpr", {}).get("mean", 0.027),
                    "adaptations": approved_m.get("commshield_twin", {}).get("onboardings_adapted", 2.0),
                    "quarantined": 0,
                },
            },
        },
        decision_trace={
            "status": "APPROVED",
            "conclusion": "Approved onboarding adapted; 100% provisioned; volume fits scheduled batch; conformal check clear.",
            "checks": [
                {"name": "volume_scale", "status": "PASSED", "detail": "k = 1.48 expansion fits batch size (30 sensors)."},
                {"name": "composition_jsd", "status": "PASSED", "detail": "JSD = 0.018 <= 0.045 limit (Proportional drift)."},
                {"name": "provisioning_catalog", "status": "PASSED", "detail": "100.0% provisioned; matches BATCH-OB-20261115-01."},
                {"name": "conformal_evaluation", "status": "PASSED", "detail": "Device anomalous share: 0.0% <= 10.0%, uncertain: 4.8% <= 30.0%."},
            ],
        },
    )

    scene_3_source = "lab" if lab_ok else "simulated_twin"
    scene_3_badge = "Live lab" if lab_ok else "Simulated twin"

    scene_3 = DemoPreset(
        id="unprovisioned_device",
        preset_number=3,
        name="3. Unprovisioned Device Burst Flagged",
        description="Sudden surge of unprovisioned rogue SIM IDs flagged and quarantined by zero-trust catalog lookup.",
        data_label=scene_3_source,
        source=scene_3_source,
        source_badge=scene_3_badge,
        scenario="unprovisioned_burst",
        dataset_id="unprovisioned_device",
        best_attack_type="Unprovisioned_Burst",
        window_range=WindowRange(start_index=0, end_index=19, total_windows=20),
        key_events=[
            KeyEvent(
                window_index=0,
                event_type="rogue_lead_in",
                caption="Replay started: Clean telemetry before sudden unprovisioned traffic ingress.",
            ),
            KeyEvent(
                window_index=10,
                event_type="first_alert",
                caption="Security Alert: Rogue devices detected; catalog provisioned share drops to 57.1% < 95.0% threshold.",
            ),
            KeyEvent(
                window_index=11,
                event_type="quarantine_isolation",
                caption="Quarantine Enforced: Rule 1 isolates unprovisioned devices; baseline contamination prevented (0.0%).",
            ),
        ],
        three_arm_summary={
            "scenario": "unprovisioned_burst",
            "source": scene_3_source,
            "arms": {
                "naive": {
                    "name": "Naive Retraining",
                    "contamination": unprov_m.get("naive", {}).get("contamination", {}).get("mean", 0.50),
                    "fpr": unprov_m.get("naive", {}).get("fpr", {}).get("mean", 0.133),
                    "adaptations": 0,
                    "quarantined": 0,
                },
                "commshield_twin": {
                    "name": "CommShield Twin",
                    "contamination": unprov_m.get("commshield_twin", {}).get("contamination", {}).get("mean", 0.0),
                    "fpr": unprov_m.get("commshield_twin", {}).get("fpr", {}).get("mean", 0.025),
                    "adaptations": 0,
                    "quarantined": 1,
                },
            },
        },
        decision_trace={
            "status": "QUARANTINED",
            "conclusion": "Quarantine enforced: unprovisioned rogue devices present without catalog registration.",
            "checks": [
                {"name": "volume_scale", "status": "FAILED", "detail": "k = 2.15 sudden anomalous surge."},
                {"name": "composition_jsd", "status": "FAILED", "detail": "JSD = 0.142 > 0.045 limit."},
                {"name": "provisioning_catalog", "status": "FAILED", "detail": "Provisioned share: 57.1% < 95.0%; 40 rogue SIMs detected."},
                {"name": "conformal_evaluation", "status": "FAILED", "detail": "Rogue devices anomaly rate: 99.3% in split conformal test."},
            ],
        },
    )

    scene_4 = DemoPreset(
        id="hidden_ramp",
        preset_number=4,
        name="4. Hidden Ramp (Naive Poisoned vs CommShield Quarantines Excess)",
        description="Subtle creeping rate increases hidden inside an approved onboarding where naive retraining is poisoned and CommShield quarantines the excess.",
        data_label="simulated_twin",
        source="simulated_twin",
        source_badge="Simulated twin",
        scenario="slow_ramp_in_onboarding",
        dataset_id="hidden_ramp",
        best_attack_type="Conformal_Gray_Band",
        window_range=WindowRange(start_index=0, end_index=19, total_windows=20),
        key_events=[
            KeyEvent(
                window_index=0,
                event_type="ramp_lead_in",
                caption="Replay started: Approved onboarding baseline active with scheduled batch event.",
            ),
            KeyEvent(
                window_index=10,
                event_type="ramp_onset",
                caption="Hidden Ramp Onset: 15 devices subtly ramp rate inside approved onboarding volume ($k=1.55$).",
            ),
            KeyEvent(
                window_index=15,
                event_type="conformal_gray_band",
                caption="Conformal Abstention: Creeping devices fall into split-conformal gray band ($p in [0.01, 0.05]$); uncertain share exceeds 30.0%.",
            ),
            KeyEvent(
                window_index=16,
                event_type="governance_divergence",
                caption="Governance Divergence: Naive retraining absorbs attack (33.3% contamination); CommShield quarantines excess (1.7% contamination).",
            ),
        ],
        three_arm_summary={
            "scenario": "slow_ramp_in_onboarding",
            "source": "simulated_twin",
            "arms": {
                "naive": {
                    "name": "Naive Retraining",
                    "contamination": ramp_m.get("naive", {}).get("contamination", {}).get("mean", 0.333),
                    "fpr": ramp_m.get("naive", {}).get("fpr", {}).get("mean", 0.0),
                    "adaptations": 0,
                    "quarantined": 0,
                },
                "commshield_twin": {
                    "name": "CommShield Twin",
                    "contamination": ramp_m.get("commshield_twin", {}).get("contamination", {}).get("mean", 0.017),
                    "fpr": ramp_m.get("commshield_twin", {}).get("fpr", {}).get("mean", 0.027),
                    "adaptations": 0,
                    "quarantined": 1,
                },
            },
        },
        decision_trace={
            "status": "QUARANTINED",
            "conclusion": "Quarantine excess enforced: split-conformal gray band detected ramping anomalous behavior despite valid batch.",
            "checks": [
                {"name": "volume_scale", "status": "PASSED", "detail": "k = 1.55 volume growth initially matches batch envelope."},
                {"name": "composition_jsd", "status": "PASSED", "detail": "JSD = 0.038 <= 0.045 limit."},
                {"name": "provisioning_catalog", "status": "PASSED", "detail": "100.0% provisioned in catalog."},
                {"name": "conformal_evaluation", "status": "FAILED", "detail": "15 ramping sensors fall into conformal gray band (uncertain share > 30.0%)."},
            ],
        },
    )

    return [scene_1, scene_2, scene_3, scene_4]


@router.get("/scenarios", response_model=DemoScenariosResponse)
def get_demo_scenarios() -> DemoScenariosResponse:
    """Return presentation-ready four-scene demo replay presets with source tags and zero-randomness event timelines."""
    presets = get_demo_presets()
    return DemoScenariosResponse(
        scenarios=presets,
        source_attribution="CommShield 5G Digital Twin & Lab Telemetry",
        fixed_seed=42,
    )
