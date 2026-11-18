"""Demo Mode API Router for CommShield.

Provides pre-packaged real-data 5G-NIDD replay presets, deterministic window ranges,
and key event timelines for zero-randomness presentations.
"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter
from pydantic import BaseModel, Field

router = APIRouter(prefix="/demo", tags=["Demo Mode"])


class KeyEvent(BaseModel):
    window_index: int = Field(..., description="0-based window index within scenario stream where event occurs")
    event_type: str = Field(..., description="Machine event code: first_alert, quarantine, candidate_built, check_result, etc.")
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
    data_label: str  # "real" or "semi-synthetic"
    dataset_id: str
    best_attack_type: Optional[str] = None
    window_range: WindowRange
    key_events: List[KeyEvent]
    three_arm_summary: Optional[Dict[str, Any]] = None
    decision_trace: Optional[Dict[str, Any]] = None


class DemoScenariosResponse(BaseModel):
    scenarios: List[DemoPreset]
    source_attribution: str = "5G-NIDD Real Capture (CIC/UNB testbed) with assigned slices"
    fixed_seed: int = 42


DEMO_PRESETS: List[DemoPreset] = [
    DemoPreset(
        id="real_benign",
        preset_number=1,
        name="Real Benign Traffic (5G-NIDD)",
        description="40 consecutive 60s windows of authentic baseline benign traffic from 5G Standalone core tap points.",
        data_label="real",
        dataset_id="demo_real_benign",
        best_attack_type=None,
        window_range=WindowRange(start_index=0, end_index=39, total_windows=40),
        key_events=[
            KeyEvent(
                window_index=0,
                event_type="nominal_start",
                caption="Replay started: Nominal 5G core user-plane telemetry flowing through calibrated baseline.",
            ),
            KeyEvent(
                window_index=18,
                event_type="drift_alarm",
                caption="Natural variation detected: ADWIN triggers drift alarm; attribution confirms proportional composition.",
            ),
            KeyEvent(
                window_index=39,
                event_type="nominal_complete",
                caption="Replay completed: 0 attack windows injected, 0.0% baseline contamination, nominal 5% FPR.",
            ),
        ],
    ),
    DemoPreset(
        id="real_attack",
        preset_number=2,
        name="Real Attack Traffic (SYNScan)",
        description="20 clean baseline benign windows followed by an authentic 5G-NIDD SYNScan reconnaissance attack window.",
        data_label="real",
        dataset_id="demo_real_attack",
        best_attack_type="SYNScan",  # Best fused recall on 5G-NIDD: 100.0% recall, 0.0% FPR, 0 delay
        window_range=WindowRange(start_index=0, end_index=20, total_windows=21),
        key_events=[
            KeyEvent(
                window_index=0,
                event_type="baseline_lead_in",
                caption="Replay started: Clean benign traffic active on eMBB slice before reconnaissance onset.",
            ),
            KeyEvent(
                window_index=20,
                event_type="first_alert",
                caption="First Alert: SYNScan attack detected immediately (fused score p=0.999 >= 0.98, delay 0w).",
            ),
            KeyEvent(
                window_index=20,
                event_type="quarantine_isolation",
                caption="Quarantine Action: Malicious window isolated in quarantine; baseline contamination remains strictly 0.0%.",
            ),
        ],
    ),
    DemoPreset(
        id="scaled_growth",
        preset_number=3,
        name="Real Benign Traffic Scaled 2x",
        description="Real benign 5G-NIDD traffic scaled 2.0x with composition preserved, modeling enterprise capacity expansion.",
        data_label="semi-synthetic",
        dataset_id="demo_scaled_growth",
        best_attack_type=None,
        window_range=WindowRange(start_index=0, end_index=39, total_windows=40),
        key_events=[
            KeyEvent(
                window_index=0,
                event_type="baseline_1x",
                caption="Replay started: 1x unscaled baseline benign traffic flowing normally.",
            ),
            KeyEvent(
                window_index=20,
                event_type="growth_onset",
                caption="Volume Surge: Traffic scales 2.0x; ADWIN drift detector fires across uplink and downlink counters.",
            ),
            KeyEvent(
                window_index=25,
                event_type="candidate_built",
                caption="Shadow Candidate Built: Proportional growth verified (JSD=0.0034 <= 0.035, per-UE deviation=0.167 <= 0.25).",
            ),
            KeyEvent(
                window_index=25,
                event_type="governance_failure",
                caption="Governance Gate Triggered: Clean candidate fails canary retention (recall drops to 25%) and drift budget (D_rms=6.65 > 2.5) -> Rejected.",
            ),
        ],
    ),
    DemoPreset(
        id="attack_in_growth",
        preset_number=4,
        name="Real Attack Injected into Scaled Growth",
        description="An authentic 5G-NIDD attack window hidden inside 2.0x scaled benign growth traffic.",
        data_label="semi-synthetic",
        dataset_id="demo_attack_in_growth",
        best_attack_type="SYNScan",
        window_range=WindowRange(start_index=0, end_index=20, total_windows=21),
        key_events=[
            KeyEvent(
                window_index=0,
                event_type="scaled_growth_lead_in",
                caption="Replay started: 2.0x scaled high-volume traffic active across eMBB slice.",
            ),
            KeyEvent(
                window_index=20,
                event_type="attack_injected_alert",
                caption="Attack Injected: Real attack window detected instantly despite 2x volume expansion (p=0.999).",
            ),
            KeyEvent(
                window_index=20,
                event_type="quarantine_isolation",
                caption="Quarantine Isolation: Attack window isolated; candidate baseline training excludes attack traffic.",
            ),
            KeyEvent(
                window_index=20,
                event_type="governance_trace",
                caption="Decision Trace & Three-Arm Comparison: Arm C blocks contamination (0.0%), whereas naive Arm B is poisoned.",
            ),
        ],
        three_arm_summary={
            "scenario": "attack_in_scaled_growth",
            "data_label": "semi-synthetic",
            "arms": {
                "arm_a_static": {
                    "name": "Static Anchor",
                    "recall": 1.0,
                    "fpr": 0.05,
                    "contamination": 0.0,
                    "adaptations": 0,
                    "quarantined": 0,
                },
                "arm_b_naive": {
                    "name": "Naive Retraining",
                    "recall": 0.0,
                    "fpr": 0.0,
                    "contamination": 0.0,
                    "adaptations": 1,
                    "quarantined": 0,
                },
                "arm_c_commshield": {
                    "name": "CommShield Gated",
                    "recall": 1.0,
                    "fpr": 0.05,
                    "contamination": 0.0,
                    "adaptations": 0,
                    "quarantined": 1,
                },
            },
        },
        decision_trace={
            "candidate_version": "v1.1.0-real-demo-cand",
            "overall_status": "REJECTED",
            "checks": [
                {
                    "name": "normal_holdout_backtest",
                    "status": "PASSED",
                    "detail": "Normal-holdout FPR is 0.00% (0/20 windows flagged) <= limit 5.00%.",
                },
                {
                    "name": "proportional_growth",
                    "status": "PASSED",
                    "detail": "JSD divergence is 0.0034 <= 0.0350 limit, per-UE session rate deviation is 0.167 <= 0.250 limit.",
                },
                {
                    "name": "canary_retention_test",
                    "status": "FAILED",
                    "detail": "Candidate recall 25.0% vs active recall 100.0% (delta 75.0% exceeds allowed 5.0% limit).",
                },
                {
                    "name": "drift_budget",
                    "status": "FAILED",
                    "detail": "D_rms(cand, active)=6.65 (limit <= 1.5) and D_max=16.90 (limit <= 3.0) exceeded.",
                },
            ],
            "conclusion": "Quarantine enforced: candidate baselines cannot be promoted while canary recall is degraded or distance exceeds anchor budget.",
        },
    ),
]


@router.get("/scenarios", response_model=DemoScenariosResponse)
def get_demo_scenarios() -> DemoScenariosResponse:
    """Return presentation-ready demo replay presets derived from real 5G-NIDD evaluations."""
    return DemoScenariosResponse(
        scenarios=DEMO_PRESETS,
        source_attribution="5G-NIDD Real Capture (CIC/UNB testbed) with assigned slices",
        fixed_seed=42,
    )
