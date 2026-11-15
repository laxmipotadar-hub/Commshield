from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, Iterable, Iterator, List


class TelemetryAdapter(ABC):
    """Abstract Telemetry Adapter Protocol.
    
    Transforms heterogeneous 5G core telemetry inputs (PCAP, flow logs, synthetic streams)
    into the canonical schema specified in CONTRACTS.md.
    """

    @abstractmethod
    def parse_records(self, records: Iterable[Any]) -> Iterator[Dict[str, Any]]:
        """Parse raw records into standardized per-second or event records."""
        pass

    @abstractmethod
    def aggregate_window(
        self,
        events: List[Dict[str, Any]],
        slice_id: str,
        nf_id: str,
        window_duration_sec: int,
        window_start: datetime,
        window_end: datetime,
    ) -> Dict[str, Any]:
        """Aggregate standardized records into a CanonicalTrafficWindow matching CONTRACTS.md."""
        pass

    def adapt(
        self,
        records: Iterable[Any],
        slice_id: str,
        nf_id: str,
        window_duration_sec: int = 60,
    ) -> List[Dict[str, Any]]:
        """Convenience method to process an iterable of records into a list of canonical windows."""
        events = list(self.parse_records(records))
        if not events:
            return []

        # Group events into windows based on window_duration_sec
        windows: List[Dict[str, Any]] = []
        events_by_window: List[Dict[str, Any]] = []
        current_window_start: datetime | None = None

        for ev in events:
            ev_time = ev.get("timestamp")
            if not isinstance(ev_time, datetime):
                continue

            if current_window_start is None:
                current_window_start = ev_time

            elapsed = (ev_time - current_window_start).total_seconds()
            if elapsed >= window_duration_sec and events_by_window:
                window_end = ev_time
                windows.append(
                    self.aggregate_window(
                        events=events_by_window,
                        slice_id=slice_id,
                        nf_id=nf_id,
                        window_duration_sec=window_duration_sec,
                        window_start=current_window_start,
                        window_end=window_end,
                    )
                )
                events_by_window = []
                current_window_start = ev_time

            events_by_window.append(ev)

        if events_by_window and current_window_start:
            # Final window
            final_end = events_by_window[-1].get("timestamp", current_window_start)
            windows.append(
                self.aggregate_window(
                    events=events_by_window,
                    slice_id=slice_id,
                    nf_id=nf_id,
                    window_duration_sec=window_duration_sec,
                    window_start=current_window_start,
                    window_end=final_end,
                )
            )

        return windows
