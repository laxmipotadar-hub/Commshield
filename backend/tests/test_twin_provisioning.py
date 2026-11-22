"""Unit and Integration Tests for Digital Twin Provisioning and Canonical Windows.

Covers:
1. Lookup correctness (provisioned flag, device class, slice, active event ID vs None).
2. Determinism across seeds (identical seeds yield identical outputs).
3. Labels on every window (ground_truth with is_attack bool and label).
4. Schema validation (strict enforcement via ml_engine/provisioning/schema.py).
5. Zero raw ID leakage (HMAC-SHA256 64-hex hashes only).
6. Seed separation (tuning seed disjoint from at least 10 test seeds).
"""

from datetime import datetime, timezone
import json
from pathlib import Path
import re
import sys
import unittest

ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ml_engine.provisioning.loader import ProvisioningLoader, hash_sim_id
from ml_engine.provisioning.schema import (
    ValidationError,
    validate_window,
    validate_slice_window,
    validate_device_window,
    VALID_SOURCES,
    HEX_64_REGEX,
)
from ml_engine.scenarios.twin_generator import (
    TwinScenarioGenerator,
    TUNING_SEED,
    TEST_SEEDS,
    STREAM_NAMES,
)


class TestTwinProvisioning(unittest.TestCase):
    """Test suite verifying Digital Twin provisioning and canonical schemas."""

    def setUp(self):
        self.loader = ProvisioningLoader()
        self.generator = TwinScenarioGenerator(seed=TUNING_SEED, loader=self.loader)

        # Load raw SIMs directly from source catalog to audit privacy
        prov_file = ROOT / "data" / "twin" / "provisioning.json"
        with open(prov_file, "r", encoding="utf-8", newline="\n") as f:
            data = json.load(f)
            self.raw_sims = [sim["sim_id"] for sim in data["sims"]]

    def test_lookup_correctness(self):
        """Verify lookup returns {provisioned, device_class, slice, event_id or None}."""
        # 1. Provisioned sensor inside active Batch 1 window (08:10 to 08:35 UTC)
        events_file = ROOT / "data" / "twin" / "change_events.json"
        with open(events_file, "r", encoding="utf-8", newline="\n") as f:
            batch1 = json.load(f)["batches"][0]
            target_sensor = batch1["sim_ids"][0]
            batch1_id = batch1["batch_id"]

        time_active = datetime(2026, 11, 15, 8, 20, 0, tzinfo=timezone.utc)
        res_active = self.loader.lookup(target_sensor, time_active)

        self.assertTrue(res_active["provisioned"])
        self.assertEqual(res_active["device_class"], "sensor")
        self.assertEqual(res_active["slice"], "sst-3-sd-030405")
        self.assertEqual(res_active["event_id"], batch1_id)

        # 2. Same sensor outside active event window
        time_outside = datetime(2026, 11, 15, 7, 0, 0, tzinfo=timezone.utc)
        res_outside = self.loader.lookup(target_sensor, time_outside)

        self.assertTrue(res_outside["provisioned"])
        self.assertEqual(res_outside["device_class"], "sensor")
        self.assertEqual(res_outside["slice"], "sst-3-sd-030405")
        self.assertIsNone(res_outside["event_id"])

        # 3. Lookup with pre-hashed ID produces identical result
        h_id = hash_sim_id(target_sensor)
        res_hashed = self.loader.lookup(h_id, time_active)
        self.assertEqual(res_active, res_hashed)

        # 4. Unprovisioned ID returns provisioned=False and None fields
        res_unprov = self.loader.lookup("unprovisioned_rogue_id_999", time_active)
        self.assertFalse(res_unprov["provisioned"])
        self.assertIsNone(res_unprov["device_class"])
        self.assertIsNone(res_unprov["slice"])
        self.assertIsNone(res_unprov["event_id"])

    def test_determinism(self):
        """Verify that identical seeds produce bitwise identical telemetry windows."""
        gen1 = TwinScenarioGenerator(seed=42, loader=self.loader)
        gen2 = TwinScenarioGenerator(seed=42, loader=self.loader)

        stream1 = gen1.generate_stream("approved_onboarding", num_windows=5)
        stream2 = gen2.generate_stream("approved_onboarding", num_windows=5)

        # Strip random UUIDs for value comparison
        for w in stream1["device_windows"]:
            w["window_id"] = "fixed-uuid"
        for w in stream2["device_windows"]:
            w["window_id"] = "fixed-uuid"

        self.assertEqual(stream1["device_windows"], stream2["device_windows"])

        # Different seed produces different values
        gen3 = TwinScenarioGenerator(seed=101, loader=self.loader)
        stream3 = gen3.generate_stream("approved_onboarding", num_windows=5)
        for w in stream3["device_windows"]:
            w["window_id"] = "fixed-uuid"

        self.assertNotEqual(stream1["device_windows"], stream3["device_windows"])

    def test_labels_on_every_window(self):
        """Verify every slice and device window has ground_truth with is_attack and label."""
        for stream_name in STREAM_NAMES:
            res = self.generator.generate_stream(stream_name, num_windows=10)

            # Check slice windows
            for sw in res["slice_windows"]:
                self.assertIn("ground_truth", sw)
                gt = sw["ground_truth"]
                self.assertIsInstance(gt["is_attack"], bool)
                self.assertIn(gt["label"], ["benign", "attack"])
                if gt["is_attack"]:
                    self.assertEqual(gt["label"], "attack")
                else:
                    self.assertEqual(gt["label"], "benign")

            # Check device windows
            for dw in res["device_windows"]:
                self.assertIn("ground_truth", dw)
                gt = dw["ground_truth"]
                self.assertIsInstance(gt["is_attack"], bool)
                self.assertIn(gt["label"], ["benign", "attack"])
                if gt["is_attack"]:
                    self.assertEqual(gt["label"], "attack")
                else:
                    self.assertEqual(gt["label"], "benign")

            # Approved onboarding must be 100% benign
            if stream_name == "approved_onboarding":
                self.assertEqual(res["counts"]["slice_attack"], 0)
                self.assertEqual(res["counts"]["device_attack"], 0)

    def test_schema_validation(self):
        """Verify schema validator enforces types, constraints, and source enum."""
        stream = self.generator.generate_stream("approved_onboarding", num_windows=2)
        valid_slice = stream["slice_windows"][0]
        valid_device = stream["device_windows"][0]

        # Valid windows pass validation
        self.assertTrue(validate_slice_window(valid_slice))
        self.assertTrue(validate_device_window(valid_device))
        self.assertTrue(validate_window(valid_slice))
        self.assertTrue(validate_window(valid_device))

        # Invalid source triggers ValidationError
        bad_source_window = dict(valid_slice)
        bad_source_window["source"] = "invalid_source_origin"
        with self.assertRaises(ValidationError):
            validate_slice_window(bad_source_window)

        # Non-64-hex device ID hash triggers ValidationError
        bad_hash_window = dict(valid_device)
        bad_hash_window["device_id_hash"] = "sim_sensor_12345"
        with self.assertRaises(ValidationError):
            validate_device_window(bad_hash_window)

    def test_no_raw_ids_in_output(self):
        """Verify no raw SIM IDs from provisioning appear in any emitted window."""
        for stream_name in STREAM_NAMES:
            res = self.generator.generate_stream(stream_name, num_windows=10)

            # Check device windows
            for dw in res["device_windows"]:
                dev_hash = dw["device_id_hash"]
                self.assertTrue(HEX_64_REGEX.match(dev_hash), f"Invalid hash: {dev_hash}")
                self.assertNotIn("sim_", dev_hash)

                serialized = json.dumps(dw)
                for raw_sim in self.raw_sims:
                    self.assertNotIn(raw_sim, serialized, f"Raw SIM {raw_sim} leaked in device window!")

            # Check slice windows
            for sw in res["slice_windows"]:
                serialized = json.dumps(sw)
                for raw_sim in self.raw_sims:
                    self.assertNotIn(raw_sim, serialized, f"Raw SIM {raw_sim} leaked in slice window!")

    def test_separate_tuning_and_test_seeds(self):
        """Verify tuning seed is disjoint from test seeds and at least 10 test seeds exist."""
        self.assertNotIn(TUNING_SEED, TEST_SEEDS)
        self.assertGreaterEqual(len(TEST_SEEDS), 10)

        # Run test across all 10 test seeds
        for t_seed in TEST_SEEDS:
            gen = TwinScenarioGenerator(seed=t_seed, loader=self.loader)
            res = gen.generate_stream("approved_onboarding", num_windows=2)
            self.assertEqual(res["seed"], t_seed)
            self.assertEqual(res["total_slice_windows"], 6)  # 3 slices x 2 windows


if __name__ == "__main__":
    unittest.main()
# CommShield AI Core
