from datetime import datetime
from pydantic import BaseModel, ConfigDict


class IsolationForestScore(BaseModel):
    raw_score_negated: float
    benign_percentile: float
    threshold_percentile: float
    is_flagged: bool


class AutoencoderScore(BaseModel):
    reconstruction_mse: float
    benign_percentile: float
    threshold_percentile: float
    is_flagged: bool


class FusionScore(BaseModel):
    primary_rule: str
    fused_percentile: float
    secondary_mean_percentile: float
    agreement_state: str
    is_anomalous: bool


class CusumScore(BaseModel):
    accumulated_statistic: float
    alarm_threshold: float
    is_alarm: bool


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
