"""Isolated What-If Digital Twin Experimentation Sandbox.

Allows operators and automated reasoning agents to evaluate hypothetical cyber-incident
scenarios on a decoupled clone of the 5G network graph without altering the active twin state.

Supported hypothetical questions:
- What if UPF fails completely?
- What if Edge Gateway is compromised and attempts data exfiltration?
- What if eMBB traffic surges by 5x?
- What if mitigation is delayed by 60 seconds?
- What if rate limiting fails and hard isolation is required?
- What if an alternative routing topology is deployed?

Returns baseline vs predicted quantitative metrics, delta impacts, assumptions, and recommendations.
"""

from copy import deepcopy
from datetime import datetime, timezone
import logging
import time
from typing import Any, Dict, List, Optional

from .models import (
    DataClassification,
    DigitalTwinStateSnapshot,
    OperationalStatus,
    ScenarioType,
    SecurityStatus,
    WhatIfExperimentRecord,
)
from .propagation import AttackPropagationEngine
from .state_engine import CentralDigitalTwinStateEngine, twin_state_engine

logger = logging.getLogger("commshield.twin.whatif")


class WhatIfExperimentEngine:
    """Decoupled digital twin sandbox for what-if scenario testing."""

    def __init__(self, state_engine: Optional[CentralDigitalTwinStateEngine] = None):
        self._state_engine = state_engine or twin_state_engine
        self._propagation_engine = AttackPropagationEngine()
        self._history: List[WhatIfExperimentRecord] = []

    def get_templates(self) -> List[Dict[str, Any]]:
        """Return catalog of standardized hypothetical experiment templates."""
        return [
            {
                "template_id": "WHAT_IF_UPF_FAILURE",
                "name": "Complete UPF Failure & User Plane Loss",
                "hypothesis": "Total failure of primary UPF will collapse user plane traffic across all slices while control plane functions (AMF, SMF) remain operational.",
                "scenario_type": "UPF_OUTAGE",
                "target_component": "upf-01",
                "default_parameters": {"failover_available": False, "traffic_loss_pct": 100.0},
            },
            {
                "template_id": "WHAT_IF_GATEWAY_BREACH",
                "name": "N6 Perimeter Gateway Exfiltration Breach",
                "hypothesis": "Perimeter router breach enables data exfiltration of up to 350 Mbps from internal edge workloads before perimeter ACL can respond.",
                "scenario_type": ScenarioType.GATEWAY_COMPROMISE.value,
                "target_component": "router-edge-01",
                "default_parameters": {"exfiltration_mbps": 350.0, "time_to_contain_sec": 45.0},
            },
            {
                "template_id": "WHAT_IF_TRAFFIC_SURGE_5X",
                "name": "5x Volumetric Traffic Surge on eMBB",
                "hypothesis": "Simulating a 500% bandwidth surge on eMBB will exceed slice quota, inducing bufferbloat, but URLLC AGV control will remain SLA-isolated.",
                "scenario_type": ScenarioType.SLICE_RESOURCE_ABUSE.value,
                "target_component": "sst-1-sd-010203",
                "default_parameters": {"surge_multiplier": 5.0, "affected_slice": "sst-1-sd-010203"},
            },
            {
                "template_id": "WHAT_IF_DELAYED_MITIGATION",
                "name": "Impact of 60-Second Mitigation Delay",
                "hypothesis": "Delaying mitigation response from automated 3 seconds to operator-manual 60 seconds increases data loss by 14x and drops resilience below 60%.",
                "scenario_type": ScenarioType.DDOS_TRAFFIC_FLOOD.value,
                "target_component": "upf-01",
                "default_parameters": {"delay_seconds": 60.0, "intensity": 4.5},
            },
            {
                "template_id": "WHAT_IF_MITIGATION_FAILURE",
                "name": "Mitigation Failure & Fallback Escalation",
                "hypothesis": "If primary rate limiting fails due to IP spoofing, immediate hard isolation of the ingress gNodeB interface will restore core stability at the cost of local cell downtime.",
                "scenario_type": "MITIGATION_FAIL",
                "target_component": "gnb-01",
                "default_parameters": {"fallback_action": "COMPONENT_ISOLATION"},
            },
        ]

    def simulate_what_if(
        self,
        name: str,
        hypothesis: str,
        scenario_type: str,
        target_component: str,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> WhatIfExperimentRecord:
        """Execute hypothetical simulation against an isolated in-memory twin clone."""
        params = parameters or {}
        exp_id = f"exp-whatif-{int(time.time())}"

        # 1. Capture snapshot of live twin to use as baseline
        snapshot = self._state_engine.get_snapshot()
        cloned_components = deepcopy(snapshot.components)
        cloned_connections = deepcopy(snapshot.connections)
        cloned_slices = deepcopy(snapshot.slices)

        # Baseline metrics
        total_bw = sum(c.traffic_volume_mbps for c in cloned_components.values())
        avg_lat = sum(c.latency_ms for c in cloned_components.values()) / max(1, len(cloned_components))
        avg_loss = sum(c.packet_loss_pct for c in cloned_components.values()) / max(1, len(cloned_components))
        active_comps = sum(1 for c in cloned_components.values() if c.operational_status == OperationalStatus.ACTIVE)
        avail_pct = (active_comps / max(1, len(cloned_components))) * 100.0

        baseline_metrics = {
            "overall_health": snapshot.overall_health_score,
            "average_latency_ms": round(avg_lat, 2),
            "average_packet_loss_pct": round(avg_loss, 2),
            "service_availability_pct": round(avail_pct, 2),
            "throughput_mbps": round(total_bw, 2),
        }

        # 2. Simulate disturbance on isolated clone
        affected_components: List[str] = [target_component]
        pred_health = baseline_metrics["overall_health"]
        pred_lat = baseline_metrics["average_latency_ms"]
        pred_loss = baseline_metrics["average_packet_loss_pct"]
        pred_avail = baseline_metrics["service_availability_pct"]
        pred_bw = baseline_metrics["throughput_mbps"]

        assumptions: List[str] = [
            "3GPP Release 16 slicing isolation parameters hold for control plane.",
            "Underlying physical fiber latency remains bounded under nominal conditions.",
            "What-if engine operates decoupled from active state mutation.",
        ]
        limitations: List[str] = [
            "Simulation models logical network queue dynamics and statistical degradation rather than per-packet ASIC scheduling.",
            "Wireless fading channel dynamics are aggregated into statistical packet loss.",
        ]
        recommendation: str = ""

        # Handle experiment scenarios
        if scenario_type in ("UPF_OUTAGE", ScenarioType.UPF_OVERLOAD.value):
            pred_health = max(20.0, pred_health - 55.0)
            pred_lat += 45.0
            pred_loss += 22.5
            pred_avail -= 35.0  # All user plane devices lose connectivity
            pred_bw = round(pred_bw * 0.1, 2)  # User plane collapsed
            affected_components.extend(["gnb-01", "switch-core-01", "router-edge-01"])
            for cid, c in cloned_components.items():
                if c.component_type == "UE":
                    affected_components.append(cid)
            recommendation = "Deploy redundant N9/N3 multi-homed UPF instance with automatic PFCP session transfer."

        elif scenario_type == ScenarioType.GATEWAY_COMPROMISE.value:
            exfil_bw = float(params.get("exfiltration_mbps", 350.0))
            pred_health = max(35.0, pred_health - 35.0)
            pred_lat += 28.0
            pred_loss += 5.0
            pred_bw += exfil_bw
            affected_components.extend(["switch-core-01", "sec-monitor-01", "edge-node-01"])
            recommendation = "Enable stateful N6 microsegmentation and enforce automated egress rate-limiting on router-edge-01."

        elif scenario_type in (ScenarioType.SLICE_RESOURCE_ABUSE.value, "TRAFFIC_SURGE_5X"):
            surge_mult = float(params.get("surge_multiplier", 4.0))
            pred_health = max(60.0, pred_health - 22.0)
            pred_lat += 18.0
            pred_loss += 8.2
            pred_bw = round(pred_bw * min(3.0, surge_mult * 0.7), 2)
            # Only eMBB UEs and UPF affected; URLLC remains SLA-protected
            affected_components.extend(["ue-camera-01", "ue-camera-02", "ue-camera-03", "ue-camera-04", "upf-01"])
            recommendation = "Verify PCF AMBR (Aggregate Maximum Bit Rate) policy to strictly enforce eMBB ceiling and preserve URLLC prioritization."

        elif scenario_type == ScenarioType.DDOS_TRAFFIC_FLOOD.value or params.get("delay_seconds"):
            delay = float(params.get("delay_seconds", 30.0))
            pred_health = max(15.0, pred_health - (30.0 + delay * 0.4))
            pred_lat += (20.0 + delay * 0.5)
            pred_loss += min(40.0, 5.0 + delay * 0.3)
            pred_avail -= min(50.0, 10.0 + delay * 0.5)
            affected_components.extend(["upf-01", "gnb-01", "switch-core-01"])
            recommendation = "Automate Closed-Loop Autonomous Response to trigger Tier-1/Tier-2 mitigation within < 5s of anomaly detection."

        else:
            # Generic disturbance
            pred_health = max(40.0, pred_health - 25.0)
            pred_lat += 15.0
            pred_loss += 4.0
            recommendation = "Maintain continuous digital twin telemetry monitoring and threshold alarm alerts."

        predicted_metrics = {
            "overall_health": round(pred_health, 2),
            "average_latency_ms": round(pred_lat, 2),
            "average_packet_loss_pct": round(pred_loss, 2),
            "service_availability_pct": round(pred_avail, 2),
            "throughput_mbps": round(pred_bw, 2),
        }

        impact_delta = {
            "health_drop": round(baseline_metrics["overall_health"] - predicted_metrics["overall_health"], 2),
            "latency_increase_ms": round(predicted_metrics["average_latency_ms"] - baseline_metrics["average_latency_ms"], 2),
            "packet_loss_increase_pct": round(predicted_metrics["average_packet_loss_pct"] - baseline_metrics["average_packet_loss_pct"], 2),
            "availability_loss_pct": round(baseline_metrics["service_availability_pct"] - predicted_metrics["service_availability_pct"], 2),
            "throughput_change_mbps": round(predicted_metrics["throughput_mbps"] - baseline_metrics["throughput_mbps"], 2),
        }

        record = WhatIfExperimentRecord(
            experiment_id=exp_id,
            name=name,
            hypothesis=hypothesis,
            target_component=target_component,
            scenario_type=scenario_type,
            parameters=params,
            baseline_metrics=baseline_metrics,
            predicted_metrics=predicted_metrics,
            affected_components=list(set(affected_components)),
            impact_delta=impact_delta,
            assumptions=assumptions,
            limitations=limitations,
            recommendation=recommendation,
            created_at=datetime.now(timezone.utc).isoformat(),
        )

        self._history.append(record)
        return record

    def get_history(self) -> List[WhatIfExperimentRecord]:
        return list(self._history)


# Global singleton instance
whatif_engine = WhatIfExperimentEngine()
# CommShield AI Core
