"""Replay service for CommShield.

Steps through scenario traffic windows at a selectable speed, stores canonical windows
into the SQLite/Postgres database in background tasks, and provides start/pause/status controls.
"""

import asyncio
from datetime import datetime, timezone
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..database import SessionLocal
from ..models import CanonicalWindow
from ..schemas import ReplayStatusResponse
from .detection import detection_service

logger = logging.getLogger("commshield.replay")

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
SYNTHETIC_DATA_DIR = PROJECT_ROOT / "data" / "synthetic"


class ReplayService:
    """Manages asynchronous background replay of 5G core telemetry streams."""

    def __init__(self):
        self.status: str = "STOPPED"
        self.dataset_id: str = "stable_benign"
        self.current_window_index: int = 0
        self.total_windows: int = 0
        self.speed_multiplier: float = 1.0
        self.current_timestamp: datetime = datetime.now(timezone.utc)
        self.active_arms: List[str] = ["arm_a_static", "arm_b_naive", "arm_c_commshield"]
        self.window_scale_sec: int = 60

        self._windows: List[Dict[str, Any]] = []
        self._task: Optional[asyncio.Task] = None
        self._lock = asyncio.Lock()
        self._legitimate_windows_by_slice: Dict[str, List[Dict[str, Any]]] = {}
        self._candidate_created_by_slice: Dict[str, bool] = {}

    def _load_scenario(self, dataset_id: str) -> List[Dict[str, Any]]:
        """Load windows from scenario file in data/synthetic/."""
        # Check direct json file or with .json suffix
        candidates = [
            SYNTHETIC_DATA_DIR / f"{dataset_id}.json",
            SYNTHETIC_DATA_DIR / dataset_id,
            SYNTHETIC_DATA_DIR / "stable_benign.json",
        ]

        target_file = None
        for cand in candidates:
            if cand.is_file():
                target_file = cand
                break

        if not target_file:
            logger.warning("No scenario file found in %s, returning empty list.", SYNTHETIC_DATA_DIR)
            return []

        try:
            with open(target_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("windows", [])
        except Exception as e:
            logger.error("Failed to load scenario %s: %s", target_file, e)
            return []

    def _store_window_in_db(self, w: Dict[str, Any]) -> None:
        """Persist a canonical traffic window into the database."""
        db = SessionLocal()
        try:
            window_id = w.get("window_id")
            existing = db.query(CanonicalWindow).filter(CanonicalWindow.id == window_id).first()
            if existing:
                import uuid
                window_id = str(uuid.uuid4())

            win_start_raw = w.get("window_start")
            win_end_raw = w.get("window_end")

            if isinstance(win_start_raw, str):
                win_start = datetime.fromisoformat(win_start_raw.replace("Z", "+00:00"))
            else:
                win_start = win_start_raw or datetime.now(timezone.utc)

            if isinstance(win_end_raw, str):
                win_end = datetime.fromisoformat(win_end_raw.replace("Z", "+00:00"))
            else:
                win_end = win_end_raw or datetime.now(timezone.utc)

            row = CanonicalWindow(
                id=window_id,
                slice_id=w.get("slice_id", "sst-1-sd-010203"),
                nf_id=w.get("nf_id", "UPF-01"),
                window_start=win_start,
                window_end=win_end,
                duration_sec=int(w.get("duration_sec", 60)),
                raw_counters=w.get("raw_counters", {}),
                ratio_features=w.get("ratio_features", {}),
                composition_vector=w.get("composition_vector", {}),
            )
            db.add(row)
            db.commit()

            # Run detection automatically as replay produces window
            try:
                w_eval = dict(w)
                w_eval["window_id"] = window_id
                detection_service.analyze_window(w_eval, db=db)
                # Run attribution automatically inside replay pipeline
                from .attribution import attribution_service
                attr_res = attribution_service.analyze_window(w_eval, db=db, scenario=self.dataset_id)

                # Track legitimate growth adaptation windows for governance candidate creation
                slice_id = w_eval.get("slice_id", "sst-1-sd-010203")
                if attr_res and attr_res.verdict == "likely_benign":
                    if slice_id not in self._legitimate_windows_by_slice:
                        self._legitimate_windows_by_slice[slice_id] = []
                    self._legitimate_windows_by_slice[slice_id].append(w_eval)

                    # When likely_benign drift persists (>= 3 windows) and no candidate created yet during this run
                    if (
                        len(self._legitimate_windows_by_slice[slice_id]) >= 3
                        and not self._candidate_created_by_slice.get(slice_id, False)
                    ):
                        from .governance import governance_service
                        try:
                            cand_bundle, cand_row = governance_service.create_candidate_for_slice(
                                slice_id=slice_id,
                                adaptation_windows=self._legitimate_windows_by_slice[slice_id],
                                db=db,
                            )
                            # Extract scaling factor from proportional growth test
                            vol_k = 1.0
                            if hasattr(attr_res, "proportional_growth_test") and attr_res.proportional_growth_test:
                                vol_k = float(getattr(attr_res.proportional_growth_test, "scaling_factor_k", 1.0))

                            # Run governance pipeline automatically; promotion left PENDING
                            governance_service.evaluate_candidate(
                                candidate_id=cand_row.id,
                                db=db,
                                volume_multiplier=vol_k,
                                adaptation_windows=self._legitimate_windows_by_slice[slice_id],
                            )
                            self._candidate_created_by_slice[slice_id] = True
                            logger.info(
                                "Automatically generated and evaluated shadow candidate %s during replay for slice %s.",
                                cand_row.candidate_version,
                                slice_id,
                            )
                        except Exception as cand_err:
                            logger.warning("Error during automatic candidate creation: %s", cand_err)
            except Exception as pipe_err:
                logger.warning("Error running detection/attribution during replay: %s", pipe_err)
        except Exception as e:
            db.rollback()
            logger.warning("Error storing window in database: %s", e)
        finally:
            db.close()

    async def _run_loop(self) -> None:
        """Background execution loop stepping through windows."""
        try:
            while self.status != "STOPPED" and self.current_window_index < self.total_windows:
                if self.status == "PAUSED":
                    await asyncio.sleep(0.2)
                    continue

                w = self._windows[self.current_window_index]
                self._store_window_in_db(w)

                raw_ts = w.get("window_end")
                if isinstance(raw_ts, str):
                    self.current_timestamp = datetime.fromisoformat(raw_ts.replace("Z", "+00:00"))

                self.current_window_index += 1

                # Calculate tick interval: base interval 0.5s divided by speed multiplier
                tick_delay = max(0.01, 0.5 / max(0.1, self.speed_multiplier))
                await asyncio.sleep(tick_delay)

            if self.current_window_index >= self.total_windows:
                self.status = "COMPLETED"
        except asyncio.CancelledError:
            self.status = "STOPPED"
        except Exception as e:
            logger.error("Error in replay background loop: %s", e)
            self.status = "ERROR"

    async def start(
        self,
        dataset_id: str,
        speed_multiplier: float = 1.0,
        active_arms: Optional[List[str]] = None,
        window_scale_sec: int = 60,
    ) -> ReplayStatusResponse:
        """Start or restart a replay background task."""
        # Cancel previous running task if any
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

        self.dataset_id = dataset_id
        self.speed_multiplier = max(0.1, speed_multiplier)
        self.window_scale_sec = window_scale_sec
        if active_arms:
            self.active_arms = active_arms

        self._windows = self._load_scenario(dataset_id)
        self.total_windows = len(self._windows)
        self.current_window_index = 0
        self.status = "RUNNING"
        self.current_timestamp = datetime.now(timezone.utc)
        self._legitimate_windows_by_slice.clear()
        self._candidate_created_by_slice.clear()

        # Reset ADWIN trackers for fresh scenario run
        try:
            from .attribution import attribution_service
            attribution_service.reset_trackers()
        except Exception:
            pass

        # Launch background task
        loop = asyncio.get_running_loop()
        self._task = loop.create_task(self._run_loop())

        return self.get_status()

    def start_sync(self, dataset_id: str, speed_multiplier: float = 1.0) -> ReplayStatusResponse:
        """Initialize scenario for synchronous stepping (used in CLI demo and tests)."""
        self.stop()
        self.dataset_id = dataset_id
        self.speed_multiplier = max(0.1, speed_multiplier)
        self._windows = self._load_scenario(dataset_id)
        self.total_windows = len(self._windows)
        self.current_window_index = 0
        self.status = "RUNNING"
        self.current_timestamp = datetime.now(timezone.utc)
        self._legitimate_windows_by_slice.clear()
        self._candidate_created_by_slice.clear()
        try:
            from .attribution import attribution_service
            attribution_service.reset_trackers()
        except Exception:
            pass
        return self.get_status()

    def pause(self) -> ReplayStatusResponse:
        """Pause active replay."""
        if self.status == "RUNNING":
            self.status = "PAUSED"
        return self.get_status()

    def resume(self) -> ReplayStatusResponse:
        """Resume paused replay."""
        if self.status == "PAUSED":
            self.status = "RUNNING"
        return self.get_status()

    def stop(self) -> ReplayStatusResponse:
        """Terminate active replay."""
        self.status = "STOPPED"
        if self._task and not self._task.done():
            self._task.cancel()
        return self.get_status()

    def get_status(self) -> ReplayStatusResponse:
        """Get current replay status snapshot."""
        return ReplayStatusResponse(
            status=self.status,
            dataset_id=self.dataset_id,
            current_window_index=self.current_window_index,
            total_windows=self.total_windows,
            speed_multiplier=self.speed_multiplier,
            current_timestamp=self.current_timestamp,
        )

    def step_sync(self, count: int = 1) -> int:
        """Synchronously step through count windows and store them in DB (useful for tests)."""
        stored = 0
        for _ in range(count):
            if self.current_window_index < self.total_windows:
                w = self._windows[self.current_window_index]
                self._store_window_in_db(w)
                self.current_window_index += 1
                stored += 1
        return stored


# Global singleton replay service
replay_service = ReplayService()
