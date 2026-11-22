"""Tests for Per-Device Behavior Model and Split Conformal Abstention.

Verifies:
1. Calibration set is strictly disjoint from training and threshold sets.
2. Conformal p-value computation is mathematically exact on toy examples.
3. Model fitting, scoring, and p-value generation are bitwise deterministic.
4. Zero raw subscriber IDs in any window, model state, or evaluation output.
5. Held-out device class (AGV) is never trained on and always abstained.
"""

from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ml_engine.device_model import (
    DeviceIsolationForest,
    DeviceModelManager,
    HELD_OUT_CLASS,
    TRAINED_CLASSES,
    compute_conformal_pvalue,
    evaluate_device_verdict,
)
from ml_engine.provisioning.loader import ProvisioningLoader
from ml_engine.scenarios.twin_generator import TwinScenarioGenerator, TUNING_SEED


class TestDeviceModel(unittest.TestCase):
    """Test suite for per-device behavior models and conformal calibration."""

    @classmethod
    def setUpClass(cls):
        cls.loader = ProvisioningLoader()
        cls.generator = TwinScenarioGenerator(seed=TUNING_SEED, loader=cls.loader)

        # Generate small tuning set for testing
        cls.tuning_windows = []
        for s_name in ["approved_onboarding", "unprovisioned_burst"]:
            s_res = cls.generator.generate_stream(s_name, num_windows=5)
            cls.tuning_windows.extend(s_res["device_windows"])

        cls.manager = DeviceModelManager(
            n_estimators=10,
            max_depth=4,
            random_state=42,
        )
        cls.cal_report = cls.manager.fit_and_calibrate(cls.tuning_windows)

        # Load raw SIMs for privacy audit
        prov_file = ROOT / "data" / "twin" / "provisioning.json"
        with open(prov_file, "r", encoding="utf-8", newline="\n") as f:
            cls.raw_sims = [sim["sim_id"] for sim in json.load(f)["sims"]]

    def test_calibration_disjoint_from_training(self):
        """Verify calibration windows are 100% disjoint from training and threshold sets."""
        for dev_class in TRAINED_CLASSES:
            ids_info = self.manager.split_window_ids[dev_class]
            train_ids = ids_info["train_ids"]
            thresh_ids = ids_info["thresh_ids"]
            cal_ids = ids_info["cal_ids"]

            self.assertGreater(len(train_ids), 0)
            self.assertGreater(len(cal_ids), 0)
            self.assertGreater(len(thresh_ids), 0)

            # Assert complete pairwise disjointness
            self.assertTrue(train_ids.isdisjoint(cal_ids), f"Train/Cal overlap in {dev_class}")
            self.assertTrue(train_ids.isdisjoint(thresh_ids), f"Train/Thresh overlap in {dev_class}")
            self.assertTrue(cal_ids.isdisjoint(thresh_ids), f"Cal/Thresh overlap in {dev_class}")

    def test_pvalue_correct_on_toy_example(self):
        """Verify split-conformal p-value computation with exact (n+1) correction."""
        # Calibration scores: 4 points [0.10, 0.20, 0.30, 0.40]
        # n = 4, denominator = 5
        cal_scores = [0.10, 0.20, 0.30, 0.40]

        # Case 1: test_score = 0.25 -> extreme count = 2 (0.30, 0.40) -> p = (1 + 2) / 5 = 0.60
        self.assertAlmostEqual(compute_conformal_pvalue(0.25, cal_scores), 0.60, places=5)

        # Case 2: test_score = 0.50 -> extreme count = 0 -> p = (1 + 0) / 5 = 0.20 = 1/(n+1)
        self.assertAlmostEqual(compute_conformal_pvalue(0.50, cal_scores), 0.20, places=5)

        # Case 3: test_score = 0.05 -> extreme count = 4 -> p = (1 + 4) / 5 = 1.0
        self.assertAlmostEqual(compute_conformal_pvalue(0.05, cal_scores), 1.00, places=5)

        # Case 4: test_score = 0.40 -> extreme count = 1 (0.40) -> p = (1 + 1) / 5 = 0.40
        self.assertAlmostEqual(compute_conformal_pvalue(0.40, cal_scores), 0.40, places=5)

    def test_determinism(self):
        """Verify Isolation Forest training and inference are bitwise deterministic."""
        import random
        rng = random.Random(42)
        X_train = [[rng.uniform(0.0, 100.0) for _ in range(7)] for _ in range(50)]
        sample = [50.0, 50.0, 50.0, 50.0, 50.0, 50.0, 50.0]

        f1 = DeviceIsolationForest(n_estimators=15, max_depth=5, random_state=42).fit(X_train)
        f2 = DeviceIsolationForest(n_estimators=15, max_depth=5, random_state=42).fit(X_train)

        score1 = f1.score(sample)
        score2 = f2.score(sample)
        self.assertEqual(score1, score2)

        # Different seed produces different score
        f3 = DeviceIsolationForest(n_estimators=15, max_depth=5, random_state=999).fit(X_train)
        self.assertNotEqual(score1, f3.score(sample))

    def test_no_raw_ids_in_model_and_results(self):
        """Verify no raw SIM IDs appear anywhere in predictions or result artifacts."""
        stream_res = self.generator.generate_stream("approved_onboarding", num_windows=2)
        for dw in stream_res["device_windows"]:
            pred = self.manager.predict_window(dw)
            serialized = json.dumps(pred)

            for raw_sim in self.raw_sims:
                self.assertNotIn(raw_sim, serialized, f"Raw SIM {raw_sim} leaked in prediction!")

        # Also check saved summary file
        summary_path = ROOT / "experiments" / "results" / "device_model" / "device_model_summary.json"
        if summary_path.is_file():
            with open(summary_path, "r", encoding="utf-8", newline="\n") as f:
                content = f.read()
                for raw_sim in self.raw_sims:
                    self.assertNotIn(raw_sim, content, f"Raw SIM {raw_sim} leaked in summary JSON!")

    def test_held_out_class_never_trained_on(self):
        """Verify held-out class (AGV) is never trained and always abstained."""
        # 1. Assert AGV is not in trained models dictionary
        self.assertNotIn(HELD_OUT_CLASS, self.manager.models)
        self.assertEqual(HELD_OUT_CLASS, "AGV")

        # 2. Find an AGV window and predict
        agv_windows = [w for w in self.tuning_windows if w["device_class"] == HELD_OUT_CLASS]
        self.assertGreater(len(agv_windows), 0)

        for agv_w in agv_windows[:5]:
            pred = self.manager.predict_window(agv_w)
            self.assertEqual(pred["verdict"], "uncertain")
            self.assertEqual(pred["abstain_reason"], "held_out_device_class")
            self.assertEqual(pred["device_class"], HELD_OUT_CLASS)
            self.assertIn("source", pred)


if __name__ == "__main__":
    unittest.main()
# CommShield AI Core
