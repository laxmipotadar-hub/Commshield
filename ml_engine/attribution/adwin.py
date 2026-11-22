"""ADWIN (Adaptive Windowing) drift detection implementation for per-slice traffic streams."""

import math
from typing import Dict, List, Optional, Tuple
from .config import DEFAULT_ATTRIBUTION_CONFIG


class ADWIN:
    """Adaptive Windowing algorithm for detecting distribution drift in continuous data streams."""

    def __init__(self, delta: float = 0.002, min_window_length: int = 5, max_window_length: int = 200):
        self.delta = delta
        self.min_window_length = min_window_length
        self.max_window_length = max_window_length
        self.window: List[float] = []
        self.total: float = 0.0
        self.variance: float = 0.0
        self.width: int = 0

    def reset(self) -> None:
        """Reset internal window and statistics."""
        self.window.clear()
        self.total = 0.0
        self.variance = 0.0
        self.width = 0

    def update(self, value: float) -> bool:
        """Add an observation to the window and check for drift.
        
        Returns:
            True if a significant distribution shift was detected, False otherwise.
        """
        self.window.append(value)
        self.total += value
        self.width += 1

        if self.width > self.max_window_length:
            popped = self.window.pop(0)
            self.total -= popped
            self.width -= 1

        if self.width < self.min_window_length * 2:
            return False

        # Calculate variance for adaptive scaling
        mean = self.total / self.width
        var = sum((x - mean) ** 2 for x in self.window) / max(1, self.width - 1)
        std_dev = math.sqrt(max(1e-6, var))

        drift_detected = False

        # Evaluate candidate cut points
        step = max(1, self.width // 10)
        cut_candidates = list(range(self.min_window_length, self.width - self.min_window_length + 1, step))

        for cut in cut_candidates:
            w0 = self.window[:cut]
            w1 = self.window[cut:]
            n0 = len(w0)
            n1 = len(w1)

            if n0 < self.min_window_length or n1 < self.min_window_length:
                continue

            u0 = sum(w0) / n0
            u1 = sum(w1) / n1

            diff = abs(u0 - u1)
            m = (n0 * n1) / (n0 + n1)
            delta_prime = max(1e-9, self.delta / self.width)
            eps = math.sqrt((1.0 / (2.0 * m)) * math.log(4.0 / delta_prime))

            # Scale epsilon by standard deviation
            thresh = eps * max(1.0, std_dev)

            if diff > thresh:
                drift_detected = True
                # Prune older segment to adapt to new distribution
                prune_len = cut
                for _ in range(prune_len):
                    if self.window:
                        self.total -= self.window.pop(0)
                        self.width -= 1
                break

        return drift_detected


class AdwinSliceTracker:
    """Tracks per-slice ADWIN instances across continuous telemetry streams."""

    def __init__(self, delta: Optional[float] = None, min_window_length: Optional[int] = None):
        cfg = DEFAULT_ATTRIBUTION_CONFIG
        self.delta = delta or cfg.adwin_delta
        self.min_window_length = min_window_length or cfg.adwin_min_window_length
        self.trackers: Dict[str, ADWIN] = {}
        self.last_drift_windows: Dict[str, str] = {}

    def get_tracker(self, slice_id: str) -> ADWIN:
        """Get or create ADWIN instance for a given slice."""
        if slice_id not in self.trackers:
            self.trackers[slice_id] = ADWIN(
                delta=self.delta,
                min_window_length=self.min_window_length,
            )
        return self.trackers[slice_id]

    def reset(self, slice_id: Optional[str] = None) -> None:
        """Reset tracker for a specific slice or all slices."""
        if slice_id is not None:
            if slice_id in self.trackers:
                self.trackers[slice_id].reset()
        else:
            for t in self.trackers.values():
                t.reset()
            self.last_drift_windows.clear()

    def update(self, slice_id: str, volume: float, window_id: str) -> Tuple[bool, Optional[str]]:
        """Feed new volume observation for slice and test for drift.
        
        Returns:
            Tuple of (drift_detected: bool, window_id: Optional[str])
        """
        tracker = self.get_tracker(slice_id)
        drift = tracker.update(volume)
        if drift:
            self.last_drift_windows[slice_id] = window_id
            return True, window_id
        return False, None
# CommShield AI Core
