"""Unit tests for Digital Twin API and saved-metrics verification.

Verifies that:
1. The API endpoint supplies every number displayed on the Digital Twin page.
2. Every number comes directly from saved result files without inventing numbers.
3. Source badge displays 'Live lab' if and only if data/lab/windows.jsonl exists and validates.
4. Floor map topology, device states, and decision traces are deterministic and complete.
"""

import asyncio
import importlib.util
import json
from pathlib import Path
import unittest

# Import twin module directly to run independently of FastAPI environment
TWIN_MODULE_PATH = Path(__file__).resolve().parent.parent / "app" / "api" / "twin.py"
spec = importlib.util.spec_from_file_location("commshield_twin_api", TWIN_MODULE_PATH)
twin_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(twin_mod)

check_lab_validated = twin_mod.check_lab_validated
get_digital_twin_dashboard = twin_mod.get_digital_twin_dashboard
load_change_events = twin_mod.load_change_events
load_provisioning_catalog = twin_mod.load_provisioning_catalog
load_saved_three_arm_summary = twin_mod.load_saved_three_arm_summary
load_window_counts = twin_mod.load_window_counts
generate_topology_data = twin_mod.generate_topology_data


class TestDigitalTwinAPI(unittest.TestCase):
    """Test suite for CommShield 5G Digital Twin API."""

    @classmethod
    def setUpClass(cls):
        cls.project_root = Path(__file__).resolve().parent.parent.parent
        cls.summary_file = cls.project_root / "experiments" / "results" / "twin" / "three_arm_twin_summary.json"
        cls.prov_file = cls.project_root / "data" / "twin" / "provisioning.json"
        cls.events_file = cls.project_root / "data" / "twin" / "change_events.json"
        cls.counts_file = cls.project_root / "experiments" / "results" / "twin" / "window_counts.json"
        cls.lab_file = cls.project_root / "data" / "lab" / "windows.jsonl"

    def test_saved_files_exist(self):
        """Verify that all required result files exist on disk."""
        self.assertTrue(self.summary_file.is_file(), f"Missing {self.summary_file}")
        self.assertTrue(self.prov_file.is_file(), f"Missing {self.prov_file}")
        self.assertTrue(self.events_file.is_file(), f"Missing {self.events_file}")
        self.assertTrue(self.counts_file.is_file(), f"Missing {self.counts_file}")

    def test_lab_validated_logic(self):
        """Verify lab validation logic reflects actual data/lab/windows.jsonl status."""
        has_lab = self.lab_file.is_file()
        is_validated = check_lab_validated()
        self.assertEqual(has_lab, is_validated)

    def test_api_supplies_every_number_shown_on_page(self):
        """Verify that the API supplies every metric displayed on the frontend page."""
        resp = asyncio.run(
            get_digital_twin_dashboard(
                scenario="approved_onboarding",
                source="simulated_twin",
                time_step=15,
            )
        )

        # 1. Source and badge
        self.assertEqual(resp["source"], "simulated_twin")
        self.assertEqual(resp["source_badge"], "Simulated twin")
        self.assertIn("lab_validated", resp)

        # 2. Topology nodes and links
        topo = resp["topology"]
        self.assertEqual(len(topo["nodes"]), 4)
        node_ids = {n["id"] for n in topo["nodes"]}
        self.assertEqual(node_ids, {"gnb", "amf", "smf", "upf"})
        self.assertEqual(len(topo["links"]), 4)

        # 3. Slices
        slices = resp["slices"]
        self.assertEqual(len(slices), 3)
        slice_rates = {s["device_class"]: s["packet_rate_pps"] for s in slices}
        self.assertAlmostEqual(slice_rates["camera"], 41.25, places=2)
        self.assertAlmostEqual(slice_rates["AGV"], 80.0, places=2)
        self.assertAlmostEqual(slice_rates["sensor"], 10.0, places=2)

        # 4. Devices (39 floor map representatives)
        devices = resp["devices"]
        self.assertEqual(len(devices), 39)
        for dev in devices:
            self.assertIn("id", dev)
            self.assertIn("device_id_hash", dev)
            self.assertIn("device_class", dev)
            self.assertIn("slice_id", dev)
            self.assertIn("rate_pps", dev)
            self.assertIn("verdict", dev)
            self.assertIn(dev["verdict"], {"benign", "attack", "uncertain", "quarantined"})
            self.assertIn("action", dev)
            self.assertIn("visible", dev)

        # 5. Provisioning Card Numbers
        prov = resp["provisioning_card"]
        saved_prov = load_provisioning_catalog()
        saved_events = load_change_events()

        # Total catalog SIMs must exactly equal saved provisioning.json count
        self.assertEqual(prov["total_catalog_sims"], len(saved_prov["sims"]))
        self.assertEqual(prov["total_catalog_sims"], 200)

        # Batches must equal saved change_events.json count
        self.assertEqual(prov["total_batches"], len(saved_events["batches"]))
        self.assertEqual(prov["total_batches"], 3)

        # Approved onboarding numbers
        self.assertAlmostEqual(prov["provisioned_share"], 1.0, places=4)
        self.assertTrue(prov["fitting_volume"])
        self.assertEqual(prov["verdict"], "likely_benign")
        self.assertEqual(prov["action"], "adapt_candidate")
        self.assertEqual(prov["matched_event"]["batch_id"], "BATCH-OB-20261115-01")
        self.assertEqual(prov["matched_event"]["count"], 30)

        # 6. Contamination Meters
        meters = resp["contamination_meters"]
        summary = load_saved_three_arm_summary()
        approved_summary = summary["streams"]["approved_onboarding"]

        # Naive Retrain Numbers
        self.assertAlmostEqual(
            meters["naive"]["contamination_mean"],
            approved_summary["naive"]["contamination"]["mean"],
            places=5,
        )
        self.assertEqual(
            meters["naive"]["contamination_ci_95"],
            approved_summary["naive"]["contamination"]["ci_95"],
        )
        self.assertAlmostEqual(
            meters["naive"]["fpr_mean"],
            approved_summary["naive"]["fpr"]["mean"],
            places=5,
        )
        self.assertAlmostEqual(
            meters["naive"]["onboardings_adapted"],
            approved_summary["naive"]["onboardings_adapted"],
            places=2,
        )

        # CommShield Twin Numbers
        self.assertAlmostEqual(
            meters["commshield_twin"]["contamination_mean"],
            approved_summary["commshield_twin"]["contamination"]["mean"],
            places=5,
        )
        self.assertEqual(
            meters["commshield_twin"]["contamination_ci_95"],
            approved_summary["commshield_twin"]["contamination"]["ci_95"],
        )
        self.assertAlmostEqual(
            meters["commshield_twin"]["fpr_mean"],
            approved_summary["commshield_twin"]["fpr"]["mean"],
            places=5,
        )
        self.assertAlmostEqual(
            meters["commshield_twin"]["onboardings_adapted"],
            approved_summary["commshield_twin"]["onboardings_adapted"],
            places=2,
        )

        # 7. Decision Trace Steps
        trace = resp["decision_trace"]
        self.assertEqual(len(trace), 5)
        step_names = [s["name"] for s in trace]
        self.assertIn("Volume Scaling Multiplier", step_names[0])
        self.assertIn("Composition Divergence Test", step_names[1])
        self.assertIn("Provisioning Catalog & Event Match", step_names[2])
        self.assertIn("Per-Device Conformal Evaluation", step_names[3])
        self.assertIn("Governance Gate Verdict", step_names[4])

        # 8. Saved Metrics Reference
        saved_ref = resp["saved_metrics_reference"]
        window_counts = load_window_counts()
        self.assertEqual(saved_ref["aggregate_windows"], window_counts["total_windows_all"])
        self.assertEqual(saved_ref["aggregate_windows"], 11870)
        self.assertEqual(saved_ref["device_windows"], window_counts["total_device_windows"])
        self.assertEqual(saved_ref["device_windows"], 11510)
        self.assertEqual(saved_ref["slice_windows"], window_counts["total_slice_windows"])
        self.assertEqual(saved_ref["slice_windows"], 360)

    def test_all_scenarios_return_unambiguous_saved_metrics(self):
        """Verify metrics across all 4 benchmark streams match saved results exactly."""
        summary = load_saved_three_arm_summary()
        scenarios = [
            "approved_onboarding",
            "unprovisioned_burst",
            "provisioned_burst_no_event",
            "slow_ramp_in_onboarding",
        ]

        for sc in scenarios:
            resp = asyncio.run(get_digital_twin_dashboard(scenario=sc, time_step=15))
            saved_stream = summary["streams"][sc]
            self.assertEqual(
                resp["contamination_meters"]["naive"]["contamination_mean"],
                saved_stream["naive"]["contamination"]["mean"],
            )
            self.assertEqual(
                resp["contamination_meters"]["commshield_twin"]["contamination_mean"],
                saved_stream["commshield_twin"]["contamination"]["mean"],
            )

    def test_live_lab_source_badge(self):
        """Verify that Live lab badge is returned when source='lab' and lab is validated."""
        if check_lab_validated():
            resp = asyncio.run(get_digital_twin_dashboard(scenario="approved_onboarding", source="lab"))
            self.assertEqual(resp["source"], "lab")
            self.assertEqual(resp["source_badge"], "Live lab")
        else:
            resp = asyncio.run(get_digital_twin_dashboard(scenario="approved_onboarding", source="lab"))
            self.assertEqual(resp["source"], "simulated_twin")
            self.assertEqual(resp["source_badge"], "Simulated twin")


if __name__ == "__main__":
    unittest.main()
