"""CUSUM persistent shift detector accumulating evidence from fused anomaly scores over time per slice."""

from typing import Any, Dict, Optional, Tuple
from .config import DEFAULT_DETECTION_CONFIG


class CusumDetector:
    """Cumulative Sum (CUSUM) detector for tracking persistent score shifts.
    
    Accumulates evidence from the fused percentile stream per slice.
    Output status: 'idle', 'accumulating', or 'triggered'.
    Resets accumulated statistic to 0.0 upon trigger.
    """

    def __init__(
        self,
        reference_value: Optional[float] = None,
        scale: Optional[float] = None,
        alarm_threshold: Optional[float] = None,
        reset_on_trigger: Optional[bool] = None,
    ):
        cfg = DEFAULT_DETECTION_CONFIG
        self.reference_value = reference_value if reference_value is not None else cfg.cusum_reference_value
        self.scale = scale if scale is not None else cfg.cusum_scale
        self.alarm_threshold = alarm_threshold if alarm_threshold is not None else cfg.cusum_alarm_threshold
        self.reset_on_trigger = reset_on_trigger if reset_on_trigger is not None else cfg.cusum_reset_on_trigger

        # Slice-keyed accumulators
        self._accumulators: Dict[str, float] = {}

    def get_statistic(self, slice_id: str) -> float:
        """Get current accumulated statistic for a slice."""
        return self._accumulators.get(slice_id, 0.0)

    def reset(self, slice_id: Optional[str] = None) -> None:
        """Reset accumulator for a given slice or all slices."""
        if slice_id is not None:
            self._accumulators[slice_id] = 0.0
        else:
            self._accumulators.clear()

    def update(self, slice_id: str, fused_score: float) -> Tuple[float, bool, str]:
        """Update CUSUM accumulator with incoming fused percentile score.
        
        Args:
            slice_id: Slice identifier.
            fused_score: Fused percentile score [0.0 - 100.0].
            
        Returns:
            Tuple of (accumulated_statistic, is_alarm, status)
            status is one of: 'idle', 'accumulating', 'triggered'.
        """
        current_stat = self._accumulators.get(slice_id, 0.0)

        # Deviation above reference value
        deviation = (fused_score - self.reference_value) / max(0.001, self.scale)
        new_stat = max(0.0, current_stat + deviation)

        if new_stat >= self.alarm_threshold:
            status = "triggered"
            is_alarm = True
            stat_to_report = round(new_stat, 4)
            if self.reset_on_trigger:
                self._accumulators[slice_id] = 0.0
            else:
                self._accumulators[slice_id] = new_stat
        elif new_stat > 0.0:
            status = "accumulating"
            is_alarm = False
            stat_to_report = round(new_stat, 4)
            self._accumulators[slice_id] = new_stat
        else:
            status = "idle"
            is_alarm = False
            stat_to_report = 0.0
            self._accumulators[slice_id] = 0.0

        return stat_to_report, is_alarm, status
