"""Cybersecurity Attack Scenarios and Progression Engine for 5G Digital Twin.

Simulates 6 realistic Private 5G cyber attack scenarios:
1. DDOS_TRAFFIC_FLOOD: Distributed volumetric flood targeting UPF user plane.
2. AUTH_ANOMALY: Signaling flood with rogue authentication cryptograms targeting AMF/AUSF.
3. SLICE_RESOURCE_ABUSE: Unauthorized throughput hogging violating S-NSSAI slice SLA.
4. UPF_OVERLOAD: GTP-U encapsulation saturation and user plane core exhaustion.
5. SUSPICIOUS_UE_ACTIVITY: Compromised IoT device performing internal subnet reconnaissance.
6. GATEWAY_COMPROMISE: Perimeter N6 router exploit attempting data exfiltration.

Includes thread-safe lifecycle state progression (NORMAL -> ATTACK_INITIATED ->
SUSPICIOUS_ACTIVITY -> ANALYSING -> THREAT_DETECTED -> MITIGATING -> VERIFYING -> RECOVERED).
"""

from datetime import datetime, timezone
import logging
import threading
import time
from typing import Any, Dict, List, Optional

from .models import (
    AttackPropagationResult,
    ConnectionStatus,
    DataClassification,
    MitigationActionType,
    MitigationRecommendation,
    MitigationStatus,
    OperationalStatus,
    ScenarioLifecycleState,
    ScenarioType,
    SecurityStatus,
    TelemetryMetric,
    ThreatDetectionResult,
    TrafficBreakdown,
)
from .propagation import AttackPropagationEngine
from .state_engine import CentralDigitalTwinStateEngine, twin_state_engine

logger = logging.getLogger("commshield.twin.scenarios")


SCENARIO_ALIASES: Dict[str, str] = {
    "volumetric ddos": ScenarioType.DDOS_TRAFFIC_FLOOD.value,
    "ddos": ScenarioType.DDOS_TRAFFIC_FLOOD.value,
    "ddos volumetric traffic flood": ScenarioType.DDOS_TRAFFIC_FLOOD.value,
    "udp flood": ScenarioType.DDOS_TRAFFIC_FLOOD.value,
    "syn flood": ScenarioType.DDOS_TRAFFIC_FLOOD.value,
    "http flood": ScenarioType.DDOS_TRAFFIC_FLOOD.value,
    "distributed ddos": ScenarioType.DDOS_TRAFFIC_FLOOD.value,
    "distributed": ScenarioType.DDOS_TRAFFIC_FLOOD.value,
    "signalling storm": ScenarioType.AUTH_ANOMALY.value,
    "signaling storm": ScenarioType.AUTH_ANOMALY.value,
    "auth anomaly": ScenarioType.AUTH_ANOMALY.value,
    "slow onboarding": ScenarioType.AUTH_ANOMALY.value,
    "network congestion": ScenarioType.SLICE_RESOURCE_ABUSE.value,
    "congestion": ScenarioType.SLICE_RESOURCE_ABUSE.value,
    "slice abuse": ScenarioType.SLICE_RESOURCE_ABUSE.value,
    "slow-rate dos": ScenarioType.SUSPICIOUS_UE_ACTIVITY.value,
    "slow-rate": ScenarioType.SUSPICIOUS_UE_ACTIVITY.value,
    "slow rate": ScenarioType.SUSPICIOUS_UE_ACTIVITY.value,
    "port scanning": ScenarioType.SUSPICIOUS_UE_ACTIVITY.value,
    "port scan": ScenarioType.SUSPICIOUS_UE_ACTIVITY.value,
    "suspicious ue": ScenarioType.SUSPICIOUS_UE_ACTIVITY.value,
    "suspicious ue behaviour": ScenarioType.SUSPICIOUS_UE_ACTIVITY.value,
    "gateway compromise": ScenarioType.GATEWAY_COMPROMISE.value,
}


SCENARIO_CATALOG: Dict[str, Dict[str, Any]] = {
    ScenarioType.DDOS_TRAFFIC_FLOOD.value: {
        "scenario_type": ScenarioType.DDOS_TRAFFIC_FLOOD,
        "name": "DDoS Volumetric Traffic Flood",
        "description": "Massive coordinated UDP/GTP-U flood targeting UPF user plane via compromised surveillance camera UEs.",
        "default_target": "upf-01",
        "default_entry": "ue-camera-01",
        "affected_slice": "sst-1-sd-010203",
        "traffic_multiplier": 5.5,
        "expected_detection": "AI_ISOLATION_FOREST",
        "confidence": 0.96,
        "severity": "CRITICAL",
        "details": {
            "attack_vector": "N3 GTP-U Tunnel Flooding",
            "protocol": "GTP-U / UDP",
            "peak_bandwidth_mbps": 820.0,
            "target_packet_loss_pct": 18.5,
            "target_latency_ms": 68.0,
        },
    },
    ScenarioType.AUTH_ANOMALY.value: {
        "scenario_type": ScenarioType.AUTH_ANOMALY,
        "name": "Signaling Storm & Authentication Anomaly",
        "description": "High-frequency rogue 5G-AKA authentication requests targeting AMF and AUSF, causing control-plane signaling congestion.",
        "default_target": "amf-01",
        "default_entry": "ue-sensor-01",
        "affected_slice": "sst-3-sd-030405",
        "traffic_multiplier": 3.0,
        "expected_detection": "RULE_BASED_ADWIN",
        "confidence": 0.91,
        "severity": "HIGH",
        "details": {
            "attack_vector": "N2 / NGAP Signalling Flood & N12 5G-AKA Replay",
            "protocol": "SCTP / NGAP / HTTP2-SBI",
            "peak_signaling_rate_rps": 1450.0,
            "target_packet_loss_pct": 4.5,
            "target_latency_ms": 42.0,
        },
    },
    ScenarioType.SLICE_RESOURCE_ABUSE.value: {
        "scenario_type": ScenarioType.SLICE_RESOURCE_ABUSE,
        "name": "Network Slice Resource Abuse",
        "description": "Unauthorized high-bitrate streaming on eMBB slice starving bandwidth allocation while URLLC isolation holds.",
        "default_target": "sst-1-sd-010203",
        "default_entry": "ue-camera-02",
        "affected_slice": "sst-1-sd-010203",
        "traffic_multiplier": 3.8,
        "expected_detection": "AI_AUTOENCODER",
        "confidence": 0.92,
        "severity": "MEDIUM",
        "details": {
            "attack_vector": "S-NSSAI Bandwidth Quota Violation",
            "protocol": "User-Plane TCP/UDP",
            "slice_consumption_mbps": 640.0,
            "target_packet_loss_pct": 11.2,
            "target_latency_ms": 36.0,
        },
    },
    ScenarioType.UPF_OVERLOAD.value: {
        "scenario_type": ScenarioType.UPF_OVERLOAD,
        "name": "UPF Core Processing Exhaustion",
        "description": "Saturates UPF packet buffer and routing table with high packet rate, degrading user-plane routing across all slices.",
        "default_target": "upf-01",
        "default_entry": "gnb-01",
        "affected_slice": "ALL",
        "traffic_multiplier": 4.8,
        "expected_detection": "AI_FUSION",
        "confidence": 0.98,
        "severity": "CRITICAL",
        "details": {
            "attack_vector": "GTP-U Encapsulation Buffer Overflow",
            "protocol": "GTP-U",
            "peak_packet_rate_kpps": 350.0,
            "target_packet_loss_pct": 24.5,
            "target_latency_ms": 78.0,
        },
    },
    ScenarioType.SUSPICIOUS_UE_ACTIVITY.value: {
        "scenario_type": ScenarioType.SUSPICIOUS_UE_ACTIVITY,
        "name": "Suspicious UE Lateral Reconnaissance",
        "description": "Compromised mMTC sensor UE scanning internal private 5G core subnet and attempting lateral movement.",
        "default_target": "switch-core-01",
        "default_entry": "ue-sensor-03",
        "affected_slice": "sst-3-sd-030405",
        "traffic_multiplier": 2.2,
        "expected_detection": "AI_ISOLATION_FOREST",
        "confidence": 0.88,
        "severity": "HIGH",
        "details": {
            "attack_vector": "Internal Port Scan & Lateral Probe",
            "protocol": "TCP SYN Scan / ICMP Sweep",
            "scan_rate_probes_sec": 240.0,
            "target_packet_loss_pct": 2.0,
            "target_latency_ms": 14.0,
        },
    },
    ScenarioType.GATEWAY_COMPROMISE.value: {
        "scenario_type": ScenarioType.GATEWAY_COMPROMISE,
        "name": "Edge Gateway Intrusion & Exfiltration",
        "description": "Perimeter N6 router exploit attempting unauthorized ingress tunneling and bulk data exfiltration.",
        "default_target": "router-edge-01",
        "default_entry": "router-edge-01",
        "affected_slice": "ALL",
        "traffic_multiplier": 3.2,
        "expected_detection": "AI_FUSION",
        "confidence": 0.95,
        "severity": "CRITICAL",
        "details": {
            "attack_vector": "N6 Ingress Vulnerability Exploit",
            "protocol": "HTTPS Tunnel / BGP Hijack",
            "exfiltration_bandwidth_mbps": 320.0,
            "target_packet_loss_pct": 8.0,
            "target_latency_ms": 52.0,
        },
    },
}


class ScenarioSimulationEngine:
    """Thread-safe engine governing cyber attack scenario execution and progression."""

    def __init__(self, state_engine: Optional[CentralDigitalTwinStateEngine] = None):
        self._state_engine = state_engine or twin_state_engine
        self._propagation_engine = AttackPropagationEngine()
        self._lock = threading.RLock()
        self._active_scenario: Optional[Dict[str, Any]] = None
        self._worker_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._pause_event = threading.Event()
        self._current_step: int = 0
        self._start_time: Optional[float] = None

    def get_catalog(self) -> List[Dict[str, Any]]:
        """Return metadata for all 6 supported scenarios."""
        result = []
        for k, v in SCENARIO_CATALOG.items():
            result.append({
                "scenario_id": k,
                "name": v["name"],
                "description": v["description"],
                "default_target": v["default_target"],
                "default_entry": v["default_entry"],
                "affected_slice": v["affected_slice"],
                "severity": v["severity"],
                "details": v["details"],
            })
        return result

    def get_active_scenario(self) -> Optional[Dict[str, Any]]:
        """Return details of currently active scenario if running."""
        with self._lock:
            if not self._active_scenario:
                return None
            return dict(self._active_scenario)

    def start_scenario(
        self,
        scenario_type: str,
        target_component: Optional[str] = None,
        entry_point: Optional[str] = None,
        intensity: float = 3.0,
        auto_progress: bool = True,
        is_distributed: bool = False,
        attacker_sources: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Initiate attack scenario and launch asynchronous state progression."""
        with self._lock:
            # Check for Normal Operation request
            raw_type = scenario_type.strip().lower()
            if raw_type in ("normal", "normal operation", "nominal"):
                return self.reset_simulation()

            if self._active_scenario and self._state_engine.get_lifecycle_state() not in (
                ScenarioLifecycleState.NORMAL,
                ScenarioLifecycleState.RECOVERED,
                ScenarioLifecycleState.SIMULATION_STOPPED,
            ):
                return {
                    "status": "ALREADY_RUNNING",
                    "scenario_id": self._active_scenario.get("scenario_id"),
                    "message": "A scenario is currently executing. Stop or reset before starting another.",
                }

            # Check if distributed
            if "distributed" in raw_type or is_distributed:
                is_distributed = True
                if not attacker_sources:
                    attacker_sources = ["ue-camera-01", "ue-camera-02", "ue-sensor-01", "ue-sensor-02", "ue-phone-01"]

            # Lookup catalog definition with alias support
            lookup_key = SCENARIO_ALIASES.get(raw_type, scenario_type)
            scen_info = SCENARIO_CATALOG.get(lookup_key)
            if not scen_info:
                scenario_type = ScenarioType.DDOS_TRAFFIC_FLOOD.value
                scen_info = SCENARIO_CATALOG[scenario_type]
            else:
                scenario_type = lookup_key

            target = target_component or scen_info["default_target"]
            entry = entry_point or (attacker_sources[0] if attacker_sources else scen_info["default_entry"])
            scen_id = f"scen-{scenario_type.lower()}-{int(time.time())}"

            # Calculate initial elevated traffic breakdown based on attack type
            if scenario_type == ScenarioType.SUSPICIOUS_UE_ACTIVITY or "slow" in raw_type:
                init_mal = round(12.0 * intensity, 1)
                pps = round(1200.0 + (350.0 * intensity), 0)
            elif scenario_type == ScenarioType.AUTH_ANOMALY:
                init_mal = round(25.0 * intensity, 1)
                pps = round(1200.0 + (5500.0 * intensity), 0)
            elif is_distributed:
                init_mal = round(75.0 * intensity, 1)
                pps = round(1200.0 + (5800.0 * intensity), 0)
            else:
                init_mal = round(45.0 * intensity, 1)
                pps = round(1200.0 + (2800.0 * intensity), 0)

            self._state_engine.update_traffic_breakdown(
                normal_traffic_mbps=75.0,
                current_traffic_mbps=round(75.0 + init_mal, 1),
                malicious_traffic_mbps=init_mal,
                legitimate_traffic_mbps=75.0,
                packet_rate_pps=pps,
                malicious_blocked_mbps=0.0,
                collateral_dropped_mbps=0.0,
                legitimate_preserved_pct=100.0,
            )

            self._stop_event.clear()
            self._pause_event.clear()
            self._current_step = 0
            self._start_time = time.time()

            self._active_scenario = {
                "scenario_id": scen_id,
                "scenario_type": scenario_type,
                "name": ("Distributed " if is_distributed and "Distributed" not in scen_info["name"] else "") + scen_info["name"],
                "description": scen_info["description"],
                "target_component": target,
                "entry_point": entry,
                "affected_slice": scen_info["affected_slice"],
                "intensity": intensity,
                "start_time": datetime.now(timezone.utc).isoformat(),
                "step": 0,
                "is_distributed": is_distributed,
                "attacker_sources": attacker_sources or [entry],
            }

            # Set initial lifecycle state
            self._state_engine._active_scenario_id = scen_id
            self._state_engine.set_lifecycle_state(ScenarioLifecycleState.ATTACK_INITIATED)

            # Record event
            self._state_engine.record_event(
                event_type="SCENARIO_STARTED",
                source="scenario_engine",
                component_id=entry,
                scenario_id=scen_id,
                severity="WARNING",
                status="INITIATED",
                description=f"Cyber attack scenario '{self._active_scenario['name']}' initiated (distributed={is_distributed}).",
                payload=self._active_scenario,
            )

            # Compute initial attack propagation & blast radius
            components = self._state_engine.get_components()
            connections = self._state_engine.get_connections()
            prop_result = self._propagation_engine.compute_propagation(
                scenario_id=scen_id,
                entry_point=entry,
                target_component=target,
                components=components,
                connections=connections,
                traffic_intensity_multiplier=intensity,
                is_distributed=is_distributed,
                attacker_sources=attacker_sources,
            )
            self._state_engine.set_propagation_result(prop_result)

            if auto_progress:
                self._worker_thread = threading.Thread(
                    target=self._run_progression_worker,
                    daemon=True,
                    name=f"ScenarioWorker-{scen_id}",
                )
                self._worker_thread.start()

            return {
                "status": "STARTED",
                "scenario_id": scen_id,
                "scenario_type": scenario_type,
                "target_component": target,
                "entry_point": entry,
                "propagation": prop_result.model_dump(),
            }

    def _run_progression_worker(self) -> None:
        """Background worker that smoothly steps through attack phases."""
        logger.info("Scenario progression worker started")
        steps = [
            (ScenarioLifecycleState.SUSPICIOUS_ACTIVITY, 2.0),
            (ScenarioLifecycleState.ANALYSING, 2.5),
            (ScenarioLifecycleState.THREAT_DETECTED, 2.5),
        ]

        for next_state, delay_sec in steps:
            # Check stop/pause
            elapsed = 0.0
            tick = 0.2
            while elapsed < delay_sec:
                if self._stop_event.is_set():
                    logger.info("Scenario worker received stop signal")
                    return
                while self._pause_event.is_set():
                    if self._stop_event.is_set():
                        return
                    time.sleep(0.2)
                time.sleep(tick)
                elapsed += tick

            with self._lock:
                if self._stop_event.is_set():
                    return
                self.step_progression(next_state)

        logger.info("Scenario reached THREAT_DETECTED phase, waiting for operator or automated mitigation")

    def step_progression(self, target_state: Optional[ScenarioLifecycleState] = None) -> Dict[str, Any]:
        """Advance one phase in the attack lifecycle, updating metrics and graph state."""
        with self._lock:
            if not self._active_scenario:
                return {"status": "NO_ACTIVE_SCENARIO"}

            current_lifecycle = self._state_engine.get_lifecycle_state()
            scen_type = self._active_scenario["scenario_type"]
            catalog_entry = SCENARIO_CATALOG.get(scen_type, {})
            target = self._active_scenario["target_component"]
            entry = self._active_scenario["entry_point"]
            intensity = self._active_scenario.get("intensity", 3.0)

            # Determine next lifecycle state
            if target_state:
                next_lifecycle = target_state
            else:
                transitions = {
                    ScenarioLifecycleState.ATTACK_INITIATED: ScenarioLifecycleState.SUSPICIOUS_ACTIVITY,
                    ScenarioLifecycleState.SUSPICIOUS_ACTIVITY: ScenarioLifecycleState.ANALYSING,
                    ScenarioLifecycleState.ANALYSING: ScenarioLifecycleState.THREAT_DETECTED,
                    ScenarioLifecycleState.THREAT_DETECTED: ScenarioLifecycleState.MITIGATING,
                    ScenarioLifecycleState.MITIGATING: ScenarioLifecycleState.VERIFYING_MITIGATION,
                    ScenarioLifecycleState.VERIFYING_MITIGATION: ScenarioLifecycleState.RECOVERED,
                }
                next_lifecycle = transitions.get(current_lifecycle, current_lifecycle)

            self._state_engine.set_lifecycle_state(next_lifecycle)
            self._current_step += 1
            self._active_scenario["step"] = self._current_step

            # Update metrics based on phase
            if next_lifecycle == ScenarioLifecycleState.SUSPICIOUS_ACTIVITY:
                self._apply_suspicious_activity_effects(entry, target, intensity)
            elif next_lifecycle == ScenarioLifecycleState.ANALYSING:
                self._apply_analysing_effects(entry, target, intensity)
            elif next_lifecycle == ScenarioLifecycleState.THREAT_DETECTED:
                self._apply_threat_detected_effects(entry, target, intensity, catalog_entry)

            return {
                "status": "ADVANCED",
                "lifecycle_state": next_lifecycle.value,
                "step": self._current_step,
            }

    def _apply_suspicious_activity_effects(self, entry: str, target: str, intensity: float) -> None:
        """Slight elevation in metrics at entry point and connecting links."""
        # Update entry component
        self._state_engine.update_component(
            entry,
            security_status=SecurityStatus.SUSPICIOUS,
            traffic_volume_mbps=round(35.0 * intensity, 2),
            latency_ms=8.5,
        )
        # Update connecting link
        connections = self._state_engine.get_connections()
        for cid, conn in connections.items():
            if conn.source == entry or conn.destination == entry:
                self._state_engine.update_connection(
                    cid,
                    utilization_mbps=min(conn.capacity_mbps, conn.utilization_mbps * 2.5),
                    security_status="SUSPICIOUS_TRAFFIC",
                )

        # Telemetry metric
        self._state_engine.record_telemetry(
            TelemetryMetric(
                metric_name="ingress_bandwidth_anomaly",
                value=round(35.0 * intensity, 2),
                unit="Mbps",
                component_id=entry,
                classification=DataClassification.SIMULATED,
            )
        )

        # Update real-time traffic breakdown
        mal_rate = round(110.0 * intensity, 1)
        self._state_engine.update_traffic_breakdown(
            normal_traffic_mbps=75.0,
            current_traffic_mbps=round(75.0 + mal_rate, 1),
            malicious_traffic_mbps=mal_rate,
            legitimate_traffic_mbps=74.5,
            packet_rate_pps=round(1200.0 + (5500.0 * intensity), 0),
        )

    def _apply_analysing_effects(self, entry: str, target: str, intensity: float) -> None:
        """Deepening impact reaching target component and adjacent nodes."""
        self._state_engine.update_component(
            target,
            security_status=SecurityStatus.SUSPICIOUS,
            cpu_utilization_pct=min(95.0, 30.0 + 15.0 * intensity),
            memory_utilization_pct=min(90.0, 35.0 + 10.0 * intensity),
            latency_ms=18.0 * intensity,
            packet_loss_pct=min(15.0, 1.5 * intensity),
        )

        self._state_engine.record_telemetry(
            TelemetryMetric(
                metric_name="target_cpu_drift",
                value=min(95.0, 30.0 + 15.0 * intensity),
                unit="%",
                component_id=target,
                classification=DataClassification.SIMULATED,
            )
        )

    def _apply_threat_detected_effects(
        self,
        entry: str,
        target: str,
        intensity: float,
        catalog_entry: Dict[str, Any],
    ) -> None:
        """Peak attack impact: degraded operational health, alarms, and AI detection verdict."""
        peak_lat = catalog_entry.get("details", {}).get("target_latency_ms", 65.0)
        peak_loss = catalog_entry.get("details", {}).get("target_packet_loss_pct", 18.0)
        peak_bw = catalog_entry.get("details", {}).get("peak_bandwidth_mbps", 600.0)

        # Mark target as ATTACKED or COMPROMISED
        sec_status = (
            SecurityStatus.COMPROMISED
            if catalog_entry.get("scenario_type") == ScenarioType.GATEWAY_COMPROMISE
            else SecurityStatus.ATTACKED
        )

        self._state_engine.update_component(
            target,
            operational_status=OperationalStatus.DEGRADED,
            security_status=sec_status,
            health_score=round(max(15.0, 100.0 - (20.0 * intensity)), 1),
            cpu_utilization_pct=min(98.5, 45.0 + (12.0 * intensity)),
            memory_utilization_pct=min(92.0, 40.0 + (10.0 * intensity)),
            traffic_volume_mbps=round(peak_bw, 1),
            latency_ms=round(peak_lat, 1),
            packet_loss_pct=round(peak_loss, 2),
        )

        # Degrade affected links
        connections = self._state_engine.get_connections()
        for cid, conn in connections.items():
            if conn.source == target or conn.destination == target:
                self._state_engine.update_connection(
                    cid,
                    connection_status=ConnectionStatus.CONGESTED,
                    utilization_mbps=min(conn.capacity_mbps, conn.capacity_mbps * 0.88),
                    latency_ms=round(peak_lat * 0.8, 1),
                    packet_loss_pct=round(peak_loss * 0.75, 2),
                    security_status="SATURATED",
                )

        # Degrade target slice if specific
        aff_slice = catalog_entry.get("affected_slice", "ALL")
        if aff_slice != "ALL":
            self._state_engine.update_slice(
                aff_slice,
                current_throughput_mbps=round(peak_bw, 1),
                current_latency_ms=round(peak_lat, 1),
                current_packet_loss_pct=round(peak_loss, 2),
                security_state="DEGRADED",
            )

        # Register ThreatDetectionResult with explainability
        threat = ThreatDetectionResult(
            threat_id=f"thr-{int(time.time())}",
            threat_category=catalog_entry.get("name", "Unknown Threat"),
            severity=catalog_entry.get("severity", "HIGH"),
            confidence=catalog_entry.get("confidence", 0.94),
            target_component=target,
            target_slice=aff_slice,
            explanation=(
                f"Multi-engine AI detection confirmed {catalog_entry.get('name')}. "
                f"Symptom: High packet loss ({peak_loss}%) and anomalous latency ({peak_lat}ms) "
                f"detected via {catalog_entry.get('expected_detection', 'AI_FUSION')} with high confidence."
            ),
            detection_source=catalog_entry.get("expected_detection", "AI_FUSION"),
            raw_anomaly_score=round(0.85 + (0.03 * intensity), 3),
            calibrated_percentile=99.6,
            model_information={
                "model_family": catalog_entry.get("expected_detection"),
                "attack_vector": catalog_entry.get("details", {}).get("attack_vector"),
                "features_flagged": ["packet_loss_ratio", "inter_arrival_cv", "bandwidth_mbps"],
            },
        )
        self._state_engine.record_threat(threat)

        # Update peak malicious traffic breakdown according to attack type
        scen_type = catalog_entry.get("scenario_type")
        is_dist = self._active_scenario.get("is_distributed", False) if self._active_scenario else False
        if scen_type == ScenarioType.SUSPICIOUS_UE_ACTIVITY:
            peak_mal = round(28.0 * intensity, 1)
            pps = round(1200.0 + (850.0 * intensity), 0)
            legit_mbps = 74.2
            legit_pct = 98.9
        elif scen_type == ScenarioType.AUTH_ANOMALY:
            peak_mal = round(65.0 * intensity, 1)
            pps = round(1200.0 + (28500.0 * intensity), 0)
            legit_mbps = 73.5
            legit_pct = 98.0
        elif is_dist:
            peak_mal = round(240.0 * intensity, 1)
            pps = round(1200.0 + (19500.0 * intensity), 0)
            legit_mbps = 70.5
            legit_pct = 94.0
        else:
            peak_mal = round(175.0 * intensity, 1)
            pps = round(1200.0 + (14500.0 * intensity), 0)
            legit_mbps = 71.8
            legit_pct = 95.7

        self._state_engine.update_traffic_breakdown(
            normal_traffic_mbps=75.0,
            current_traffic_mbps=round(75.0 + peak_mal, 1),
            malicious_traffic_mbps=peak_mal,
            legitimate_traffic_mbps=legit_mbps,
            packet_rate_pps=pps,
            legitimate_preserved_pct=legit_pct,
        )

        # Policy Decision Engine: Generate actionable mitigation recommendation
        rec_id = f"rec-{int(time.time())}"
        scen_type = catalog_entry.get("scenario_type")
        if scen_type == ScenarioType.DDOS_TRAFFIC_FLOOD:
            prop_action = MitigationActionType.RATE_LIMITING
            reason = "High-volume UDP/GTP-U flood saturating UPF user-plane ingress interface."
            exp_effect = "Enforce token-bucket bandwidth throttle to cap malicious packet rate while preserving legitimate PDU sessions."
            side_eff = "Minor buffer queuing latency during peak burst traffic."
            risk = "LOW"
        elif scen_type == ScenarioType.AUTH_ANOMALY:
            prop_action = MitigationActionType.RATE_LIMITING
            reason = "Anomalous N2/NGAP signaling request flood targeting AMF/AUSF."
            exp_effect = "Throttle unauthenticated 5G-AKA registration bursts."
            side_eff = "New device initial registration delay up to 1.5 seconds."
            risk = "MEDIUM"
        elif scen_type == ScenarioType.SLICE_RESOURCE_ABUSE:
            prop_action = MitigationActionType.SLICE_PROTECTION
            reason = "Bandwidth hogging on eMBB slice starving URLLC mission-critical allocation."
            exp_effect = "Enforce PCF S-NSSAI bandwidth quotas and prioritize URLLC slices."
            side_eff = "eMBB non-critical video streaming reduced to standard definition."
            risk = "LOW"
        elif scen_type == ScenarioType.SUSPICIOUS_UE_ACTIVITY:
            prop_action = MitigationActionType.SUSPICIOUS_SOURCE_ISOLATION
            reason = "Compromised UE conducting internal subnet scanning and unauthorized lateral probing."
            exp_effect = "Immediately revoke radio access and isolate rogue device from 5G core."
            side_eff = "Device loses all 5G network connectivity."
            risk = "LOW"
        else:
            prop_action = MitigationActionType.TRAFFIC_RESTRICTION
            reason = f"Security anomaly detected on {target} exceeding safety envelope."
            exp_effect = "Filter and drop malformed packets matching anomaly vector."
            side_eff = "Zero impact on conforming legitimate flows."
            risk = "LOW"

        rec = MitigationRecommendation(
            recommendation_id=rec_id,
            attack_type=catalog_entry.get("name", "Unknown Threat"),
            proposed_action=prop_action,
            reason=reason,
            target_component=target,
            target_slice=aff_slice if aff_slice != "ALL" else None,
            expected_effect=exp_effect,
            potential_side_effects=side_eff,
            collateral_risk=risk,
            parameters={"intensity": intensity, "rate_limit_mbps": 100.0},
            approved=False,
        )
        self._state_engine.add_recommendation(rec)

        # In AUTOMATIC DEFENCE mode, immediately approve and execute
        if self._state_engine.get_defence_mode() == "AUTOMATIC":
            from .mitigation import mitigation_engine
            self._state_engine.approve_recommendation(rec_id)
            mitigation_engine.apply_mitigation(
                action_type=prop_action.value,
                target_component=target,
                target_slice=aff_slice if aff_slice != "ALL" else None,
                parameters={"auto_defence": True, "intensity": intensity},
                auto_verify=True,
            )

    def pause_scenario(self) -> Dict[str, Any]:
        """Pause active scenario progression."""
        with self._lock:
            if not self._active_scenario:
                return {"status": "NO_ACTIVE_SCENARIO"}
            self._pause_event.set()
            return {"status": "PAUSED", "scenario_id": self._active_scenario.get("scenario_id")}

    def resume_scenario(self) -> Dict[str, Any]:
        """Resume paused scenario progression."""
        with self._lock:
            if not self._active_scenario:
                return {"status": "NO_ACTIVE_SCENARIO"}
            self._pause_event.clear()
            return {"status": "RESUMED", "scenario_id": self._active_scenario.get("scenario_id")}

    def stop_scenario(self) -> Dict[str, Any]:
        """Stop active scenario execution."""
        with self._lock:
            self._stop_event.set()
            self._pause_event.clear()
            if not self._active_scenario:
                return {"status": "NO_ACTIVE_SCENARIO"}

            scen_id = self._active_scenario.get("scenario_id")
            self._state_engine.set_lifecycle_state(ScenarioLifecycleState.SIMULATION_STOPPED)
            self._state_engine.record_event(
                event_type="SCENARIO_STOPPED",
                source="scenario_engine",
                scenario_id=scen_id,
                severity="INFO",
                status="STOPPED",
                description="Active attack simulation terminated by operator.",
            )
            self._active_scenario = None
            return {"status": "STOPPED", "scenario_id": scen_id}

    def reset_simulation(self) -> Dict[str, Any]:
        """Stop any active scenario and reset the global state engine to nominal."""
        with self._lock:
            self._stop_event.set()
            self._pause_event.clear()
            self._active_scenario = None
            self._current_step = 0
            self._state_engine.reset_to_nominal()
            return {"status": "RESET_SUCCESSFUL", "state_version": self._state_engine.get_state_version()}


# Global singleton instance
scenario_engine = ScenarioSimulationEngine()
# CommShield AI Core
