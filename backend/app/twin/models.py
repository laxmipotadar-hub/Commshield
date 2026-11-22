"""Data models and schemas for CommShield AI Private 5G Digital Twin.

Defines the complete structural representation for:
- 5G network components (RAN, Core, Infrastructure, Slices)
- Control-plane and user-plane connections
- High-resolution telemetry items with strict provenance classification
- Attack simulation lifecycle states and parameters
- Graph-based attack propagation and blast radius analysis
- AI threat detection and classification
- Multi-tier mitigation actions and recovery tracking
- Isolated What-If scenario experiments
- Quantitative resilience scoring with documented formulas
- Immutable timestamped event logging
"""

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class DataClassification(str, Enum):
    LIVE = "LIVE"
    BACKEND = "BACKEND"
    SIMULATED = "SIMULATED"
    DERIVED = "DERIVED"
    PREDICTED = "PREDICTED"
    TESTBED_5G = "TESTBED_5G"


class OperationalStatus(str, Enum):
    ACTIVE = "ACTIVE"
    DEGRADED = "DEGRADED"
    CRITICAL = "CRITICAL"
    ISOLATED = "ISOLATED"
    OFFLINE = "OFFLINE"


class SecurityStatus(str, Enum):
    SECURE = "SECURE"
    SUSPICIOUS = "SUSPICIOUS"
    ATTACKED = "ATTACKED"
    COMPROMISED = "COMPROMISED"
    QUARANTINED = "QUARANTINED"


class ConnectionType(str, Enum):
    CONTROL_PLANE = "CONTROL_PLANE"
    USER_PLANE = "USER_PLANE"


class ConnectionStatus(str, Enum):
    ACTIVE = "ACTIVE"
    CONGESTED = "CONGESTED"
    DEGRADED = "DEGRADED"
    DOWN = "DOWN"
    THROTTLED = "THROTTLED"


class ScenarioLifecycleState(str, Enum):
    NORMAL = "NORMAL"
    ATTACK_INITIATED = "ATTACK_INITIATED"
    SUSPICIOUS_ACTIVITY = "SUSPICIOUS_ACTIVITY"
    ANALYSING = "ANALYSING"
    THREAT_DETECTED = "THREAT_DETECTED"
    MITIGATING = "MITIGATING"
    VERIFYING_MITIGATION = "VERIFYING_MITIGATION"
    RECOVERED = "RECOVERED"
    DETECTION_FAILED = "DETECTION_FAILED"
    MITIGATION_FAILED = "MITIGATION_FAILED"
    RECOVERY_FAILED = "RECOVERY_FAILED"
    SIMULATION_STOPPED = "SIMULATION_STOPPED"


class ScenarioType(str, Enum):
    DDOS_TRAFFIC_FLOOD = "DDOS_TRAFFIC_FLOOD"
    AUTH_ANOMALY = "AUTH_ANOMALY"
    SLICE_RESOURCE_ABUSE = "SLICE_RESOURCE_ABUSE"
    UPF_OVERLOAD = "UPF_OVERLOAD"
    SUSPICIOUS_UE_ACTIVITY = "SUSPICIOUS_UE_ACTIVITY"
    GATEWAY_COMPROMISE = "GATEWAY_COMPROMISE"


class MitigationActionType(str, Enum):
    RATE_LIMITING = "RATE_LIMITING"
    TRAFFIC_RESTRICTION = "TRAFFIC_RESTRICTION"
    SUSPICIOUS_SOURCE_ISOLATION = "SUSPICIOUS_SOURCE_ISOLATION"
    SESSION_TERMINATION = "SESSION_TERMINATION"
    COMPONENT_ISOLATION = "COMPONENT_ISOLATION"
    SLICE_PROTECTION = "SLICE_PROTECTION"
    POLICY_UPDATE = "POLICY_UPDATE"


class MitigationStatus(str, Enum):
    REQUESTED = "REQUESTED"
    IN_PROGRESS = "IN_PROGRESS"
    VERIFYING = "VERIFYING"
    SUCCESSFUL = "SUCCESSFUL"
    FAILED = "FAILED"


# ---------------------------------------------------------
# Core Network Graph Components and Connections
# ---------------------------------------------------------

class NetworkComponent(BaseModel):
    """Structured representation of a single private 5G network entity."""
    id: str
    name: str
    component_type: str  # e.g., "gNodeB", "AMF", "SMF", "UPF", "UDM", "AUSF", "PCF", "UE", "EdgeNode", "Gateway"
    network_role: str    # e.g., "Radio Access", "Core Control", "Core User Plane", "Infrastructure"
    operational_status: OperationalStatus = OperationalStatus.ACTIVE
    health_score: float = 100.0  # 0.0 - 100.0
    cpu_utilization_pct: float = 15.0
    memory_utilization_pct: float = 25.0
    traffic_volume_mbps: float = 0.0
    latency_ms: float = 2.0
    packet_loss_pct: float = 0.0
    connected_components: List[str] = Field(default_factory=list)
    network_slice: Optional[str] = None  # eMBB, URLLC, mMTC, or "ALL"
    security_status: SecurityStatus = SecurityStatus.SECURE
    last_updated: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    provenance: DataClassification = DataClassification.SIMULATED
    coordinates_3d: Dict[str, float] = Field(default_factory=lambda: {"x": 0.0, "y": 0.0, "z": 0.0})
    metadata: Dict[str, Any] = Field(default_factory=dict)


class NetworkConnection(BaseModel):
    """Structured representation of a logical or physical connection in the 5G topology."""
    id: str
    source: str
    destination: str
    connection_type: ConnectionType  # CONTROL_PLANE or USER_PLANE
    direction: str = "BIDIRECTIONAL"
    protocol: str  # e.g., "N2 (SCTP/NGAP)", "N3 (GTP-U)", "N4 (PFCP)", "N11 (HTTP/2 SBI)"
    capacity_mbps: float = 1000.0
    utilization_mbps: float = 10.0
    utilization_pct: float = 1.0
    latency_ms: float = 1.5
    packet_loss_pct: float = 0.0
    connection_status: ConnectionStatus = ConnectionStatus.ACTIVE
    associated_slice: Optional[str] = None
    security_status: str = "NORMAL"  # "NORMAL", "SUSPICIOUS_TRAFFIC", "SATURATED", "ISOLATED"
    last_updated: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    provenance: DataClassification = DataClassification.SIMULATED


class NetworkSliceInfo(BaseModel):
    """Structured representation of a 3GPP S-NSSAI network slice."""
    slice_id: str  # e.g. "sst-1-sd-010203"
    name: str      # e.g. "eMBB High-Throughput"
    sst: int       # Slice/Service Type (1: eMBB, 2: URLLC, 3: mMTC)
    sd: str        # Slice Differentiator
    description: str
    allocated_bandwidth_mbps: float
    current_throughput_mbps: float
    max_latency_ms: float
    current_latency_ms: float
    target_packet_loss_pct: float
    current_packet_loss_pct: float
    active_ues_count: int
    security_state: str = "NOMINAL"
    isolation_guarantee: str = "Hardware/VLAN Encapsulated"


class TelemetryMetric(BaseModel):
    """Strictly classified metric item for network and component level telemetry."""
    metric_name: str
    value: float
    unit: str
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    component_id: Optional[str] = None
    slice_id: Optional[str] = None
    source: str = "twin_telemetry_engine"
    classification: DataClassification = DataClassification.SIMULATED


# ---------------------------------------------------------
# Attack Propagation and Blast Radius
# ---------------------------------------------------------

class AttackPropagationResult(BaseModel):
    """Graph-based blast radius and attack propagation analysis."""
    scenario_id: str
    entry_point: str
    target_component: str
    attack_path: List[str]
    directly_targeted: List[str]
    indirectly_affected: List[str]
    potentially_affected: List[str]
    unaffected: List[str]
    affected_ues: List[str]
    affected_slices: List[str]
    affected_services: List[str]
    suspicious_traffic_paths: List[str]
    containment_boundaries: List[str]
    blast_radius_score: float  # 0.0 - 100.0 (percentage of network affected)
    impact_explanation: str
    attacker_sources: List[str] = Field(default_factory=list)
    attack_paths: List[List[str]] = Field(default_factory=list)
    is_distributed: bool = False
    per_source_traffic_mbps: Dict[str, float] = Field(default_factory=dict)
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


# ---------------------------------------------------------
# AI Threat Detection Result
# ---------------------------------------------------------

class ThreatDetectionResult(BaseModel):
    """Threat detection verdict generated by CommShield AI detection engine."""
    threat_id: str
    threat_category: str
    severity: str  # "LOW", "MEDIUM", "HIGH", "CRITICAL"
    confidence: Optional[float] = None
    target_component: str
    target_slice: str
    detection_timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    explanation: str
    detection_source: str  # "AI_ISOLATION_FOREST", "AI_AUTOENCODER", "AI_FUSION", "RULE_BASED_ADWIN", "CUSUM_ACCUMULATOR"
    model_information: Dict[str, Any] = Field(default_factory=dict)
    raw_anomaly_score: Optional[float] = None
    calibrated_percentile: Optional[float] = None
    is_mitigated: bool = False


# ---------------------------------------------------------
# Mitigation and Recovery Lifecycle
# ---------------------------------------------------------

class MitigationActionRecord(BaseModel):
    """Lifecycle record for an automated or operator-approved cybersecurity mitigation."""
    action_id: str
    scenario_id: Optional[str] = None
    action_type: MitigationActionType
    target_component: str
    target_slice: Optional[str] = None
    status: MitigationStatus = MitigationStatus.REQUESTED
    start_time: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    completion_time: Optional[str] = None
    result_summary: str = "Initiating mitigation action"
    failed_reason: Optional[str] = None
    recovery_status: str = "PENDING"
    remaining_impact_pct: float = 100.0
    is_simulated: bool = True
    parameters: Dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------
# What-If Experiment
# ---------------------------------------------------------

class WhatIfExperimentRecord(BaseModel):
    """Isolated What-If hypothetical digital twin simulation."""
    experiment_id: str
    name: str
    hypothesis: str
    target_component: str
    scenario_type: str
    parameters: Dict[str, Any] = Field(default_factory=dict)
    baseline_metrics: Dict[str, float] = Field(default_factory=dict)
    predicted_metrics: Dict[str, float] = Field(default_factory=dict)
    affected_components: List[str] = Field(default_factory=list)
    impact_delta: Dict[str, float] = Field(default_factory=dict)
    assumptions: List[str] = Field(default_factory=list)
    limitations: List[str] = Field(default_factory=list)
    recommendation: str
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


# ---------------------------------------------------------
# Resilience Intelligence
# ---------------------------------------------------------

class ResilienceMetrics(BaseModel):
    """Quantitative network resilience metrics with mathematically documented formulas."""
    time_to_detect_sec: float
    time_to_mitigate_sec: float
    time_to_recover_sec: float
    service_availability_pct: float
    network_degradation_pct: float
    affected_components_count: int
    affected_slices_count: int
    residual_impact_pct: float
    resilience_score: float  # 0.0 - 100.0
    formula_documentation: str
    assessment_grade: str  # "EXCELLENT", "GOOD", "DEGRADED", "VULNERABLE"
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


# ---------------------------------------------------------
# Historical Event
# ---------------------------------------------------------

class HistoricalNetworkEvent(BaseModel):
    """Immutable, timestamped event in the Digital Twin historical record."""
    event_id: str
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    event_type: str  # e.g., "SCENARIO_STARTED", "THREAT_DETECTED", "HEALTH_DEGRADED", "MITIGATION_APPLIED"
    source: str      # e.g., "twin_scenario_engine", "commshield_ai_detector", "mitigation_engine"
    component_id: Optional[str] = None
    scenario_id: Optional[str] = None
    severity: str    # "INFO", "WARNING", "HIGH", "CRITICAL"
    status: str
    description: str
    payload: Dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------
# Cyber Defence Operations: Traffic Breakdown, Recommendations & Incidents
# ---------------------------------------------------------

class TrafficBreakdown(BaseModel):
    """Real-time split of legitimate versus malicious packet volume."""
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    normal_traffic_mbps: float = 75.0
    current_traffic_mbps: float = 75.0
    malicious_traffic_mbps: float = 0.0
    legitimate_traffic_mbps: float = 75.0
    packet_rate_pps: float = 1200.0
    malicious_blocked_mbps: float = 0.0
    collateral_dropped_mbps: float = 0.0
    legitimate_preserved_pct: float = 100.0


class MitigationRecommendation(BaseModel):
    """Actionable defence recommendation produced by policy decision engine."""
    recommendation_id: str
    attack_type: str
    proposed_action: MitigationActionType
    reason: str
    target_component: str
    target_slice: Optional[str] = None
    expected_effect: str
    potential_side_effects: str
    collateral_risk: str = "LOW"  # "LOW", "MEDIUM", "HIGH"
    parameters: Dict[str, Any] = Field(default_factory=dict)
    approved: bool = False
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class IncidentRecord(BaseModel):
    """Complete forensic incident record generated post-attack."""
    incident_id: str
    attack_type: str
    severity: str
    target_component: str
    start_time: str
    detection_time: Optional[str] = None
    mitigation_time: Optional[str] = None
    verification_time: Optional[str] = None
    recovery_time: Optional[str] = None
    affected_nodes: List[str] = Field(default_factory=list)
    applied_policies: List[str] = Field(default_factory=list)
    peak_malicious_traffic_mbps: float = 0.0
    blocked_packets_count: int = 0
    legitimate_preserved_pct: float = 100.0
    verification_status: str = "CONTAINMENT_VERIFIED"  # "CONTAINMENT_VERIFIED", "PARTIAL_MITIGATION", "MITIGATION_FAILED"
    final_outcome: str = "Recovered nominal operations"
    evidence: Dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------
# Global Digital Twin State Snapshot
# ---------------------------------------------------------

class DigitalTwinStateSnapshot(BaseModel):
    """Complete single-source-of-truth snapshot of the 5G Digital Twin."""
    version: int
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    provenance: DataClassification = DataClassification.SIMULATED
    overall_health_score: float
    active_scenario_id: Optional[str] = None
    lifecycle_state: ScenarioLifecycleState = ScenarioLifecycleState.NORMAL
    total_components_count: int
    active_ues_count: int
    network_throughput_mbps: float
    average_latency_ms: float
    average_packet_loss_pct: float
    components: Dict[str, NetworkComponent]
    connections: Dict[str, NetworkConnection]
    slices: Dict[str, NetworkSliceInfo]
    active_threats: List[ThreatDetectionResult] = Field(default_factory=list)
    active_mitigations: List[MitigationActionRecord] = Field(default_factory=list)
    active_recommendations: List[MitigationRecommendation] = Field(default_factory=list)
    active_incidents: List[IncidentRecord] = Field(default_factory=list)
    traffic_breakdown: Optional[TrafficBreakdown] = None
    recent_events: List[HistoricalNetworkEvent] = Field(default_factory=list)
    resilience: Optional[ResilienceMetrics] = None
    current_propagation: Optional[AttackPropagationResult] = None
    data_mode: str = "LIVE_SIMULATION"  # "REAL_DATASET", "LIVE_SIMULATION", "HYBRID"
    synthetic_data_enabled: bool = True
    active_slice_id: str = "sst-1-sd-010203"
    simulation_speed: float = 1.0
    defence_mode: str = "MANUAL"
    ensemble_fusion_enabled: bool = True
    data_integrity: Dict[str, Any] = Field(default_factory=dict)
# CommShield AI Core
