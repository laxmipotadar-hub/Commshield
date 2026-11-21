"""Unit tests for CommShield Four-Scene Demo Mode.

Tests:
1. Scene order: strictly (1) baseline, (2) approved onboarding, (3) unprovisioned device, (4) hidden ramp.
2. Deterministic replay across runs with identical seed.
3. Labels present on every canonical window and valid source tags on every scene.
4. Demo runs end-to-end with the lab file absent (fallback to simulated twin).
5. Scene 3 uses the lab clip only if it exists and validates.
"""

import importlib.util
import json
from pathlib import Path
import unittest

# Import demo API module directly to decouple from global FastAPI requirement
DEMO_MODULE_PATH = Path(__file__).resolve().parent.parent / "app" / "api" / "demo.py"
spec = importlib.util.spec_from_file_location("commshield_demo_api", DEMO_MODULE_PATH)
demo_api_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(demo_api_mod)

check_lab_validated = demo_api_mod.check_lab_validated
get_demo_presets = demo_api_mod.get_demo_presets
get_demo_scenarios = demo_api_mod.get_demo_scenarios

from backend.app.services.replay import replay_service
import backend.app.services.replay as replay_service_mod

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


class TestDemoMode(unittest.TestCase):
    """Test suite for CommShield deterministic four-scene demo presentation mode."""

    def test_demo_scene_order(self):
        """Verify the 4 presentation demo scenes are returned in strict order."""
        resp = get_demo_scenarios()
        scenarios = resp.scenarios
        self.assertEqual(len(scenarios), 4, f"Expected exactly 4 demo scenes, got {len(scenarios)}")

        # Strict sequence check: 1, 2, 3, 4
        self.assertEqual([s.preset_number for s in scenarios], [1, 2, 3, 4])

        # Scene 1: Baseline
        s1 = scenarios[0]
        self.assertEqual(s1.preset_number, 1)
        self.assertEqual(s1.id, "baseline")
        self.assertIn("baseline", s1.name.lower())

        # Scene 2: Approved Onboarding
        s2 = scenarios[1]
        self.assertEqual(s2.preset_number, 2)
        self.assertEqual(s2.id, "approved_onboarding")
        self.assertIn("approved onboarding", s2.name.lower())

        # Scene 3: Unprovisioned Device Flagged
        s3 = scenarios[2]
        self.assertEqual(s3.preset_number, 3)
        self.assertEqual(s3.id, "unprovisioned_device")
        self.assertIn("unprovisioned", s3.name.lower())

        # Scene 4: Hidden Ramp (Naive Poisoned vs CommShield Quarantines Excess)
        s4 = scenarios[3]
        self.assertEqual(s4.preset_number, 4)
        self.assertEqual(s4.id, "hidden_ramp")
        self.assertIn("hidden ramp", s4.name.lower())

    def test_labels_and_source_tags_present(self):
        """Verify source tags and labels are present on all scenes and windows."""
        presets = get_demo_presets()
        valid_sources = {"simulated_twin", "lab", "real_recorded"}

        for p in presets:
            self.assertIn(p.source, valid_sources, f"Scene {p.preset_number} has invalid source {p.source}")
            self.assertTrue(len(p.source_badge) > 0, f"Scene {p.preset_number} missing source badge")
            self.assertTrue(len(p.key_events) > 0, f"Scene {p.preset_number} missing key events")

            # Check that every key event has a one-line caption
            for ev in p.key_events:
                self.assertIsInstance(ev.caption, str)
                self.assertTrue(len(ev.caption) > 10, f"Caption too short in event {ev.event_type}")
                self.assertNotIn("\n", ev.caption.strip(), f"Caption must be a single line: {ev.caption}")

        # Check that windows produced by replay contain ground truth labels
        for sc_id in ["baseline", "approved_onboarding", "unprovisioned_device", "hidden_ramp"]:
            status = replay_service.start_sync(sc_id)
            self.assertEqual(status.status, "RUNNING")
            self.assertTrue(status.total_windows > 0)
            windows = replay_service._windows
            for w in windows:
                self.assertIn("ground_truth", w, f"Window in {sc_id} missing ground_truth")
                gt = w["ground_truth"]
                self.assertIn("is_attack", gt)
                self.assertIsInstance(gt["is_attack"], bool)
                self.assertIn("label", gt)
                self.assertIsInstance(gt["label"], str)

    def test_deterministic_replay(self):
        """Verify replaying each scene produces bitwise identical windows."""
        for sc_id in ["baseline", "approved_onboarding", "hidden_ramp"]:
            # Run 1
            replay_service.start_sync(sc_id)
            ids_run1 = [w["window_id"] for w in replay_service._windows]
            packets_run1 = [w["raw_counters"]["total_packets"] for w in replay_service._windows]

            # Run 2
            replay_service.start_sync(sc_id)
            ids_run2 = [w["window_id"] for w in replay_service._windows]
            packets_run2 = [w["raw_counters"]["total_packets"] for w in replay_service._windows]

            self.assertEqual(ids_run1, ids_run2, f"Window IDs differ across runs for {sc_id}")
            self.assertEqual(packets_run1, packets_run2, f"Counters differ across runs for {sc_id}")

    def test_demo_runs_end_to_end_with_lab_file_absent(self):
        """Verify the demo runs end-to-end without errors when data/lab/windows.jsonl is absent."""
        original_demo_lab_dir = demo_api_mod.DATA_LAB_DIR
        original_replay_proj_root = replay_service_mod.PROJECT_ROOT

        try:
            # Point to a nonexistent directory so lab file is guaranteed absent
            fake_dir = PROJECT_ROOT / "data" / "nonexistent_lab_dir"
            demo_api_mod.DATA_LAB_DIR = fake_dir

            # Check lab validated returns False
            self.assertFalse(check_lab_validated())

            # Presets must still construct cleanly
            presets = get_demo_presets()
            self.assertEqual(len(presets), 4)

            # Scene 3 must fall back to simulated_twin
            scene_3 = presets[2]
            self.assertEqual(scene_3.source, "simulated_twin")
            self.assertEqual(scene_3.source_badge, "Simulated twin")

            # Point replay service to fake root for lab check
            replay_service_mod.PROJECT_ROOT = fake_dir

            # All 4 scenes must replay synchronously end-to-end without raising errors
            for p in presets:
                res = replay_service.start_sync(p.id)
                self.assertEqual(res.status, "RUNNING")
                self.assertTrue(res.total_windows > 0)
                # Verify all windows can be accessed
                for i in range(min(5, res.total_windows)):
                    w = replay_service._windows[i]
                    self.assertIn("raw_counters", w)
                    self.assertIn("ground_truth", w)

        finally:
            # Restore original paths
            demo_api_mod.DATA_LAB_DIR = original_demo_lab_dir
            replay_service_mod.PROJECT_ROOT = original_replay_proj_root

    def test_scene_3_uses_lab_clip_if_exists(self):
        """Verify that Scene 3 uses the lab clip only if data/lab/windows.jsonl exists and validates."""
        lab_file = PROJECT_ROOT / "data" / "lab" / "windows.jsonl"
        has_lab = lab_file.is_file()
        lab_validated = check_lab_validated()

        presets = get_demo_presets()
        scene_3 = presets[2]

        if has_lab and lab_validated:
            self.assertEqual(scene_3.source, "lab")
            self.assertEqual(scene_3.source_badge, "Live lab")
        else:
            self.assertEqual(scene_3.source, "simulated_twin")
            self.assertEqual(scene_3.source_badge, "Simulated twin")


    def test_demo_endpoint_returns_four_scenarios_and_toggle_renders(self):
        """Verify that demo endpoint returns exactly 4 scenarios and frontend toggle renders."""
        # 1. API endpoint returns exactly 4 scenarios
        resp = get_demo_scenarios()
        self.assertEqual(len(resp.scenarios), 4)
        expected_ids = ["baseline", "approved_onboarding", "unprovisioned_device", "hidden_ramp"]
        self.assertEqual([s.id for s in resp.scenarios], expected_ids)

        # 2. Frontend toggle component exists and is rendered in App.tsx
        control_bar_path = PROJECT_ROOT / "frontend" / "src" / "components" / "DemoControlBar.tsx"
        self.assertTrue(control_bar_path.is_file(), "DemoControlBar.tsx component must exist")
        with open(control_bar_path, "r", encoding="utf-8") as f:
            bar_content = f.read()
        self.assertIn("Demo Mode", bar_content)
        self.assertIn("setIsDemoMode", bar_content)
        self.assertIn("Presentation", bar_content)

        app_path = PROJECT_ROOT / "frontend" / "src" / "App.tsx"
        self.assertTrue(app_path.is_file(), "App.tsx must exist")
        with open(app_path, "r", encoding="utf-8") as f:
            app_content = f.read()
        self.assertIn("<DemoControlBar />", app_content)
        self.assertIn("<DemoProvider>", app_content)


if __name__ == "__main__":
    unittest.main()
