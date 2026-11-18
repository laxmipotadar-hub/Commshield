from abc import ABC, abstractmethod
from datetime import datetime
import hashlib
import hmac
import os
from typing import Any, Dict, Iterable, Iterator, List, Optional, Set, Union

# Documented Privacy Constants
SUPPRESSED_ENTROPY_VALUE: float = -1.0
DEFAULT_SUPPRESSION_K: int = int(os.getenv("COMMSHIELD_SUPPRESSION_K", "5"))
DEFAULT_HMAC_SALT: bytes = b"commshield-pseudonymization-default-salt-v1"

# Strict Allowlist Schemas for Canonical Aggregate Windows (CONTRACTS.md)
CANONICAL_WINDOW_ALLOWLIST: Set[str] = {
    "window_id",
    "slice_id",
    "nf_id",
    "window_start",
    "window_end",
    "duration_sec",
    "raw_counters",
    "ratio_features",
    "composition_vector",
    "ground_truth",
}

RAW_COUNTERS_ALLOWLIST: Set[str] = {
    "active_ue_count",
    "registration_attempts",
    "registration_failures",
    "pdu_sessions_established",
    "nas_messages_total",
    "nas_failures",
    "pfcp_association_messages",
    "pfcp_failures",
    "total_bytes_uplink",
    "total_bytes_downlink",
    "total_packets",
    "gtpu_teid_count",
}

RATIO_FEATURES_ALLOWLIST: Set[str] = {
    "registrations_per_active_ue",
    "nas_failure_ratio",
    "pfcp_failure_ratio",
    "pdu_session_rate_per_ue",
    "bytes_per_session",
    "packets_per_session",
    "gtpu_volume_per_ue",
    "ue_hash_entropy",
    "new_ue_rate",
}

COMPOSITION_VECTOR_ALLOWLIST: Set[str] = {
    "registration_ratio",
    "session_setup_ratio",
    "failure_ratio",
    "other_signalling_ratio",
}


def get_hmac_secret() -> bytes:
    """Retrieve HMAC secret key from environment without logging or committing."""
    secret = os.getenv("COMMSHIELD_HMAC_KEY")
    if secret:
        return secret.encode("utf-8")
    return DEFAULT_HMAC_SALT


def pseudonymize_identifier(identifier: str, key: Optional[Union[bytes, str]] = None) -> str:
    """Pseudonymise a network or subscriber identifier (IP/UE) using HMAC-SHA256.
    
    Guarantees deterministic pseudonym generation for matching within an deployment
    while preventing rainbow table attacks or unauthorized re-identification.
    """
    if not identifier:
        return ""
    if key is None:
        hmac_key = get_hmac_secret()
    elif isinstance(key, str):
        hmac_key = key.encode("utf-8")
    else:
        hmac_key = key
    return hmac.new(hmac_key, identifier.encode("utf-8"), hashlib.sha256).hexdigest()


def enforce_aggregate_boundary(window: Dict[str, Any]) -> Dict[str, Any]:
    """Filter window dictionary strictly against aggregate-only allowlist schemas.
    
    Guarantees that no raw identifiers (IP addresses, port numbers, subscriber IDs,
    or flow payloads) escape the adapter boundary into the database, API, or models.
    """
    clean_window: Dict[str, Any] = {}
    for k, v in window.items():
        if k in CANONICAL_WINDOW_ALLOWLIST:
            clean_window[k] = v

    # 1. Filter raw_counters (allow numbers only)
    raw_counters = clean_window.get("raw_counters") or {}
    clean_window["raw_counters"] = {
        k: (int(v) if isinstance(v, (int, float)) and v == int(v) else float(v))
        for k, v in raw_counters.items()
        if k in RAW_COUNTERS_ALLOWLIST and isinstance(v, (int, float))
    }

    # 2. Filter ratio_features (allow floats only)
    ratio_features = clean_window.get("ratio_features") or {}
    clean_window["ratio_features"] = {
        k: (float(v) if v is not None else None)
        for k, v in ratio_features.items()
        if k in RATIO_FEATURES_ALLOWLIST and (isinstance(v, (int, float)) or v is None)
    }

    # 3. Filter composition_vector (allow floats only)
    comp_vector = clean_window.get("composition_vector") or {}
    clean_window["composition_vector"] = {
        k: float(v)
        for k, v in comp_vector.items()
        if k in COMPOSITION_VECTOR_ALLOWLIST and isinstance(v, (int, float))
    }

    return clean_window


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
        nf_id: str = "UPF-01",
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
