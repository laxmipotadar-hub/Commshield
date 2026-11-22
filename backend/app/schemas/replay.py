from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ReplayStartRequest(BaseModel):
    dataset_id: str = "5g_nidd"
    data_source: Optional[str] = "5g_nidd"
    speed_multiplier: float = 1.0
    active_arms: List[str] = Field(
        default_factory=lambda: ["arm_a_static", "arm_b_naive", "arm_c_commshield"]
    )
    window_scale_sec: int = 60


class ReplayStatusResponse(BaseModel):
    status: str
    dataset_id: str
    data_source: Optional[str] = "5g_nidd"
    current_window_index: int
    total_windows: int
    speed_multiplier: float
    current_timestamp: datetime


class DatasetInfo(BaseModel):
    dataset_id: str
    name: str
    description: Optional[str] = None
    data_source: Optional[str] = "synthetic"
    total_windows: Optional[int] = None
    duration_sec: Optional[int] = None
    attack_types: Optional[List[str]] = None


class DatasetListResponse(BaseModel):
    datasets: List[DatasetInfo]
    total: int


class WindowReplayEvent(BaseModel):
    event_type: str = "window"
    arm: Optional[str] = None
    window: Dict[str, Any]
    detector_output: Optional[Dict[str, Any]] = None
    attribution_output: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
# CommShield AI Core
