"""Canonical Window Schema Definitions and Validator.

Enforces schema contracts for slice-level and per-device windows across Digital Twin,
Lab, and Real Recorded data sources.
"""

from datetime import datetime, timezone
import math
from pathlib import Path
import re
from typing import Any, Dict, List, Optional, Set, Tuple, Union

# Documented valid values
VALID_SOURCES: Set[str] = {"simulated_twin", "lab", "real_recorded"}
VALID_DEVICE_CLASSES: Set[str] = {"sensor", "camera", "AGV"}
VALID_LABELS: Set[str] = {"benign", "attack"}

HEX_64_REGEX = re.compile(r"^[0-9a-f]{64}$")


class ValidationError(ValueError):
    """Raised when a canonical window violates schema contracts."""
    pass


def parse_iso_timestamp(ts: Union[str, datetime]) -> datetime:
    """Parse ISO 8601 timestamp string to timezone-aware UTC datetime."""
    if isinstance(ts, datetime):
        if ts.tzinfo is None:
            return ts.replace(tzinfo=timezone.utc)
        return ts.astimezone(timezone.utc)
    if not isinstance(ts, str):
        raise ValidationError(f"Timestamp must be ISO 8601 string or datetime, got {type(ts)}")
    clean_str = ts.replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(clean_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception as e:
        raise ValidationError(f"Invalid ISO 8601 timestamp '{ts}': {e}") from e


def assert_finite_numbers(d: Dict[str, Any], context: str) -> None:
    """Assert all values in dictionary are valid finite numbers."""
    if not isinstance(d, dict):
        raise ValidationError(f"{context} must be a dictionary, got {type(d)}")
    for k, v in d.items():
        if not isinstance(v, (int, float)):
            raise ValidationError(f"{context}['{k}'] must be a numeric value, got {type(v)}")
        if math.isnan(v) or math.isinf(v):
            raise ValidationError(f"{context}['{k}'] must be finite, got {v}")


def validate_slice_window(window: Dict[str, Any]) -> bool:
    """Validate slice-level canonical window against CANONICAL_WINDOW_SCHEMA.md.
    
    Raises:
        ValidationError: If any schema constraint is violated.
    Returns:
        True if valid.
    """
    if not isinstance(window, dict):
        raise ValidationError(f"Window must be a dict, got {type(window)}")

    # 1. Source check
    source = window.get("source")
    if source not in VALID_SOURCES:
        raise ValidationError(f"Invalid source '{source}'. Must be one of {sorted(VALID_SOURCES)}")

    # 2. Required string identifiers
    for field in ["window_id", "slice_id", "nf_id"]:
        val = window.get(field)
        if not isinstance(val, str) or not val.strip():
            raise ValidationError(f"Slice window missing or invalid required string field '{field}'")

    # 3. Timestamps & duration
    start_dt = parse_iso_timestamp(window.get("window_start"))
    end_dt = parse_iso_timestamp(window.get("window_end"))
    if end_dt <= start_dt:
        raise ValidationError(f"window_end ({end_dt}) must be strictly after window_start ({start_dt})")

    duration = window.get("duration_sec")
    if not isinstance(duration, int) or duration <= 0:
        raise ValidationError(f"duration_sec must be positive integer, got {duration}")

    # 4. Feature containers
    raw_counters = window.get("raw_counters")
    if not isinstance(raw_counters, dict) or not raw_counters:
        raise ValidationError("Slice window missing raw_counters dictionary")
    assert_finite_numbers(raw_counters, "raw_counters")

    ratio_features = window.get("ratio_features")
    if not isinstance(ratio_features, dict) or not ratio_features:
        raise ValidationError("Slice window missing ratio_features dictionary")
    assert_finite_numbers(ratio_features, "ratio_features")

    comp_vec = window.get("composition_vector")
    if not isinstance(comp_vec, dict) or not comp_vec:
        raise ValidationError("Slice window missing composition_vector dictionary")
    assert_finite_numbers(comp_vec, "composition_vector")

    # 5. Ground truth labels
    gt = window.get("ground_truth")
    if not isinstance(gt, dict):
        raise ValidationError("Slice window missing ground_truth dictionary")
    if "is_attack" not in gt or not isinstance(gt["is_attack"], bool):
        raise ValidationError("ground_truth must contain boolean 'is_attack'")
    label = gt.get("label")
    if label not in VALID_LABELS:
        raise ValidationError(f"ground_truth['label'] must be one of {sorted(VALID_LABELS)}, got '{label}'")

    # Check consistency
    if gt["is_attack"] and label != "attack":
        raise ValidationError("ground_truth is_attack=True requires label='attack'")
    if not gt["is_attack"] and label != "benign":
        raise ValidationError("ground_truth is_attack=False requires label='benign'")

    # 6. Ensure no raw subscriber id leaks
    raw_id_pattern = re.compile(r"sim_[a-zA-Z0-9_]+|imsi[0-9]+", re.IGNORECASE)
    for k, v in window.items():
        if isinstance(v, str) and raw_id_pattern.search(v):
            raise ValidationError(f"Potential raw subscriber ID leaked in field '{k}': {v}")

    return True


def validate_device_window(window: Dict[str, Any]) -> bool:
    """Validate per-device canonical window against CANONICAL_WINDOW_SCHEMA.md.
    
    Raises:
        ValidationError: If any schema constraint is violated.
    Returns:
        True if valid.
    """
    if not isinstance(window, dict):
        raise ValidationError(f"Window must be a dict, got {type(window)}")

    # 1. Source check
    source = window.get("source")
    if source not in VALID_SOURCES:
        raise ValidationError(f"Invalid source '{source}'. Must be one of {sorted(VALID_SOURCES)}")

    # 2. Required string identifiers
    for field in ["window_id", "slice_id"]:
        val = window.get(field)
        if not isinstance(val, str) or not val.strip():
            raise ValidationError(f"Device window missing or invalid required string field '{field}'")

    # 3. Privacy & Device ID: MUST be 64-character lowercase hex digest
    dev_hash = window.get("device_id_hash")
    if not isinstance(dev_hash, str) or not HEX_64_REGEX.match(dev_hash):
        raise ValidationError(
            f"device_id_hash must be a 64-character hexadecimal HMAC-SHA256 digest, got '{dev_hash}'"
        )

    # 4. Device class check
    device_class = window.get("device_class")
    if device_class not in VALID_DEVICE_CLASSES:
        raise ValidationError(
            f"Invalid device_class '{device_class}'. Must be one of {sorted(VALID_DEVICE_CLASSES)}"
        )

    # 5. Timestamps & duration
    start_dt = parse_iso_timestamp(window.get("window_start"))
    end_dt = parse_iso_timestamp(window.get("window_end"))
    if end_dt <= start_dt:
        raise ValidationError(f"window_end ({end_dt}) must be strictly after window_start ({start_dt})")

    duration = window.get("duration_sec")
    if not isinstance(duration, int) or duration <= 0:
        raise ValidationError(f"duration_sec must be positive integer, got {duration}")

    # 6. Feature containers
    rate_features = window.get("rate_features")
    if not isinstance(rate_features, dict) or not rate_features:
        raise ValidationError("Device window missing rate_features dictionary")
    assert_finite_numbers(rate_features, "rate_features")

    ratio_features = window.get("ratio_features")
    if not isinstance(ratio_features, dict) or not ratio_features:
        raise ValidationError("Device window missing ratio_features dictionary")
    assert_finite_numbers(ratio_features, "ratio_features")

    raw_counters = window.get("raw_counters")
    if not isinstance(raw_counters, dict) or not raw_counters:
        raise ValidationError("Device window missing raw_counters dictionary")
    assert_finite_numbers(raw_counters, "raw_counters")

    # 7. Provisioning status container
    prov_status = window.get("provisioning_status")
    if not isinstance(prov_status, dict):
        raise ValidationError("Device window missing provisioning_status dictionary")
    if "is_provisioned" not in prov_status or not isinstance(prov_status["is_provisioned"], bool):
        raise ValidationError("provisioning_status must contain boolean 'is_provisioned'")

    # 8. Ground truth labels
    gt = window.get("ground_truth")
    if not isinstance(gt, dict):
        raise ValidationError("Device window missing ground_truth dictionary")
    if "is_attack" not in gt or not isinstance(gt["is_attack"], bool):
        raise ValidationError("ground_truth must contain boolean 'is_attack'")
    label = gt.get("label")
    if label not in VALID_LABELS:
        raise ValidationError(f"ground_truth['label'] must be one of {sorted(VALID_LABELS)}, got '{label}'")

    if gt["is_attack"] and label != "attack":
        raise ValidationError("ground_truth is_attack=True requires label='attack'")
    if not gt["is_attack"] and label != "benign":
        raise ValidationError("ground_truth is_attack=False requires label='benign'")

    # 9. Strict check: No raw ID anywhere in entire window structure
    raw_id_pattern = re.compile(r"sim_[a-zA-Z0-9_]+|imsi[0-9]+", re.IGNORECASE)
    for k, v in window.items():
        if isinstance(v, str) and raw_id_pattern.search(v):
            raise ValidationError(f"Potential raw subscriber ID leaked in field '{k}': {v}")

    return True


def validate_window(window: Dict[str, Any]) -> bool:
    """Validate any window (slice-level or per-device)."""
    if not isinstance(window, dict):
        raise ValidationError(f"Window must be a dict, got {type(window)}")
    if "device_id_hash" in window:
        return validate_device_window(window)
    return validate_slice_window(window)
