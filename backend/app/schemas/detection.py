from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict


class IsolationForestScore(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="allow")

    raw_score_negated: float
    benign_percentile: float
    threshold_percentile: float
    is_flagged: bool


class AutoencoderScore(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="allow")

    reconstruction_mse: float
    benign_percentile: float
    threshold_percentile: float
    is_flagged: bool


class FusionScore(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="allow")

    primary_rule: str
    fused_percentile: float
    secondary_mean_percentile: float
    agreement_state: str
    is_anomalous: bool


class CusumScore(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="allow")

    accumulated_statistic: float
    alarm_threshold: float
    is_alarm: bool
    status: Optional[str] = "idle"


class DetectorOutput(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="allow")

    window_id: str
    slice_id: str
    nf_id: str
    evaluated_at: datetime
    baseline_version: str
    isolation_forest: IsolationForestScore
    autoencoder: AutoencoderScore
    fusion: FusionScore
    cusum: CusumScore


class AnalyzeRequest(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="allow")

    window_id: Optional[str] = None
    slice_id: Optional[str] = None
    nf_id: Optional[str] = None
    ratio_features: Optional[Dict[str, float]] = None
    window: Optional[Dict[str, Any]] = None


class AlertItem(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="allow")

    id: str
    window_id: str
    slice_id: str
    nf_id: str
    detector_output: DetectorOutput
    is_anomalous: bool
    fused_score: Optional[float] = None
    created_at: datetime


class DashboardOverviewResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="allow")

    total_traffic_bytes: int
    active_slices_count: int
    anomaly_alerts_count: int
    drift_status: str
    quarantined_windows_count: int
    active_baseline_version: str
    pending_updates_count: int
    recent_alerts: List[Dict[str, Any]]
    traffic_over_time: List[Dict[str, Any]]
