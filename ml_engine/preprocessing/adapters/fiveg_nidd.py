from datetime import datetime
from typing import Any, Dict, Iterable, Iterator, List

from .base import TelemetryAdapter


class FiveGNIDDAdapter(TelemetryAdapter):
    """Telemetry adapter for the public 5G-NIDD NetFlow / PCAP dataset.
    
    Stub implementation scheduled for milestone M2.
    """

    def parse_records(self, records: Iterable[Any]) -> Iterator[Dict[str, Any]]:
        raise NotImplementedError(
            "FiveGNIDDAdapter is scheduled for Milestone M2. Use SyntheticAdapter for active streams."
        )

    def aggregate_window(
        self,
        events: List[Dict[str, Any]],
        slice_id: str,
        nf_id: str,
        window_duration_sec: int,
        window_start: datetime,
        window_end: datetime,
    ) -> Dict[str, Any]:
        raise NotImplementedError(
            "FiveGNIDDAdapter is scheduled for Milestone M2. Use SyntheticAdapter for active streams."
        )
