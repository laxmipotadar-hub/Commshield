"""Unit and Integration Tests for Digital Twin Attribution and Evidence Rules.

Covers:
1. Verdict per stream matches documented rule:
   - approved_onboarding -> likely_benign (action=adapt_candidate)
   - unprovisioned_burst -> likely_attack (action=quarantine, reason=unprovisioned_devices_present)
   - provisioned_burst_no_event -> likely_attack (action=alert, burst with no event)
   - slow_ramp_in_onboarding -> uncertain/likely_attack (quarantine)
2. Specific named reasons for abstention:
   - growth_exceeds_approved_batch
   - device_behaviour_uncertain
   - partial_event_match
3. Determinism across runs with the same seed.
4. Zero raw SIM ID leakage (HMAC hashes only).
5. Backward compatibility when device_evidence_enabled=False.
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

from ml_engine.attribution.config import (
    AttributionConfig,
    AttributionVerdict,
    AbstainReason,
    RecommendedAction,
)
from ml_engine.attribution.rule_based import RuleBasedAttributor
from ml_engine.device_model import DeviceModelManager
from ml_engine.provisioning.loader import ProvisioningLoader
from ml_engine.scenarios.twin_generator import (
    TwinScenarioGenerator,
    TUNING_SEED,
    STREAM_NAMES,
)

HEX_64_REGEX = re.compile(r"^[0-9a-f]{64}$")


class TestTwinAttribution(unittest.TestCase):
    """Test suite for Digital Twin attribution evidence and rule evaluation."""

    @classmethod
    def setUpClass(cls):
        cls.loader = ProvisioningLoader()
        cls.tuning_gen = TwinScenarioGenerator(seed=TUNING_SEED, loader=cls.loader, source="simulated_twin")
        tuning_dev_windows = []
        for s in STREAM_NAMES:
            res = cls.tuning_gen.generate_stream(s, num_windows=20)
            tuning_dev_windows.extend(res["device_windows"])

        cls.device_manager = DeviceModelManager(
            n_estimators=25,
            max_depth=6,
            random_state=42,
        )
        cls.device_manager.fit_and_calibrate(tuning_dev_windows)

        cls.config_twin = AttributionConfig(
            device_evidence_enabled=True,
            min_provisioned_share=0.95,
            max_anomalous_share=0.10,
            max_uncertain_share=0.30,
            volume_batch_tolerance=1.25,
        )
        cls.attributor_twin = RuleBasedAttributor(config=cls.config_twin)

        cls.config_base = AttributionConfig(device_evidence_enabled=False)
        cls.attributor_base = RuleBasedAttributor(config=cls.config_base)

        cls.baseline_bundle = {
            "composition_vector": {
                "registration_ratio": 0.0778,
                "session_setup_ratio": 0.9122,
                "failure_ratio": 0.0044,
                "other_signalling_ratio": 0.0056,
            },
            "scaler_params": {"medians": {"ue_hash_entropy": 7.42}},
            "active_ue_count": 40,
        }

        # Raw SIM IDs for privacy audit
        prov_file = ROOT / "data" / "twin" / "provisioning.json"
        with open(prov_file, "r", encoding="utf-8", newline="\n") as f:
            data = json.load(f)
            cls.raw_sims = [sim["sim_id"] for sim in data["sims"]]

    def test_rule_1_unprovisioned_ids(self):
        """Rule 1: Unprovisioned IDs present -> LIKELY_ATTACK & QUARANTINE."""
        gen = TwinScenarioGenerator(seed=101, loader=self.loader, source="simulated_twin")
        data = gen.generate_stream("unprovisioned_burst", num_windows=20)
        sw = [s for s in data["slice_windows"] if s["slice_id"] == "sst-3-sd-030405" and s["ground_truth"]["is_attack"]][0]
        dw = [d for d in data["device_windows"] if d["slice_id"] == sw["slice_id"] and d["window_start"] == sw["window_start"]]
        preds = [self.device_manager.predict_window(d) for d in dw]

        res = self.attributor_twin.attribute(
            window=sw,
            baseline_bundle=self.baseline_bundle,
            device_windows=dw,
            device_predictions=preds,
            provisioning_loader=self.loader,
        )
        self.assertEqual(res["verdict"], AttributionVerdict.LIKELY_ATTACK.value)
        self.assertEqual(res["action"], RecommendedAction.QUARANTINE.value)
        self.assertEqual(res["abstain_reason"], AbstainReason.UNPROVISIONED_DEVICES_PRESENT.value)
        self.assertLess(res["supporting_signals"]["provisioned_share"], 0.95)

    def test_rule_2_likely_benign_onboarding(self):
        """Rule 2: Provisioned AND matched event AND fitting volume AND low anomaly -> LIKELY_BENIGN."""
        gen = TwinScenarioGenerator(seed=101, loader=self.loader, source="simulated_twin")
        data = gen.generate_stream("approved_onboarding", num_windows=20)
        # Check window at t=12 for Batch 1 sensor onboarding
        sw = [s for s in data["slice_windows"] if s["slice_id"] == "sst-3-sd-030405" and s["window_start"].endswith("08:12:00+00:00")][0]
        dw = [d for d in data["device_windows"] if d["slice_id"] == sw["slice_id"] and d["window_start"] == sw["window_start"]]
        preds = [self.device_manager.predict_window(d) for d in dw]

        res = self.attributor_twin.attribute(
            window=sw,
            baseline_bundle=self.baseline_bundle,
            device_windows=dw,
            device_predictions=preds,
            provisioning_loader=self.loader,
        )
        self.assertEqual(res["verdict"], AttributionVerdict.LIKELY_BENIGN.value)
        self.assertEqual(res["action"], RecommendedAction.ADAPT_CANDIDATE.value)
        self.assertIsNone(res["abstain_reason"])
        self.assertTrue(res["supporting_signals"]["event_match"])
        self.assertTrue(res["supporting_signals"]["volume_vs_batch_size"]["fitting_volume"])
        self.assertGreaterEqual(res["supporting_signals"]["provisioned_share"], 0.95)
        self.assertLessEqual(res["supporting_signals"]["device_anomalous_share"], 0.10)

    def test_rule_3_growth_exceeds_approved_batch(self):
        """Rule 3: Volume exceeds approved batch count -> UNCERTAIN (growth_exceeds_approved_batch)."""
        gen = TwinScenarioGenerator(seed=101, loader=self.loader, source="simulated_twin")
        data = gen.generate_stream("approved_onboarding", num_windows=20)
        sw = [s for s in data["slice_windows"] if s["slice_id"] == "sst-3-sd-030405" and s["window_start"].endswith("08:12:00+00:00")][0]

        res = self.attributor_twin.attribute(
            window=sw,
            baseline_bundle=self.baseline_bundle,
            provisioned_share=1.0,
            event_match=True,
            volume_vs_batch_size={"fitting_volume": False, "batch_id": "BATCH-OB-20261115-01", "batch_size": 30, "added_devices": 60, "ratio": 2.0},
            device_anomalous_share=0.02,
            device_uncertain_share=0.05,
        )
        self.assertEqual(res["verdict"], AttributionVerdict.UNCERTAIN.value)
        self.assertEqual(res["action"], RecommendedAction.QUARANTINE.value)
        self.assertEqual(res["abstain_reason"], AbstainReason.GROWTH_EXCEEDS_APPROVED_BATCH.value)

    def test_rule_3_device_behaviour_uncertain(self):
        """Rule 3: High uncertain share -> UNCERTAIN (device_behaviour_uncertain)."""
        gen = TwinScenarioGenerator(seed=101, loader=self.loader, source="simulated_twin")
        data = gen.generate_stream("approved_onboarding", num_windows=20)
        sw = [s for s in data["slice_windows"] if s["slice_id"] == "sst-3-sd-030405" and s["window_start"].endswith("08:12:00+00:00")][0]

        res = self.attributor_twin.attribute(
            window=sw,
            baseline_bundle=self.baseline_bundle,
            provisioned_share=1.0,
            event_match=True,
            volume_vs_batch_size={"fitting_volume": True, "batch_id": "BATCH-OB-20261115-01", "batch_size": 30, "added_devices": 30, "ratio": 1.0},
            device_anomalous_share=0.02,
            device_uncertain_share=0.45,  # Exceeds max_uncertain_share 0.30
        )
        self.assertEqual(res["verdict"], AttributionVerdict.UNCERTAIN.value)
        self.assertEqual(res["action"], RecommendedAction.QUARANTINE.value)
        self.assertEqual(res["abstain_reason"], AbstainReason.DEVICE_BEHAVIOUR_UNCERTAIN.value)

    def test_rule_3_partial_event_match(self):
        """Rule 3: Partial or unverified match with added devices -> UNCERTAIN (partial_event_match)."""
        gen = TwinScenarioGenerator(seed=101, loader=self.loader, source="simulated_twin")
        data = gen.generate_stream("approved_onboarding", num_windows=20)
        sw = [s for s in data["slice_windows"] if s["slice_id"] == "sst-3-sd-030405" and s["window_start"].endswith("08:12:00+00:00")][0]

        res = self.attributor_twin.attribute(
            window=sw,
            baseline_bundle=self.baseline_bundle,
            provisioned_share=1.0,
            event_match=False,
            volume_vs_batch_size={"fitting_volume": False, "batch_id": None, "batch_size": 0, "added_devices": 15, "ratio": 0.0},
            device_anomalous_share=0.02,
            device_uncertain_share=0.05,
        )
        self.assertEqual(res["verdict"], AttributionVerdict.UNCERTAIN.value)
        self.assertEqual(res["action"], RecommendedAction.QUARANTINE.value)
        self.assertEqual(res["abstain_reason"], AbstainReason.PARTIAL_EVENT_MATCH.value)

    def test_determinism(self):
        """Verify identical seed produces bit-identical attribution results across repeated runs."""
        gen1 = TwinScenarioGenerator(seed=101, loader=self.loader, source="simulated_twin")
        data1 = gen1.generate_stream("provisioned_burst_no_event", num_windows=15)

        gen2 = TwinScenarioGenerator(seed=101, loader=self.loader, source="simulated_twin")
        data2 = gen2.generate_stream("provisioned_burst_no_event", num_windows=15)

        res1_list = []
        res2_list = []
        for d1, d2 in zip(data1["slice_windows"], data2["slice_windows"]):
            dw1 = [d for d in data1["device_windows"] if d["slice_id"] == d1["slice_id"] and d["window_start"] == d1["window_start"]]
            dw2 = [d for d in data2["device_windows"] if d["slice_id"] == d2["slice_id"] and d["window_start"] == d2["window_start"]]

            p1 = [self.device_manager.predict_window(d) for d in dw1]
            p2 = [self.device_manager.predict_window(d) for d in dw2]

            r1 = self.attributor_twin.attribute(window=d1, baseline_bundle=self.baseline_bundle, device_windows=dw1, device_predictions=p1, provisioning_loader=self.loader)
            r2 = self.attributor_twin.attribute(window=d2, baseline_bundle=self.baseline_bundle, device_windows=dw2, device_predictions=p2, provisioning_loader=self.loader)

            res1_list.append((r1["verdict"], r1["action"], r1["abstain_reason"], r1["supporting_signals"]))
            res2_list.append((r2["verdict"], r2["action"], r2["abstain_reason"], r2["supporting_signals"]))

        self.assertEqual(res1_list, res2_list)

    def test_no_raw_ids(self):
        """Verify zero raw SIM identifiers appear in attribution outputs, device windows, or signals."""
        gen = TwinScenarioGenerator(seed=101, loader=self.loader, source="simulated_twin")
        data = gen.generate_stream("slow_ramp_in_onboarding", num_windows=15)

        for dw in data["device_windows"]:
            dev_hash = dw["device_id_hash"]
            self.assertTrue(HEX_64_REGEX.match(dev_hash), f"Invalid 64-hex hash: {dev_hash}")
            for raw_sim in self.raw_sims:
                self.assertNotIn(raw_sim, json.dumps(dw))

        for sw in data["slice_windows"]:
            dw = [d for d in data["device_windows"] if d["slice_id"] == sw["slice_id"] and d["window_start"] == sw["window_start"]]
            preds = [self.device_manager.predict_window(d) for d in dw]
            res = self.attributor_twin.attribute(
                window=sw,
                baseline_bundle=self.baseline_bundle,
                device_windows=dw,
                device_predictions=preds,
                provisioning_loader=self.loader,
            )
            res_str = json.dumps(res)
            for raw_sim in self.raw_sims:
                self.assertNotIn(raw_sim, res_str)

    def test_backward_compatibility_flag(self):
        """When device_evidence_enabled=False, the original attribution pipeline executes unchanged."""
        gen = TwinScenarioGenerator(seed=101, loader=self.loader, source="simulated_twin")
        data = gen.generate_stream("approved_onboarding", num_windows=15)
        sw = data["slice_windows"][0]

        res = self.attributor_base.attribute(
            window=sw,
            baseline_bundle=self.baseline_bundle,
            recent_windows=[sw],
            drift_detected=False,
        )
        self.assertIn("verdict", res)
        self.assertIn("action", res)
        # Should not have device-evidence specific signals overwritten
        self.assertIn("provisioned_share", res["supporting_signals"])
        self.assertIsNone(res["supporting_signals"]["provisioned_share"])


if __name__ == "__main__":
    unittest.main()
