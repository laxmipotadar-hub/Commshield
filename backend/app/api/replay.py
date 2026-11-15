from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import CanonicalWindow
from ..schemas import (
    ReplayStartRequest,
    ReplayStatusResponse,
    WindowReplayEvent,
)
from ..services.sample_data import (
    get_sample_replay_status,
    get_sample_window_event,
)

router = APIRouter(prefix="/replay", tags=["Replay"])


@router.post("/start", response_model=ReplayStatusResponse)
def start_replay(payload: ReplayStartRequest) -> ReplayStatusResponse:
    """Start replay stream across 3 arms."""
    # TODO: Call Three-Arm ReplayEngine (ml_engine/evaluation/replay.py) to initialize multi-arm stream playback
    return get_sample_replay_status(
        status="RUNNING",
        dataset_id=payload.dataset_id,
        speed_multiplier=payload.speed_multiplier,
    )


@router.post("/pause", response_model=ReplayStatusResponse)
def pause_replay() -> ReplayStatusResponse:
    """Pause active replay."""
    # TODO: Call ReplayEngine to pause active replay worker
    return get_sample_replay_status(status="PAUSED")


@router.post("/resume", response_model=ReplayStatusResponse)
def resume_replay() -> ReplayStatusResponse:
    """Resume paused replay."""
    # TODO: Call ReplayEngine to resume paused replay worker
    return get_sample_replay_status(status="RUNNING")


@router.post("/stop", response_model=ReplayStatusResponse)
def stop_replay() -> ReplayStatusResponse:
    """Terminate active replay."""
    # TODO: Call ReplayEngine to terminate active replay session
    return get_sample_replay_status(status="STOPPED")


@router.get("/status", response_model=ReplayStatusResponse)
def get_replay_status() -> ReplayStatusResponse:
    """Current tick and replay state."""
    # TODO: Query ReplayEngine status to fetch current window tick and playback progress
    return get_sample_replay_status()


@router.get("/stream")
def stream_replay(
    speed: float = Query(default=1.0, description="Playback speed multiplier"),
    db: Session = Depends(get_db),
):
    """Server-Sent Events stream of replay windows."""
    # TODO: Connect to ReplayEngine event generator to yield live window replay SSE stream across arms

    def event_generator():
        db_windows = db.query(CanonicalWindow).limit(10).all()
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
                    is_placeholder=False,
                )
                yield f"data: {event.model_dump_json()}\n\n"
        else:
            sample_event = get_sample_window_event()
            yield f"data: {sample_event.model_dump_json()}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
