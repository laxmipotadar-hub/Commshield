from typing import Any, Dict, Optional
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
    proportional_growth_test: ProportionalGrowthTest
    supporting_signals: Dict[str, Any]
    action_recommendation: str
