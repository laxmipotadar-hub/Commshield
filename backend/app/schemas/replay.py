from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ReplayStartRequest(BaseModel):
    dataset_id: str
    speed_multiplier: float = 1.0
    active_arms: List[str] = Field(
        default_factory=lambda: ["arm_a_static", "arm_b_naive", "arm_c_commshield"]
    )
    window_scale_sec: int = 60


class ReplayStatusResponse(BaseModel):
    status: str
    dataset_id: str
    current_window_index: int
    total_windows: int
    speed_multiplier: float
    current_timestamp: datetime
    is_placeholder: Optional[bool] = None


class DatasetInfo(BaseModel):
    dataset_id: str
    name: str
    description: Optional[str] = None
    total_windows: Optional[int] = None
    duration_sec: Optional[int] = None
    attack_types: Optional[List[str]] = None


class DatasetListResponse(BaseModel):
    datasets: List[DatasetInfo]
    total: int
    is_placeholder: Optional[bool] = None


class WindowReplayEvent(BaseModel):
    event_type: str = "window"
    arm: Optional[str] = None
    window: Dict[str, Any]
    detector_output: Optional[Dict[str, Any]] = None
    attribution_output: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    is_placeholder: Optional[bool] = None
