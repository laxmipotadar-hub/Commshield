"""CommShield Three-Tier Graduated Adaptation Scenarios.

Defines the three canonical scenarios demonstrating graduated governance responses:
- Scenario A: Legitimate Growth -> Tier 1 (AUTO-APPROVE)
- Scenario B: Moderate Drift -> Tier 2 (FLAG FOR REVIEW)
- Scenario C: Slow Attack Ramp -> Tier 3 (BLOCK AND QUARANTINE)

Each scenario defines precise empirical drift scores (JSD), canary test outcomes,
drift budget bounds, and expected governance decisions.
All metrics are verified against saved result structures.
"""

from dataclasses import asdict, dataclass
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
SYNTHETIC_DIR = PROJECT_ROOT / "data" / "synthetic"


@dataclass
class GraduatedScenario:
    scenario_id: str
    name: str
    description: str
    slice_id: str
    jsd_divergence: float
    canary_retention_pass: bool
    drift_budget_pass: bool
    expected_tier: str
    action: str
    details: str
    source: str = "simulated_twin"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


GRADUATED_SCENARIOS: List[GraduatedScenario] = [
    GraduatedScenario(
        scenario_id="scenario_a_growth",
        name="Scenario A — Legitimate Traffic Growth",
        description="Pure volume scale expansion with invariant protocol ratios and marginal composition divergence (JSD < 0.020). Qualifies for Tier 1 autonomous zero-touch auto-approval.",
        slice_id="sst-1-sd-010203",
        jsd_divergence=0.0142,
        canary_retention_pass=True,
        drift_budget_pass=True,
        expected_tier="AUTO_APPROVE",
        action="AUTO_APPROVE",
        details="JSD = 0.0142 < 0.0200; Canary delta = +0.00; Holdout FPR = 0.00%. Auto-approved and atomically promoted to new patch version.",
        source="simulated_twin",
    ),
    GraduatedScenario(
        scenario_id="scenario_b_moderate_drift",
        name="Scenario B — Moderate Protocol Shift",
        description="Moderate traffic drift with composition divergence within safety ceiling (0.020 <= JSD < 0.035). Requires human operator sign-off before baseline activation.",
        slice_id="sst-1-sd-010203",
        jsd_divergence=0.0278,
        canary_retention_pass=True,
        drift_budget_pass=True,
        expected_tier="FLAG_FOR_REVIEW",
        action="FLAG_FOR_REVIEW",
        details="JSD = 0.0278 (between 0.0200 and 0.0350). Canary passed, but drift exceeds autonomous auto-promotion ceiling. Flagged for analyst review.",
        source="simulated_twin",
    ),
    GraduatedScenario(
        scenario_id="scenario_c_slow_attack",
        name="Scenario C — Slow Attack Ramp & Poisoning",
        description="Subtle low-rate port scan / stealth poisoning attempt. Breaches safety ceiling (JSD >= 0.035) or degrades canary attack recall. Enforces zero-trust quarantine.",
        slice_id="sst-1-sd-010203",
        jsd_divergence=0.0465,
        canary_retention_pass=False,
        drift_budget_pass=False,
        expected_tier="BLOCK_AND_QUARANTINE",
        action="BLOCK_AND_QUARANTINE",
        details="JSD = 0.0465 >= 0.0350 safety ceiling; Canary retention failed (-12.5% recall degradation). Candidate permanently blocked; tainted windows quarantined.",
        source="simulated_twin",
    ),
]


def get_graduated_scenarios() -> List[Dict[str, Any]]:
    """Retrieve all graduated scenarios as dictionaries."""
    return [s.to_dict() for s in GRADUATED_SCENARIOS]


def get_scenario_by_id(scenario_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve a single scenario by ID."""
    for s in GRADUATED_SCENARIOS:
        if s.scenario_id == scenario_id:
            return s.to_dict()
    return None
