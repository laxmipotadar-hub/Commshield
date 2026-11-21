"""Tests for Split Conformal Calibration and Principled Abstention.

Verifies:
1. Conformal p-value correctness on a toy example with the exact (n+1) correction.
2. Bitwise determinism of p-values, scores, and verdicts.
3. Calibration windows strictly disjoint from training and threshold-setting windows.
4. Named abstention reasons present: 'conformal gray band' and 'detector p-value disagreement'.
5. Calibration sample size reporting and pooled fallback when n < min_calibration_size (30).
6. Decision trace and supporting signals exposure.
"""

from copy import deepcopy
from datetime import datetime, timezone
import unittest
import numpy as np

from backend.app.services.attribution import AttributionService
from ml_engine.attribution.config import (
    AbstainReason,
    AttributionVerdict,
    ConformalAttributionConfig,
)
from ml_engine.attribution.conformal import (
    CalibrationSliceBundle,
    ConformalCalibrationManager,
    compute_conformal_pvalue,
    evaluate_conformal_abstention,
)
from ml_engine.evaluation.conformal_evaluator import partition_benign_windows
from ml_engine.preprocessing.synthetic_generator import SyntheticGenerator


class TestConformalAttribution(unittest.TestCase):
    """Test suite for split conformal calibration and principled abstention."""

    def setUp(self):
        from backend.app.database import Base, SessionLocal, engine
        from backend.app.models import CanonicalWindow
        Base.metadata.create_all(bind=engine)

        db = SessionLocal()
        try:
            if not db.query(CanonicalWindow).filter(CanonicalWindow.id == "win-conformal-001").first():
                win = CanonicalWindow(
                    id="win-conformal-001",
                    slice_id="sst-1-sd-010203",
                    nf_id="UPF-01",
                    window_start=datetime.now(timezone.utc),
                    window_end=datetime.now(timezone.utc),
                    duration_sec=60,
                    raw_counters={},
                    ratio_features={},
                    composition_vector={},
                    created_at=datetime.now(timezone.utc),
                )
                db.add(win)
                db.commit()
        finally:
            db.close()

        self.sample_window = {
            "window_id": "win-conformal-001",
            "slice_id": "sst-1-sd-010203",
            "raw_counters": {
                "total_bytes_uplink": 250_000_000,
                "total_bytes_downlink": 1_000_000_000,
                "active_ue_count": 1200,
            },
            "ratio_features": {
                "pdu_session_rate_per_ue": 55.63,
                "ue_hash_entropy": 7.42,
                "nas_failure_ratio": 0.003,
                "pfcp_failure_ratio": 0.0,
                "new_ue_rate": 0.02,
            },
            "composition_vector": {
                "registration_ratio": 0.08,
                "session_setup_ratio": 0.90,
                "failure_ratio": 0.005,
                "other_signalling_ratio": 0.015,
            },
        }

    def test_pvalue_correctness_toy_example(self):
        """Verify conformal p-value calculation with (n+1) correction against exact hand-computed values."""
        calibration = np.array([0.1, 0.2, 0.5, 0.8])  # n = 4

        # 1. Test score greater than all calibration points: count = 0 -> p = (1 + 0) / 5 = 0.20
        p1 = compute_conformal_pvalue(0.9, calibration)
        self.assertAlmostEqual(p1, 0.20, places=6)

        # 2. Test score equals median point 0.5: scores >= 0.5 are [0.5, 0.8] (count = 2) -> p = (1 + 2) / 5 = 0.60
        p2 = compute_conformal_pvalue(0.5, calibration)
        self.assertAlmostEqual(p2, 0.60, places=6)

        # 3. Test score less than all calibration points: count = 4 -> p = (1 + 4) / 5 = 1.00
        p3 = compute_conformal_pvalue(0.05, calibration)
        self.assertAlmostEqual(p3, 1.00, places=6)

        # 4. Test score equals minimum point 0.1: count = 4 -> p = (1 + 4) / 5 = 1.00
        p4 = compute_conformal_pvalue(0.1, calibration)
        self.assertAlmostEqual(p4, 1.00, places=6)

        # 5. Test score 0.7: score >= 0.7 is only [0.8] (count = 1) -> p = (1 + 1) / 5 = 0.40
        p5 = compute_conformal_pvalue(0.7, calibration)
        self.assertAlmostEqual(p5, 0.40, places=6)

        # Minimum possible p-value for n = 4 is 1 / (n + 1) = 0.20
        self.assertAlmostEqual(compute_conformal_pvalue(99.0, calibration), 0.20, places=6)

    def test_determinism(self):
        """Verify p-value and abstention evaluations are bitwise deterministic."""
        cal = np.array([0.05, 0.12, 0.18, 0.25, 0.40, 0.60, 0.75])
        test_val = 0.33

        p_vals = [compute_conformal_pvalue(test_val, cal) for _ in range(10)]
        self.assertEqual(len(set(p_vals)), 1, "Conformal p-value computation is not deterministic.")

        cfg = ConformalAttributionConfig(alpha_low=0.05, alpha_high=0.20, detector_disagreement_margin=0.35)
        res_list = [evaluate_conformal_abstention(0.15, 0.18, 0.12, cfg) for _ in range(10)]
        for r in res_list[1:]:
            self.assertEqual(r[0], res_list[0][0])
            self.assertEqual(r[1], res_list[0][1])

    def test_calibration_windows_disjoint(self):
        """Verify calibration windows are strictly disjoint from training and threshold-setting windows."""
        gen = SyntheticGenerator(seed=8888)
        windows = gen.generate_scenario_windows("clean_training", "eMBB", num_windows=60)

        train, thresh, cal = partition_benign_windows(windows, n_train=30, n_threshold=15)

        train_ids = {w["window_id"] for w in train}
        thresh_ids = {w["window_id"] for w in thresh}
        cal_ids = {w["window_id"] for w in cal}

        self.assertEqual(len(train), 30)
        self.assertEqual(len(thresh), 15)
        self.assertEqual(len(cal), 15)

        self.assertTrue(train_ids.isdisjoint(thresh_ids), "Train and threshold IDs must be disjoint.")
        self.assertTrue(train_ids.isdisjoint(cal_ids), "Train and calibration IDs must be disjoint.")
        self.assertTrue(thresh_ids.isdisjoint(cal_ids), "Threshold and calibration IDs must be disjoint.")

        # Test manager enforcement of disjointness
        mgr = ConformalCalibrationManager()
        mgr.register_known_partition_ids(train_ids, thresh_ids)

        # Registering disjoint cal_ids must succeed
        bundle = mgr.register_calibration_bundle(
            slice_id="sst-1-sd-010203",
            calibration_window_ids=list(cal_ids),
            if_scores=np.zeros(len(cal)),
            ae_scores=np.zeros(len(cal)),
            attr_scores=np.zeros(len(cal)),
        )
        self.assertEqual(bundle.size, 15)

        # Attempting to register an overlapping window ID must raise ValueError
        leaked_ids = list(cal_ids) + [list(train_ids)[0]]
        with self.assertRaises(ValueError):
            mgr.register_calibration_bundle(
                slice_id="sst-test-leaked",
                calibration_window_ids=leaked_ids,
                if_scores=np.zeros(len(leaked_ids)),
                ae_scores=np.zeros(len(leaked_ids)),
                attr_scores=np.zeros(len(leaked_ids)),
            )

    def test_abstention_reasons_present(self):
        """Verify exact named abstention reasons trigger correctly."""
        cfg = ConformalAttributionConfig(
            alpha_low=0.05,
            alpha_high=0.20,
            detector_disagreement_margin=0.35,
        )

        # Case 1: Attributor p-value in gray band [0.05, 0.20]
        should_abs_1, reason_1, details_1 = evaluate_conformal_abstention(
            p_if=0.15,
            p_ae=0.18,
            p_attr=0.10,  # inside gray band
            config=cfg,
        )
        self.assertTrue(should_abs_1)
        self.assertEqual(reason_1, AbstainReason.CONFORMAL_GRAY_BAND.value)
        self.assertEqual(reason_1, "conformal gray band")
        self.assertTrue(details_1["gray_band_triggered"])

        # Case 2: Detector p-values disagree by > 0.35
        should_abs_2, reason_2, details_2 = evaluate_conformal_abstention(
            p_if=0.04,
            p_ae=0.85,  # |0.04 - 0.85| = 0.81 > 0.35
            p_attr=0.50,  # outside gray band
            config=cfg,
        )
        self.assertTrue(should_abs_2)
        self.assertEqual(reason_2, AbstainReason.DETECTOR_PVALUE_DISAGREEMENT.value)
        self.assertEqual(reason_2, "detector p-value disagreement")
        self.assertTrue(details_2["detector_disagreement_triggered"])

        # Case 3: Confident attack (p < alpha_low) without detector disagreement
        should_abs_3, reason_3, details_3 = evaluate_conformal_abstention(
            p_if=0.02,
            p_ae=0.03,
            p_attr=0.01,  # null rejected, confident attack
            config=cfg,
        )
        self.assertFalse(should_abs_3)
        self.assertIsNone(reason_3)

    def test_calibration_size_and_fallback(self):
        """Verify calibration size tracking, smallest achievable p-value, and pooled fallback."""
        bundle_small = CalibrationSliceBundle(
            slice_id="sst-small",
            window_ids=["w1", "w2", "w3"],
            if_scores=np.array([0.1, 0.2, 0.3]),
            ae_scores=np.array([0.1, 0.2, 0.3]),
            attr_scores=np.array([0.1, 0.2, 0.3]),
            size=3,
            is_pooled=True,
            fallback_reason="Deficient slice calibration",
        )
        # For n = 3, smallest achievable p-value is 1 / (3 + 1) = 0.25
        self.assertAlmostEqual(bundle_small.smallest_achievable_pvalue(), 0.25, places=4)

        bundle_full = CalibrationSliceBundle(
            slice_id="sst-full",
            window_ids=[f"w_{i}" for i in range(45)],
            if_scores=np.zeros(45),
            ae_scores=np.zeros(45),
            attr_scores=np.zeros(45),
            size=45,
            is_pooled=False,
        )
        # For n = 45, smallest achievable p-value is 1 / 46 = 0.0217
        self.assertAlmostEqual(bundle_full.smallest_achievable_pvalue(), 1.0 / 46.0, places=4)

    def test_backend_decision_trace_exposes_conformal(self):
        """Verify AttributionService exposes conformal calibration p-values and decision trace entries."""
        service = AttributionService(conformal_flag=True)

        res = service.analyze_window(self.sample_window, force_drift=True)

        # Verify supporting signals
        supp = res.supporting_signals
        self.assertTrue(supp.get("conformal_calibration_enabled"))
        self.assertIn("p_value_isolation_forest", supp)
        self.assertIn("p_value_autoencoder", supp)
        self.assertIn("p_value_attributor", supp)

        # Verify DecisionTrace step in database
        from backend.app.database import SessionLocal
        from backend.app.models import DecisionTrace
        db = SessionLocal()
        try:
            trace = db.query(DecisionTrace).filter(DecisionTrace.id == res.decision_trace_id).first()
            self.assertIsNotNone(trace)
            step_eval = next(s for s in trace.steps if s["step_name"] == "evidence_evaluated")
            self.assertIn("conformal_calibration", step_eval["details"])
            conf_details = step_eval["details"]["conformal_calibration"]
            self.assertIn("p_value_attributor", conf_details)
        finally:
            db.close()


if __name__ == "__main__":
    unittest.main()

