from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class RawCounters(BaseModel):
    model_config = ConfigDict(extra="allow")

    active_ue_count: Optional[int] = None
    registration_attempts: Optional[int] = None
    registration_failures: Optional[int] = None
    pdu_sessions_established: Optional[int] = None
    nas_messages_total: Optional[int] = None
    nas_failures: Optional[int] = None
    pfcp_association_messages: Optional[int] = None
    pfcp_failures: Optional[int] = None
    total_bytes_uplink: Optional[int] = None
    total_bytes_downlink: Optional[int] = None
    total_packets: Optional[int] = None
    gtpu_teid_count: Optional[int] = None


class RatioFeatures(BaseModel):
    model_config = ConfigDict(extra="allow")

    registrations_per_active_ue: Optional[float] = None
    nas_failure_ratio: Optional[float] = None
    pfcp_failure_ratio: Optional[float] = None
    pdu_session_rate_per_ue: Optional[float] = None
    bytes_per_session: Optional[float] = None
    packets_per_session: Optional[float] = None
    gtpu_volume_per_ue: Optional[float] = None
    ue_hash_entropy: Optional[float] = None
    new_ue_rate: Optional[float] = None


class CompositionVector(BaseModel):
    model_config = ConfigDict(extra="allow")

    registration_ratio: Optional[float] = None
    session_setup_ratio: Optional[float] = None
    failure_ratio: Optional[float] = None
    other_signalling_ratio: Optional[float] = None


class CanonicalTrafficWindow(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="allow")

    window_id: str
    slice_id: str
    nf_id: str
    window_start: datetime
    window_end: datetime
    duration_sec: int
    raw_counters: Dict[str, Any]
    ratio_features: Dict[str, Any]
    composition_vector: Dict[str, Any]


class PaginatedWindowsResponse(BaseModel):
    items: List[CanonicalTrafficWindow]
    total: int
    limit: int
    offset: int


class AttributionSummary(BaseModel):
    verdict: str
    abstain_reason: Optional[str] = None


class ExplainabilityResponse(BaseModel):
    window_id: str
    slice_id: str
    nf_id: str
    is_anomalous: bool
    fused_percentile: float
    shap_values: Dict[str, float]
    hypothesis: str
    attribution_summary: AttributionSummary
