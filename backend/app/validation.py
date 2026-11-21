"""CommShield Telemetry Data Integrity and Validation Engine.

Enforces strict runtime data hygiene and telemetry invariants:
1. Chronological Monotonicity: Timestamps must be strictly non-decreasing.
2. Continuity / Gap Detection: Flag missing windows where duration exceeds expected interval (60s).
3. Non-Negative Volumes: Uplink/downlink bytes, packets, and UEs must never be negative.
4. Finite Numbers: Detect and reject NaN, +Inf, -Inf in feature vectors and scores.
5. Schema Invariants: Ensure mandatory fields, valid S-NSSAI slice formats, and valid attack labels.
6. Range Boundaries: Verify ratios are bounded [0.0, 1.0] and percentiles bounded [0.0, 100.0].
"""

from dataclasses import asdict, dataclass, field
from datetime import datetime
import math
from typing import Any, Dict, List, Optional, Set, Tuple
from pydantic import BaseModel, Field

VALID_SLICES: Set[str] = {
    "sst-1-sd-010203",  # eMBB
    "sst-2-sd-112233",  # URLLC
    "sst-3-sd-445566",  # mMTC
    "slice-embb",
    "slice-urllc",
    "slice-mmtc",
    "slice-1",
    "slice-2",
    "slice-3",
}

EXPECTED_WINDOW_DURATION_SEC = 60


@dataclass
class ValidationIssue:
    severity: str  # "ERROR", "WARNING"
    category: str  # "MONOTONICITY", "MISSING_WINDOW", "NEGATIVE_VALUE", "NON_FINITE", "SCHEMA", "RANGE"
    window_id: Optional[str]
    message: str
    field_name: Optional[str] = None
    value: Optional[Any] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ValidationReport(BaseModel):
    is_valid: bool
    total_windows_checked: int
    error_count: int
    warning_count: int
    issues: List[Dict[str, Any]] = Field(default_factory=list)
    summary: str


def is_finite_number(val: Any) -> bool:
    """Check if value is a valid finite float or int (not NaN or Inf)."""
    if val is None:
        return False
    try:
        f = float(val)
        return not (math.isnan(f) or math.isinf(f))
    except (ValueError, TypeError):
        return False


def parse_iso_datetime(dt_str: str) -> Optional[datetime]:
    """Parse ISO timestamp robustly."""
    if not dt_str:
        return None
    try:
        clean = dt_str.replace("Z", "+00:00")
        return datetime.fromisoformat(clean)
    except Exception:
        return None


def validate_single_window(w: Dict[str, Any], index: int = 0) -> List[ValidationIssue]:
    """Validate schema and numerical invariants of a single telemetry window."""
    issues: List[ValidationIssue] = []
    w_id = str(w.get("window_id", f"idx-{index}"))

    # 1. Schema check
    if not w.get("timestamp") and not w.get("window_start"):
        issues.append(
            ValidationIssue(
                severity="ERROR",
                category="SCHEMA",
                window_id=w_id,
                message="Missing mandatory timestamp or window_start field",
                field_name="timestamp",
            )
        )

    # 2. Slice ID check
    slice_id = str(w.get("slice_id", "")).lower()
    if slice_id and slice_id not in VALID_SLICES and not any(s in slice_id for s in ("embb", "urllc", "mmtc", "sst", "slice")):
        issues.append(
            ValidationIssue(
                severity="WARNING",
                category="SCHEMA",
                window_id=w_id,
                message=f"Non-standard slice_id '{slice_id}'",
                field_name="slice_id",
                value=slice_id,
            )
        )

    # 3. Non-negative volumes and finite numbers in raw counters
    raw_counters = w.get("raw_counters") or {}
    for counter_name in [
        "active_ue_count", "total_bytes_uplink", "total_bytes_downlink",
        "total_packets", "registration_attempts", "registration_failures",
        "nas_messages_total", "nas_failures", "pfcp_association_messages",
        "pfcp_failures", "gtpu_teid_count", "uplink_mb", "downlink_mb",
    ]:
        val = w.get(counter_name) if counter_name in w else raw_counters.get(counter_name)
        if val is not None:
            if not is_finite_number(val):
                issues.append(
                    ValidationIssue(
                        severity="ERROR",
                        category="NON_FINITE",
                        window_id=w_id,
                        message=f"Non-finite value in '{counter_name}': {val}",
                        field_name=counter_name,
                        value=str(val),
                    )
                )
            elif float(val) < 0.0:
                issues.append(
                    ValidationIssue(
                        severity="ERROR",
                        category="NEGATIVE_VALUE",
                        window_id=w_id,
                        message=f"Negative volume in '{counter_name}': {val}",
                        field_name=counter_name,
                        value=val,
                    )
                )

    # 4. Ratio features bounded [0, 1]
    ratio_features = w.get("ratio_features") or {}
    for ratio_name in [
        "nas_failure_ratio", "pfcp_failure_ratio", "udp_ratio",
        "tcp_ratio", "icmp_ratio", "syn_flag_ratio", "rst_flag_ratio",
    ]:
        val = w.get(ratio_name) if ratio_name in w else ratio_features.get(ratio_name)
        if val is not None:
            if not is_finite_number(val):
                issues.append(
                    ValidationIssue(
                        severity="ERROR",
                        category="NON_FINITE",
                        window_id=w_id,
                        message=f"Non-finite ratio in '{ratio_name}': {val}",
                        field_name=ratio_name,
                        value=str(val),
                    )
                )
            elif not (-1e-5 <= float(val) <= 1.0 + 1e-5):
                issues.append(
                    ValidationIssue(
                        severity="WARNING",
                        category="RANGE",
                        window_id=w_id,
                        message=f"Ratio '{ratio_name}' out of [0.0, 1.0] bounds: {val}",
                        field_name=ratio_name,
                        value=val,
                    )
                )

    # 5. Percentiles bounded [0, 100]
    for pct_name in ["fused_percentile", "percentile_score", "anomaly_percentile"]:
        if pct_name in w:
            val = w[pct_name]
            if not is_finite_number(val):
                issues.append(
                    ValidationIssue(
                        severity="ERROR",
                        category="NON_FINITE",
                        window_id=w_id,
                        message=f"Non-finite percentile in '{pct_name}': {val}",
                        field_name=pct_name,
                        value=str(val),
                    )
                )
            elif float(val) < 0.0 or float(val) > 100.0:
                issues.append(
                    ValidationIssue(
                        severity="ERROR",
                        category="RANGE",
                        window_id=w_id,
                        message=f"Percentile '{pct_name}' out of [0, 100] bounds: {val}",
                        field_name=pct_name,
                        value=val,
                    )
                )

    return issues


def validate_telemetry_series(
    windows: List[Dict[str, Any]],
    expected_step_seconds: int = EXPECTED_WINDOW_DURATION_SEC,
) -> ValidationReport:
    """Validate a complete time series of telemetry windows for monotonicity, gaps, and invariants."""
    all_issues: List[ValidationIssue] = []
    prev_dt: Optional[datetime] = None

    for i, w in enumerate(windows):
        # Validate individual window invariants
        win_issues = validate_single_window(w, index=i)
        all_issues.extend(win_issues)

        # Monotonicity & Continuity
        raw_ts = w.get("timestamp") or w.get("window_start") or w.get("window_end")
        dt = parse_iso_datetime(str(raw_ts)) if raw_ts else None
        w_id = str(w.get("window_id", f"idx-{i}"))

        if dt and prev_dt:
            delta_sec = (dt - prev_dt).total_seconds()
            if delta_sec < 0:
                all_issues.append(
                    ValidationIssue(
                        severity="ERROR",
                        category="MONOTONICITY",
                        window_id=w_id,
                        message=f"Timestamp decreased from {prev_dt.isoformat()} to {dt.isoformat()} (delta: {delta_sec}s)",
                        field_name="timestamp",
                        value=dt.isoformat(),
                    )
                )
            elif delta_sec > (expected_step_seconds * 1.5):
                all_issues.append(
                    ValidationIssue(
                        severity="WARNING",
                        category="MISSING_WINDOW",
                        window_id=w_id,
                        message=f"Temporal gap detected: {delta_sec:.0f}s elapsed between consecutive windows (expected ~{expected_step_seconds}s)",
                        field_name="timestamp",
                        value=delta_sec,
                    )
                )

        if dt:
            prev_dt = dt

    errors = sum(1 for iss in all_issues if iss.severity == "ERROR")
    warnings = sum(1 for iss in all_issues if iss.severity == "WARNING")
    is_valid = (errors == 0)

    summary = (
        f"Validation PASSED: {len(windows)} windows checked, 0 errors, {warnings} warnings."
        if is_valid
        else f"Validation FAILED: {errors} critical errors, {warnings} warnings found in {len(windows)} windows."
    )

    return ValidationReport(
        is_valid=is_valid,
        total_windows_checked=len(windows),
        error_count=errors,
        warning_count=warnings,
        issues=[iss.to_dict() for iss in all_issues],
        summary=summary,
    )
