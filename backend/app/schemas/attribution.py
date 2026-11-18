from typing import Any, Dict, List, Optional
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class ProportionalGrowthTest(BaseModel):
    scaling_factor_k: float
    jsd_divergence: float
    jsd_null_threshold_99th: float
    passed: bool


class AttributionOutput(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="allow")

    window_id: str
    slice_id: str
    drift_detected: bool
    verdict: str
    abstain_reason: Optional[str] = None
    confidence_type: str = "evidence_category"
    proportional_growth_test: ProportionalGrowthTest
    supporting_signals: Dict[str, Any]
    action: Optional[str] = None
    action_recommendation: str
    decision_trace_id: Optional[str] = None
    attributor_type: Optional[str] = "rules"


class AttributionAnalyzeRequest(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="allow")

    window_id: Optional[str] = None
    slice_id: Optional[str] = None
    window: Optional[Dict[str, Any]] = None
    scenario: Optional[str] = None
    force_drift: Optional[bool] = False


class DriftEventItem(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="allow")

    id: str
    window_id: str
    slice_id: str
    event_time: datetime
    volume_multiplier: float
    drift_detected: bool
    verdict: str
    abstain_reason: Optional[str] = None
    action: str
    decision_trace_id: Optional[str] = None
    attribution: Optional[Dict[str, Any]] = None


class DecisionTraceStep(BaseModel):
    step_name: str
    description: str
    timestamp: datetime
    details: Dict[str, Any]


class DecisionTraceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="allow")

    id: str
    window_id: str
    slice_id: str
    alert_id: Optional[str] = None
    drift_event_id: Optional[str] = None
    verdict: str
    action: str
    steps: List[Dict[str, Any]]
    created_at: datetime
