"""Resilience Intelligence and Quantitative Scoring Engine for 5G Digital Twin.

Computes multi-dimensional resilience score based on:
- Time to Detect (TTD)
- Time to Mitigate (TTM)
- Time to Recover (TTR)
- Service Availability (%)
- Network Health Degradation (%)
- Residual Impact Post-Mitigation (%)

Mathematical Formula:
Resilience = 100 * [
    0.40 * (Availability / 100)
    + 0.40 * (1 - Degradation / 100)
    + 0.20 * exp(-0.01 * (TTD + TTM + TTR))
] * (1 - ResidualImpact)
"""

from datetime import datetime, timezone
import math
from typing import Any, Dict, Optional

from .models import (
    DigitalTwinStateSnapshot,
    OperationalStatus,
    ResilienceMetrics,
    ScenarioLifecycleState,
)


FORMULA_DOCUMENTATION = (
    "Resilience = 100 * [0.40 * (Availability / 100) + 0.40 * (1 - Degradation / 100) "
    "+ 0.20 * exp(-0.01 * (TTD + TTM + TTR))] * (1 - ResidualImpact)"
)


class ResilienceIntelligenceEngine:
    """Computes verifiable, quantitative resilience scores for the 5G Digital Twin."""

    @staticmethod
    def calculate_resilience(
        snapshot: DigitalTwinStateSnapshot,
        ttd_sec: float = 0.0,
        ttm_sec: float = 0.0,
        ttr_sec: float = 0.0,
        residual_impact_ratio: float = 0.0,
    ) -> ResilienceMetrics:
        """Evaluate network state snapshot and compute multi-factor resilience metrics."""
        components = snapshot.components
        total_comps = max(1, len(components))

        # 1. Service Availability: Percentage of components not OFFLINE or CRITICAL
        active_or_nominal = sum(
            1 for c in components.values()
            if c.operational_status in (OperationalStatus.ACTIVE, OperationalStatus.DEGRADED)
        )
        service_availability_pct = round((active_or_nominal / total_comps) * 100.0, 2)

        # 2. Network Degradation: Inverse of overall health score
        # 100% health = 0% degradation; 60% health = 40% degradation
        overall_health = snapshot.overall_health_score
        network_degradation_pct = round(max(0.0, min(100.0, 100.0 - overall_health)), 2)

        # 3. Counts of affected components & slices
        affected_comps_count = sum(
            1 for c in components.values()
            if c.operational_status != OperationalStatus.ACTIVE or c.health_score < 90.0
        )
        affected_slices_count = sum(
            1 for s in snapshot.slices.values()
            if s.security_state != "NOMINAL" or s.current_packet_loss_pct > 1.0
        )

        # If in nominal state and no active attack or perturbation specified, return nominal baseline metrics
        if (
            snapshot.lifecycle_state == ScenarioLifecycleState.NORMAL
            and affected_comps_count == 0
            and ttd_sec <= 0.0
            and ttm_sec <= 0.0
            and ttr_sec <= 0.0
            and residual_impact_ratio <= 0.0
        ):
            return ResilienceMetrics(
                time_to_detect_sec=0.0,
                time_to_mitigate_sec=0.0,
                time_to_recover_sec=0.0,
                service_availability_pct=100.0,
                network_degradation_pct=0.0,
                affected_components_count=0,
                affected_slices_count=0,
                residual_impact_pct=0.0,
                resilience_score=100.0,
                formula_documentation=FORMULA_DOCUMENTATION,
                assessment_grade="EXCELLENT",
                timestamp=datetime.now(timezone.utc).isoformat(),
            )

        # Dynamic TTD, TTM, TTR estimation if not explicitly provided
        if ttd_sec <= 0.0 and snapshot.lifecycle_state not in (
            ScenarioLifecycleState.NORMAL,
            ScenarioLifecycleState.ATTACK_INITIATED,
        ):
            ttd_sec = 4.2  # Nominal AI inference and telemetry window latency

        if ttm_sec <= 0.0 and snapshot.lifecycle_state in (
            ScenarioLifecycleState.MITIGATING,
            ScenarioLifecycleState.VERIFYING_MITIGATION,
            ScenarioLifecycleState.RECOVERED,
        ):
            ttm_sec = 3.5  # Time to enact containment / rate-limiting

        if ttr_sec <= 0.0 and snapshot.lifecycle_state == ScenarioLifecycleState.RECOVERED:
            ttr_sec = 5.0  # Telemetry stabilization time

        total_response_time = max(0.0, ttd_sec + ttm_sec + ttr_sec)
        time_factor = math.exp(-0.01 * total_response_time)

        # Term calculation
        term_avail = 0.40 * (service_availability_pct / 100.0)
        term_degrad = 0.40 * (1.0 - (network_degradation_pct / 100.0))
        term_time = 0.20 * time_factor

        base_resilience = 100.0 * (term_avail + term_degrad + term_time)
        residual_impact_clamped = max(0.0, min(1.0, residual_impact_ratio))
        final_score = round(max(0.0, min(100.0, base_resilience * (1.0 - residual_impact_clamped))), 2)

        # Assessment Grade
        if final_score >= 85.0:
            grade = "EXCELLENT"
        elif final_score >= 70.0:
            grade = "GOOD"
        elif final_score >= 50.0:
            grade = "DEGRADED"
        else:
            grade = "VULNERABLE"

        return ResilienceMetrics(
            time_to_detect_sec=round(ttd_sec, 2),
            time_to_mitigate_sec=round(ttm_sec, 2),
            time_to_recover_sec=round(ttr_sec, 2),
            service_availability_pct=service_availability_pct,
            network_degradation_pct=network_degradation_pct,
            affected_components_count=affected_comps_count,
            affected_slices_count=affected_slices_count,
            residual_impact_pct=round(residual_impact_clamped * 100.0, 2),
            resilience_score=final_score,
            formula_documentation=FORMULA_DOCUMENTATION,
            assessment_grade=grade,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )


# Global singleton instance
resilience_engine = ResilienceIntelligenceEngine()
