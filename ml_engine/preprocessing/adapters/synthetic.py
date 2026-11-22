import math
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, Iterator, List, Optional

from .base import (
    DEFAULT_SUPPRESSION_K,
    SUPPRESSED_ENTROPY_VALUE,
    TelemetryAdapter,
    enforce_aggregate_boundary,
)


class SyntheticAdapter(TelemetryAdapter):
    """Telemetry adapter for synthetic parametric 5G core telemetry streams."""

    def __init__(self, suppression_k: Optional[int] = None):
        self.suppression_k = suppression_k if suppression_k is not None else DEFAULT_SUPPRESSION_K

    def parse_records(self, records: Iterable[Any]) -> Iterator[Dict[str, Any]]:
        for rec in records:
            if isinstance(rec, dict):
                # Ensure timestamp is parsed as datetime
                ts = rec.get("timestamp")
                if isinstance(ts, str):
                    try:
                        rec["timestamp"] = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                    except Exception:
                        rec["timestamp"] = datetime.now(timezone.utc)
                elif not isinstance(ts, datetime):
                    rec["timestamp"] = datetime.now(timezone.utc)
                yield rec

    def aggregate_window(
        self,
        events: List[Dict[str, Any]],
        slice_id: str,
        nf_id: str,
        window_duration_sec: int,
        window_start: datetime,
        window_end: datetime,
    ) -> Dict[str, Any]:
        """Aggregate per-second events into a single CanonicalTrafficWindow matching CONTRACTS.md."""
        active_ue_max = 0
        reg_attempts = 0
        reg_failures = 0
        pdu_established = 0
        nas_total = 0
        nas_fail = 0
        pfcp_total = 0
        pfcp_fail = 0
        ul_bytes = 0
        dl_bytes = 0
        packets = 0
        teids = 0
        entropy_vals: List[float] = []
        new_ue_counts = 0

        # Ground truth tracking across events if present
        is_attack_any = False
        attack_types: List[str] = []
        is_growth_any = False

        for ev in events:
            active_ue_max = max(active_ue_max, int(ev.get("active_ue_count", 0)))
            reg_attempts += int(ev.get("registration_attempts", 0))
            reg_failures += int(ev.get("registration_failures", 0))
            pdu_established += int(ev.get("pdu_sessions_established", 0))
            nas_total += int(ev.get("nas_messages_total", 0))
            nas_fail += int(ev.get("nas_failures", 0))
            pfcp_total += int(ev.get("pfcp_association_messages", 0))
            pfcp_fail += int(ev.get("pfcp_failures", 0))
            ul_bytes += int(ev.get("total_bytes_uplink", 0))
            dl_bytes += int(ev.get("total_bytes_downlink", 0))
            packets += int(ev.get("total_packets", 0))
            teids = max(teids, int(ev.get("gtpu_teid_count", pdu_established)))
            new_ue_counts += int(ev.get("new_ue_count", 0))

            if "ue_hash_entropy" in ev:
                entropy_vals.append(float(ev["ue_hash_entropy"]))

            gt = ev.get("ground_truth", {})
            if gt.get("is_attack"):
                is_attack_any = True
                if gt.get("attack_type"):
                    attack_types.append(gt["attack_type"])
            if gt.get("is_growth"):
                is_growth_any = True

        # Compute ratio features
        ue_denom = max(active_ue_max, 1)
        pdu_denom = max(pdu_established, 1)
        nas_denom = max(nas_total, 1)
        pfcp_denom = max(pfcp_total, 1)

        registrations_per_active_ue = round(reg_attempts / ue_denom, 4)
        nas_failure_ratio = round(nas_fail / nas_denom, 4)
        pfcp_failure_ratio = round(pfcp_fail / pfcp_denom, 4)
        pdu_session_rate_per_ue = round(pdu_established / ue_denom, 4)
        bytes_per_session = round((ul_bytes + dl_bytes) / pdu_denom, 2)
        packets_per_session = round(packets / pdu_denom, 2)
        gtpu_volume_per_ue = round((ul_bytes + dl_bytes) / ue_denom, 2)
        # Small-group k-anonymity suppression:
        # If distinct active UEs < K, suppress entropy aggregate
        if active_ue_max < self.suppression_k:
            ue_hash_entropy = SUPPRESSED_ENTROPY_VALUE
        else:
            ue_hash_entropy = round(
                sum(entropy_vals) / len(entropy_vals) if entropy_vals else 7.42, 3
            )
        new_ue_rate = round(new_ue_counts / ue_denom, 4)

        # Compute normalized composition vector (sum to 1.0)
        total_events = max(reg_attempts + pdu_established + nas_fail + pfcp_fail + 10, 1)
        reg_ratio = round(reg_attempts / total_events, 4)
        pdu_ratio = round(pdu_established / total_events, 4)
        fail_ratio = round((reg_failures + nas_fail + pfcp_fail) / total_events, 4)
        other_ratio = max(0.0, round(1.0 - (reg_ratio + pdu_ratio + fail_ratio), 4))

        window_id = str(uuid.uuid4())

        canonical_window = {
            "window_id": window_id,
            "slice_id": slice_id,
            "nf_id": nf_id,
            "window_start": window_start.isoformat(),
            "window_end": window_end.isoformat(),
            "duration_sec": window_duration_sec,
            "active_ue_count": active_ue_max,
            "raw_counters": {
                "active_ue_count": active_ue_max,
                "registration_attempts": reg_attempts,
                "registration_failures": reg_failures,
                "pdu_sessions_established": pdu_established,
                "nas_messages_total": nas_total,
                "nas_failures": nas_fail,
                "pfcp_association_messages": pfcp_total,
                "pfcp_failures": pfcp_fail,
                "total_bytes_uplink": ul_bytes,
                "total_bytes_downlink": dl_bytes,
                "total_packets": packets,
                "gtpu_teid_count": teids,
            },
            "ratio_features": {
                "registrations_per_active_ue": registrations_per_active_ue,
                "nas_failure_ratio": nas_failure_ratio,
                "pfcp_failure_ratio": pfcp_failure_ratio,
                "pdu_session_rate_per_ue": pdu_session_rate_per_ue,
                "bytes_per_session": bytes_per_session,
                "packets_per_session": packets_per_session,
                "gtpu_volume_per_ue": gtpu_volume_per_ue,
                "ue_hash_entropy": ue_hash_entropy,
                "new_ue_rate": new_ue_rate,
            },
            "composition_vector": {
                "registration_ratio": reg_ratio,
                "session_setup_ratio": pdu_ratio,
                "failure_ratio": fail_ratio,
                "other_signalling_ratio": other_ratio,
            },
            "ground_truth": {
                "is_attack": is_attack_any,
                "attack_type": attack_types[0] if attack_types else None,
                "is_growth": is_growth_any,
            },
        }

        return enforce_aggregate_boundary(canonical_window)
# CommShield AI Core
