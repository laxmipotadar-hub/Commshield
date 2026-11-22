r"""Validator CLI for CommShield Lab Canonical Windows.

Usage:
    Windows PowerShell:
        python -m lab.validate data\lab\windows.jsonl
    Ubuntu / Linux:
        python3 -m lab.validate data/lab/windows.jsonl
"""

import argparse
import json
from pathlib import Path
import re
import sys
from typing import Any, Dict, Set

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ml_engine.provisioning.schema import (
    ValidationError,
    validate_window,
    HEX_64_REGEX,
)


def validate_lab_windows_file(file_path: Path) -> Dict[str, Any]:
    """Validate a lab canonical windows jsonl file against schema contracts and privacy rules."""
    if not file_path.is_file():
        raise FileNotFoundError(f"Canonical windows file not found: {file_path}")

    total_count = 0
    slice_count = 0
    device_count = 0
    slices_seen: Set[str] = set()
    classes_seen: Set[str] = set()
    earliest_time = None
    latest_time = None

    raw_id_pattern = re.compile(r"sim_[a-zA-Z0-9_]+|imsi[0-9]+", re.IGNORECASE)

    with open(file_path, "r", encoding="utf-8", newline="\n") as f:
        for line_num, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue

            try:
                window = json.loads(line)
            except json.JSONDecodeError as e:
                raise ValidationError(f"Line {line_num}: Invalid JSON - {e}") from e

            # 1. Enforce strict schema validation
            validate_window(window)

            # 2. Enforce lab source contract
            source = window.get("source")
            if source != "lab":
                raise ValidationError(
                    f"Line {line_num}: Invalid source '{source}'. Expected 'lab' for lab telemetry."
                )

            # 3. Privacy audit: zero raw IMSIs or SIM IDs in entire serialized line
            if raw_id_pattern.search(line):
                raise ValidationError(
                    f"Line {line_num}: Raw subscriber identifier detected in serialized window record."
                )

            # Track window types and metadata
            total_count += 1
            slice_id = window.get("slice_id")
            if slice_id:
                slices_seen.add(slice_id)

            w_start = window.get("window_start")
            w_end = window.get("window_end")
            if earliest_time is None or (w_start and w_start < earliest_time):
                earliest_time = w_start
            if latest_time is None or (w_end and w_end > latest_time):
                latest_time = w_end

            if "device_id_hash" in window:
                device_count += 1
                dev_hash = window.get("device_id_hash", "")
                if not HEX_64_REGEX.match(dev_hash):
                    raise ValidationError(f"Line {line_num}: Invalid 64-hex device hash: {dev_hash}")
                cls_name = window.get("device_class")
                if cls_name:
                    classes_seen.add(cls_name)
            else:
                slice_count += 1

    if total_count == 0:
        raise ValidationError(f"File {file_path} is empty. No canonical windows found.")

    return {
        "file_path": str(file_path),
        "total_windows": total_count,
        "slice_windows": slice_count,
        "device_windows": device_count,
        "slices": sorted(list(slices_seen)),
        "device_classes": sorted(list(classes_seen)),
        "earliest_time": earliest_time,
        "latest_time": latest_time,
        "source": "lab",
        "raw_ids_leaked": 0,
    }


def main():
    parser = argparse.ArgumentParser(description="Validate CommShield Lab Canonical Windows")
    parser.add_argument(
        "file_path",
        nargs="?",
        type=Path,
        default=ROOT / "data" / "lab" / "windows.jsonl",
        help="Path to canonical windows JSONL file (default: data/lab/windows.jsonl)",
    )
    args = parser.parse_args()

    target_file = args.file_path
    print(f"Validating canonical windows in: {target_file}")
    try:
        report = validate_lab_windows_file(target_file)
        print("=" * 70)
        print("✓ VALIDATION SUCCESSFUL: All canonical windows pass schema contracts")
        print("=" * 70)
        print(f"  Source Tag        : {report['source']}")
        print(f"  Total Windows     : {report['total_windows']}")
        print(f"    - Slice-Level   : {report['slice_windows']}")
        print(f"    - Per-Device    : {report['device_windows']}")
        print(f"  Slices Evaluated  : {', '.join(report['slices'])}")
        print(f"  Device Classes    : {', '.join(report['device_classes'])}")
        print(f"  Time Window Range : {report['earliest_time']} to {report['latest_time']}")
        print(f"  Raw ID Audit      : PASSED (0 raw identifiers leaked; HMAC-SHA256 only)")
        print("=" * 70)
        sys.exit(0)
    except Exception as e:
        print("=" * 70)
        print(f"✗ VALIDATION FAILED: {e}")
        print("=" * 70)
        sys.exit(1)


if __name__ == "__main__":
    main()
# CommShield AI Core
