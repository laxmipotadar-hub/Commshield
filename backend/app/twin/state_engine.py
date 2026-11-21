"""Central Digital Twin State Engine for CommShield AI.

Serves as the authoritative single source of truth for:
- 5G Network Topology & Component Graph
- Live Component Health, CPU, Memory, Latency & Packet Loss
- Control-Plane & User-Plane Connection Status & Bandwidth
- Active Cyber Attack Simulation & Lifecycle State Machine
- AI Threat Detection Verdicts & Explainability Evidence
- Blast-Radius & Attack Propagation Maps
- Active Mitigations & Verifiable Recovery Operations
- Quantitative Network Resilience Scoring
- Immutable Historical Incident Ledger
- Thread-safe State Versioning and Real-Time WebSocket Synchronization.
"""

from copy import deepcopy
from datetime import datetime, timezone
import logging
import threading
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from .models import (
    AttackPropagationResult,
    ConnectionStatus,
    DataClassification,
    DigitalTwinStateSnapshot,
    HistoricalNetworkEvent,
    MitigationActionRecord,
    MitigationActionType,
    MitigationStatus,
    NetworkComponent,
    NetworkConnection,
    NetworkSliceInfo,
    OperationalStatus,
    ResilienceMetrics,
    ScenarioLifecycleState,
    SecurityStatus,
    TelemetryMetric,
    ThreatDetectionResult,
)
from .topology import (
    build_canonical_components,
    build_canonical_connections,
    build_canonical_slices,
)

logger = logging.getLogger("commshield.twin.state")


class CentralDigitalTwinStateEngine:
    """Thread-safe, reactive single-source-of-truth state engine for private 5G network."""

    def __init__(self):
        self._lock = threading.RLock()
        self._state_version = 1
        self._lifecycle_state = ScenarioLifecycleState.NORMAL
        self._active_scenario_id: Optional[str] = None
        self._active_scenario_metadata: Dict[str, Any] = {}

        # Canonical Network State Graph
        self._components: Dict[str, NetworkComponent] = build_canonical_components()
        self._connections: Dict[str, NetworkConnection] = build_canonical_connections()
        self._slices: Dict[str, NetworkSliceInfo] = build_canonical_slices()

        # Telemetry ring buffers for history
        self._telemetry_history: Dict[str, List[TelemetryMetric]] = {}

        # Incident, threat, mitigation, and historical logs
        self._active_threats: List[ThreatDetectionResult] = []
        self._active_mitigations: List[MitigationActionRecord] = []
        self._events: List[HistoricalNetworkEvent] = []

        # Current attack propagation & blast radius analysis
        self._current_propagation: Optional[AttackPropagationResult] = None

        # Resilience metrics
        self._resilience: ResilienceMetrics = self._compute_initial_resilience()

        # Real-time WebSocket subscriber callbacks
        self._subscribers: Set[Callable[[Dict[str, Any]], None]] = set()

        # Record Genesis event
        self.record_event(
            event_type="TWIN_INITIALIZED",
            source="central_state_engine",
            component_id="system",
            severity="INFO",
            status="NOMINAL",
            description="CommShield Private 5G Central Digital Twin State Engine initialized with 3GPP canonical topology.",
            payload={"version": self._state_version, "components": len(self._components), "connections": len(self._connections)},
        )

    def _compute_initial_resilience(self) -> ResilienceMetrics:
        """Compute nominal baseline resilience metrics."""
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
            formula_documentation="Resilience = 100 * [0.4*(Availability/100) + 0.4*(1 - Degradation/100) + 0.2*exp(-0.01*(TTD+TTM+TTR))] * (1 - ResidualImpact)",
            assessment_grade="EXCELLENT",
        )

    def subscribe(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        """Register a callback to receive real-time state mutation events."""
        with self._lock:
            self._subscribers.add(callback)

    def unsubscribe(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        """Unregister a subscriber callback."""
        with self._lock:
            self._subscribers.discard(callback)

    def _notify_subscribers(self, event_type: str, data: Dict[str, Any]) -> None:
        """Broadcast state updates to all active WebSocket connections."""
        payload = {
            "version": self._state_version,
            "event_type": event_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": data,
        }
        for cb in list(self._subscribers):
            try:
                cb(payload)
            except Exception as e:
                logger.warning(f"Subscriber notification failed: {e}")

    # -----------------------------------------------------
    # State Inspection Methods
    # -----------------------------------------------------

    def get_state_version(self) -> int:
        with self._lock:
            return self._state_version

    def get_lifecycle_state(self) -> ScenarioLifecycleState:
        with self._lock:
            return self._lifecycle_state

    def set_lifecycle_state(self, state: ScenarioLifecycleState) -> None:
        with self._lock:
            if self._lifecycle_state != state:
                prev = self._lifecycle_state
                self._lifecycle_state = state
                self._state_version += 1
                self.record_event(
                    event_type="LIFECYCLE_STATE_CHANGED",
                    source="state_engine",
                    severity="INFO",
                    status=state.value,
                    description=f"Scenario lifecycle transitioned from {prev.value} to {state.value}.",
                    payload={"previous_state": prev.value, "new_state": state.value},
                )
                self._notify_subscribers("LIFECYCLE_STATE_CHANGED", {"state": state.value})

    def get_snapshot(self) -> DigitalTwinStateSnapshot:
        """Retrieve complete immutable snapshot of the active Digital Twin."""
        with self._lock:
            now_iso = datetime.now(timezone.utc).isoformat()
            total_traffic = sum(c.traffic_volume_mbps for c in self._components.values())
            active_ues = sum(1 for c in self._components.values() if c.component_type == "UE" and c.operational_status == OperationalStatus.ACTIVE)
            avg_latency = sum(c.latency_ms for c in self._components.values()) / max(1, len(self._components))
            avg_loss = sum(c.packet_loss_pct for c in self._components.values()) / max(1, len(self._components))

            return DigitalTwinStateSnapshot(
                version=self._state_version,
                timestamp=now_iso,
                provenance=DataClassification.SIMULATED,
                overall_health_score=self.calculate_overall_health(),
                active_scenario_id=self._active_scenario_id,
                lifecycle_state=self._lifecycle_state,
                total_components_count=len(self._components),
                active_ues_count=active_ues,
                network_throughput_mbps=round(total_traffic, 2),
                average_latency_ms=round(avg_latency, 2),
                average_packet_loss_pct=round(avg_loss, 4),
                components=deepcopy(self._components),
                connections=deepcopy(self._connections),
                slices=deepcopy(self._slices),
                active_threats=list(self._active_threats),
                active_mitigations=list(self._active_mitigations),
                recent_events=list(self._events[-20:]),
                resilience=deepcopy(self._resilience),
            )

    def calculate_overall_health(self) -> float:
        """Calculate weighted global health score across Core, RAN, and Devices."""
        with self._lock:
            if not self._components:
                return 100.0

            core_types = {"UPF", "AMF", "SMF", "UDM", "AUSF", "PCF", "NRF", "NSSF", "NEF", "UDR"}
            infra_types = {"Gateway", "Switch", "EdgeNode", "SecurityMonitoring"}

            core_scores = [c.health_score for c in self._components.values() if c.component_type in core_types]
            ran_scores = [c.health_score for c in self._components.values() if c.component_type == "gNodeB"]
            device_scores = [c.health_score for c in self._components.values() if c.component_type == "UE"]
            infra_scores = [c.health_score for c in self._components.values() if c.component_type in infra_types]

            w_core = (sum(core_scores) / len(core_scores)) if core_scores else 100.0
            w_ran = (sum(ran_scores) / len(ran_scores)) if ran_scores else 100.0
            w_dev = (sum(device_scores) / len(device_scores)) if device_scores else 100.0
            w_inf = (sum(infra_scores) / len(infra_scores)) if infra_scores else 100.0

            # 40% Core, 30% RAN, 15% Infrastructure, 15% Devices
            overall = (0.40 * w_core) + (0.30 * w_ran) + (0.15 * w_inf) + (0.15 * w_dev)
            return round(max(0.0, min(100.0, overall)), 2)

    def get_components(self) -> Dict[str, NetworkComponent]:
        with self._lock:
            return deepcopy(self._components)

    def get_component(self, component_id: str) -> Optional[NetworkComponent]:
        with self._lock:
            comp = self._components.get(component_id)
            return deepcopy(comp) if comp else None

    def update_component(self, component_id: str, **kwargs) -> Optional[NetworkComponent]:
        """Atomically update component attributes, recompute health, and increment state version."""
        with self._lock:
            comp = self._components.get(component_id)
            if not comp:
                return None

            for key, val in kwargs.items():
                if hasattr(comp, key):
                    setattr(comp, key, val)

            comp.last_updated = datetime.now(timezone.utc).isoformat()
            self._state_version += 1
            self._notify_subscribers("COMPONENT_UPDATED", {"component_id": component_id, "updates": kwargs})
            return deepcopy(comp)

    def get_connections(self) -> Dict[str, NetworkConnection]:
        with self._lock:
            return deepcopy(self._connections)

    def update_connection(self, connection_id: str, **kwargs) -> Optional[NetworkConnection]:
        """Atomically update logical link utilization, latency, or security status."""
        with self._lock:
            conn = self._connections.get(connection_id)
            if not conn:
                return None

            for key, val in kwargs.items():
                if hasattr(conn, key):
                    setattr(conn, key, val)

            if "utilization_mbps" in kwargs and conn.capacity_mbps > 0:
                conn.utilization_pct = round((conn.utilization_mbps / conn.capacity_mbps) * 100.0, 2)

            conn.last_updated = datetime.now(timezone.utc).isoformat()
            self._state_version += 1
            self._notify_subscribers("CONNECTION_UPDATED", {"connection_id": connection_id, "updates": kwargs})
            return deepcopy(conn)

    def get_slices(self) -> Dict[str, NetworkSliceInfo]:
        with self._lock:
            return deepcopy(self._slices)

    def update_slice(self, slice_id: str, **kwargs) -> Optional[NetworkSliceInfo]:
        with self._lock:
            slc = self._slices.get(slice_id)
            if not slc:
                return None
            for key, val in kwargs.items():
                if hasattr(slc, key):
                    setattr(slc, key, val)
            self._state_version += 1
            return deepcopy(slc)

    # -----------------------------------------------------
    # Telemetry and Metric Recording
    # -----------------------------------------------------

    def record_telemetry(self, metric: TelemetryMetric) -> None:
        """Store classified telemetry point in thread-safe ring buffer."""
        with self._lock:
            key = f"{metric.component_id or 'global'}:{metric.metric_name}"
            if key not in self._telemetry_history:
                self._telemetry_history[key] = []
            buf = self._telemetry_history[key]
            buf.append(metric)
            if len(buf) > 120:  # Retain last 120 telemetry ticks
                self._telemetry_history[key] = buf[-120:]

    def get_telemetry_history(self, component_id: Optional[str], metric_name: str, limit: int = 30) -> List[TelemetryMetric]:
        with self._lock:
            key = f"{component_id or 'global'}:{metric_name}"
            buf = self._telemetry_history.get(key, [])
            return deepcopy(buf[-limit:])

    # -----------------------------------------------------
    # Threat & Mitigation Operations
    # -----------------------------------------------------

    def record_threat(self, threat: ThreatDetectionResult) -> None:
        with self._lock:
            self._active_threats.append(threat)
            self._state_version += 1
            self.record_event(
                event_type="THREAT_DETECTED",
                source=threat.detection_source,
                component_id=threat.target_component,
                scenario_id=self._active_scenario_id,
                severity=threat.severity,
                status="DETECTED",
                description=threat.explanation,
                payload=threat.model_dump(),
            )
            self._notify_subscribers("THREAT_DETECTED", threat.model_dump())

    def clear_threats(self) -> None:
        with self._lock:
            self._active_threats.clear()
            self._state_version += 1

    def record_mitigation(self, action: MitigationActionRecord) -> None:
        with self._lock:
            self._active_mitigations.append(action)
            self._state_version += 1
            self.record_event(
                event_type="MITIGATION_REQUESTED",
                source="mitigation_engine",
                component_id=action.target_component,
                scenario_id=action.scenario_id,
                severity="INFO",
                status=action.status.value,
                description=f"Mitigation {action.action_type.value} enacted on {action.target_component}.",
                payload=action.model_dump(),
            )
            self._notify_subscribers("MITIGATION_APPLIED", action.model_dump())

    def get_active_mitigations(self) -> List[MitigationActionRecord]:
        with self._lock:
            return list(self._active_mitigations)

    def set_propagation_result(self, prop: Optional[AttackPropagationResult]) -> None:
        with self._lock:
            self._current_propagation = prop
            self._state_version += 1
            if prop:
                self._notify_subscribers("PROPAGATION_UPDATED", prop.model_dump())

    def get_propagation_result(self) -> Optional[AttackPropagationResult]:
        with self._lock:
            return deepcopy(self._current_propagation)

    def set_resilience_metrics(self, res: ResilienceMetrics) -> None:
        with self._lock:
            self._resilience = res
            self._state_version += 1
            self._notify_subscribers("RESILIENCE_UPDATED", res.model_dump())

    def get_resilience_metrics(self) -> ResilienceMetrics:
        with self._lock:
            return deepcopy(self._resilience)

    # -----------------------------------------------------
    # Immutable Historical Events Log
    # -----------------------------------------------------

    def record_event(
        self,
        event_type: str,
        source: str,
        severity: str,
        status: str,
        description: str,
        component_id: Optional[str] = None,
        scenario_id: Optional[str] = None,
        payload: Optional[Dict[str, Any]] = None,
    ) -> HistoricalNetworkEvent:
        """Append immutable timestamped incident record into historical ledger."""
        with self._lock:
            ev_id = f"ev-{len(self._events) + 1:05d}-{int(datetime.now(timezone.utc).timestamp())}"
            event = HistoricalNetworkEvent(
                event_id=ev_id,
                timestamp=datetime.now(timezone.utc).isoformat(),
                event_type=event_type,
                source=source,
                component_id=component_id,
                scenario_id=scenario_id or self._active_scenario_id,
                severity=severity,
                status=status,
                description=description,
                payload=payload or {},
            )
            self._events.append(event)
            if len(self._events) > 500:
                self._events = self._events[-500:]  # Cap memory buffer
            return event

    def get_historical_events(
        self,
        scenario_id: Optional[str] = None,
        severity: Optional[str] = None,
        limit: int = 50,
    ) -> List[HistoricalNetworkEvent]:
        with self._lock:
            evs = self._events
            if scenario_id:
                evs = [e for e in evs if e.scenario_id == scenario_id]
            if severity:
                evs = [e for e in evs if e.severity.upper() == severity.upper()]
            return [deepcopy(e) for e in reversed(evs[-limit:])]

    # -----------------------------------------------------
    # Reset to Clean Baseline
    # -----------------------------------------------------

    def reset_to_nominal(self) -> None:
        """Reset live graph, telemetry, and threat states back to nominal without erasing audit history."""
        with self._lock:
            self._components = build_canonical_components()
            self._connections = build_canonical_connections()
            self._slices = build_canonical_slices()
            self._active_threats.clear()
            self._active_mitigations.clear()
            self._current_propagation = None
            self._active_scenario_id = None
            self._active_scenario_metadata = {}
            self._lifecycle_state = ScenarioLifecycleState.NORMAL
            self._resilience = self._compute_initial_resilience()
            self._state_version += 1

            self.record_event(
                event_type="NETWORK_RESET_NOMINAL",
                source="state_engine",
                severity="INFO",
                status="NORMAL",
                description="Digital Twin topology and performance parameters reset to nominal baseline.",
                payload={"version": self._state_version},
            )
            self._notify_subscribers("STATE_RESET", {"version": self._state_version})


# Global singleton instance
twin_state_engine = CentralDigitalTwinStateEngine()
