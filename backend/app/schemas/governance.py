from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict


class ApprovalActionRequest(BaseModel):
    candidate_id: Optional[str] = None
    analyst_id: str
    notes: str


class EvaluateCandidateRequest(BaseModel):
    candidate_id: Optional[str] = None
    slice_id: Optional[str] = None
    volume_multiplier: Optional[float] = 1.0


class GovernanceApproveRequest(BaseModel):
    candidate_id: Optional[str] = None
    analyst_id: str
    notes: str


class GovernanceRejectRequest(BaseModel):
    candidate_id: Optional[str] = None
    analyst_id: str
    notes: str


class RollbackRequest(BaseModel):
    slice_id: str
    nf_id: str
    target_baseline_version: str
    reason: str
    analyst_id: str


class RollbackResponse(BaseModel):
    status: str
    slice_id: str
    active_version: str
    restored_artifacts: List[str]
    timestamp: datetime


class BaselineSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="allow")

    id: str
    slice_id: str
    nf_id: str
    version: str
    is_anchor: bool
    is_active: bool
    training_window_start: datetime
    training_window_end: datetime
    model_artifact_path: str
    scaler_params: Dict[str, Any]
    threshold_params: Dict[str, Any]
    feature_schema: Dict[str, Any]
    created_at: datetime
    is_candidate: Optional[bool] = False
    candidate_status: Optional[str] = None


class CandidateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="allow")

    id: str
    slice_id: str
    candidate_version: str
    active_baseline_id: str
    anchor_baseline_id: str
    status: str
    gate_metrics: Dict[str, Any]
    decision_trace: List[str]
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    created_at: datetime


class CandidateBaselinePackage(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="allow")

    candidate_id: str
    slice_id: str
    nf_id: str
    candidate_version: str
    active_version: str
    anchor_version: str
    training_metadata: Dict[str, Any]
    gate_evaluations: Dict[str, Any]
    overall_governance_decision: str
    decision_trace: List[str]


class ThreeArmComparisonResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    dataset_id: str
    arms: Dict[str, Any]
