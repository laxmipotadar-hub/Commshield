from datetime import datetime, timezone
import json
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import CanonicalWindow
from ..schemas import (
    ReplayStartRequest,
    ReplayStatusResponse,
    WindowReplayEvent,
)
from ..services.replay import replay_service

router = APIRouter(prefix="/replay", tags=["Replay"])


@router.post("/start", response_model=ReplayStatusResponse)
async def start_replay(payload: ReplayStartRequest) -> ReplayStatusResponse:
    """Start replay stream across 3 arms in a background task.
    
    Refuses to start if a replay is already RUNNING.
    """
    if replay_service.status == "RUNNING":
        raise HTTPException(
            status_code=409,
            detail=f"Replay is already running for dataset '{replay_service.dataset_id}'. Stop or pause active replay before starting a new one.",
        )

    status = await replay_service.start(
        dataset_id=payload.dataset_id,
        speed_multiplier=payload.speed_multiplier,
        active_arms=payload.active_arms,
        window_scale_sec=payload.window_scale_sec,
        data_source=payload.data_source,
    )
    return status


@router.post("/pause", response_model=ReplayStatusResponse)
def pause_replay() -> ReplayStatusResponse:
    """Pause active replay."""
    return replay_service.pause()


@router.post("/resume", response_model=ReplayStatusResponse)
def resume_replay() -> ReplayStatusResponse:
    """Resume paused replay."""
    return replay_service.resume()


@router.post("/stop", response_model=ReplayStatusResponse)
def stop_replay() -> ReplayStatusResponse:
    """Terminate active replay."""
    return replay_service.stop()


@router.get("/status", response_model=ReplayStatusResponse)
def get_replay_status() -> ReplayStatusResponse:
    """Current tick and replay state."""
    return replay_service.get_status()


@router.get("/stream")
def stream_replay(
    speed: float = Query(default=1.0, description="Playback speed multiplier"),
    db: Session = Depends(get_db),
):
    """Server-Sent Events stream of replay windows."""
    def event_generator():
        db_windows = db.query(CanonicalWindow).order_by(CanonicalWindow.window_start.asc()).limit(50).all()
        if db_windows:
            for w in db_windows:
                event = WindowReplayEvent(
                    event_type="window",
                    arm="arm_c_commshield",
                    window={
                        "window_id": w.id,
                        "slice_id": w.slice_id,
                        "nf_id": w.nf_id,
                        "window_start": w.window_start.isoformat(),
                        "window_end": w.window_end.isoformat(),
                        "duration_sec": w.duration_sec,
                        "raw_counters": w.raw_counters,
                        "ratio_features": w.ratio_features,
                        "composition_vector": w.composition_vector,
                    },
                    timestamp=datetime.now(timezone.utc),
                )
                yield f"data: {event.model_dump_json()}\n\n"
        else:
            idle_event = {
                "event_type": "status",
                "status": replay_service.status,
                "current_window_index": replay_service.current_window_index,
                "total_windows": replay_service.total_windows,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            yield f"data: {json.dumps(idle_event)}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
