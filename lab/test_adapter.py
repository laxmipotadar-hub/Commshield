"""Unit Tests for CommShield Open5GS Lab Adapter.

Enforces:
1. Offline execution exclusively using sample logs in lab/sample_logs/ (never a running core).
2. All generated windows pass ml_engine/provisioning/schema.py contracts.
3. Source field is strictly 'lab'.
4. Identifiers are cryptographically pseudonymised via HMAC-SHA256 (64-char hex).
5. Zero raw IMSI or SIM identifiers leaked in serialized output.
6. Validation CLI module python -m lab.validate succeeds.
"""

import json
from pathlib import Path
import re
import sys
import unittest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lab.adapter import LabAdapter
from lab.validate import validate_lab_windows_file
from ml_engine.provisioning.schema import validate_window, HEX_64_REGEX


class TestLabAdapter(unittest.TestCase):
    """Test suite verifying lab adapter offline processing and canonical schema compliance."""

    @classmethod
    def setUpClass(cls):
        cls.sample_logs_dir = ROOT / "lab" / "sample_logs"
        cls.output_file = ROOT / "data" / "lab" / "windows.jsonl"
        cls.adapter = LabAdapter(
            sample_logs_dir=cls.sample_logs_dir,
            output_file=cls.output_file,
        )
        cls.emitted_count = cls.adapter.process_and_emit()

    def test_sample_logs_exist(self):
        """Verify sample logs directory contains required offline captures."""
        self.assertTrue((self.sample_logs_dir / "open5gs_amf.log").is_file())
        self.assertTrue((self.sample_logs_dir / "open5gs_upf.log").is_file())
        self.assertTrue((self.sample_logs_dir / "amf_metrics.json").is_file())

    def test_offline_execution_succeeds(self):
        """Verify adapter executes offline without network or running 5G core."""
        self.assertTrue(self.output_file.is_file())
        self.assertGreater(self.emitted_count, 0)

    def test_canonical_schema_validation_every_window(self):
        """Verify every emitted window passes schema validator in ml_engine/provisioning/schema.py."""
        with open(self.output_file, "r", encoding="utf-8", newline="\n") as f:
            for line_idx, line in enumerate(f, start=1):
                line = line.strip()
                if line:
                    window = json.loads(line)
                    # Must validate cleanly without raising ValidationError
                    self.assertTrue(validate_window(window), f"Window at line {line_idx} failed validation")

    def test_source_tag_is_lab(self):
        """Verify every emitted window strictly specifies source='lab'."""
        with open(self.output_file, "r", encoding="utf-8", newline="\n") as f:
            for line in f:
                line = line.strip()
                if line:
                    window = json.loads(line)
                    self.assertEqual(window.get("source"), "lab")

    def test_pseudonymisation_and_zero_raw_ids(self):
        """Verify all subscriber identifiers are HMAC-SHA256 hashed and no raw IMSIs appear."""
        raw_imsi_regex = re.compile(r"imsi[-_]?[0-9]+", re.IGNORECASE)
        raw_sim_regex = re.compile(r"sim_[a-zA-Z0-9_]+", re.IGNORECASE)

        with open(self.output_file, "r", encoding="utf-8", newline="\n") as f:
            for line_idx, line in enumerate(f, start=1):
                # Check serialized line directly
                self.assertIsNone(
                    raw_imsi_regex.search(line),
                    f"Line {line_idx} leaked raw IMSI identifier: {line}",
                )
                self.assertIsNone(
                    raw_sim_regex.search(line),
                    f"Line {line_idx} leaked raw SIM identifier: {line}",
                )

                window = json.loads(line)
                if "device_id_hash" in window:
                    dev_hash = window["device_id_hash"]
                    self.assertTrue(
                        HEX_64_REGEX.match(dev_hash),
                        f"Line {line_idx} has invalid 64-hex device hash: {dev_hash}",
                    )

    def test_validate_module_function(self):
        """Verify validate_lab_windows_file accurately inspects the generated output."""
        report = validate_lab_windows_file(self.output_file)
        self.assertEqual(report["source"], "lab")
        self.assertEqual(report["total_windows"], self.emitted_count)
        self.assertGreater(report["slice_windows"], 0)
        self.assertGreater(report["device_windows"], 0)
        self.assertEqual(report["raw_ids_leaked"], 0)
        self.assertIn("sst-1-sd-010203", report["slices"])
        self.assertIn("sst-2-sd-020304", report["slices"])
        self.assertIn("sst-3-sd-030405", report["slices"])


if __name__ == "__main__":
    unittest.main()
# CommShield AI Core
