"""Tests for the Learned Drift Attributor and Sequential Decision Engine.

Verifies:
1. No label leakage (labels, ground_truth, and raw identifiers never enter feature matrix).
2. Determinism (identical output across multiple runs with fixed random seed).
3. Held-out generator family integrity (real 5G-NIDD and test scenarios never accessed).
4. Feature ordering matches canonical schema.
5. Sequential evidence accumulation over horizon N prevents single-window decision flipping.
6. Graceful fallback to rule-based attributor.
7. Decision trace explicitly exposes active attributor and producing engine.
"""

from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
import unittest
import numpy as np

from backend.app.services.attribution import AttributionService
from ml_engine.attribution import (
    AbstainReason,
    AttributionVerdict,
    DEFAULT_LEARNED_ATTRIBUTION_CONFIG,
    LEARNED_ATTRIBUTION_FEATURES,
    LearnedAttributionConfig,
    LearnedAttributor,
    RuleBasedAttributor,
    SmallRegularizedAttributionModel,
    extract_attribution_features,
)
from ml_engine.attribution.trainer import TUNING_SEED, generate_tuning_dataset

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


class TestLearnedAttribution(unittest.TestCase):
    """Test suite for learned attribution model and pipeline integration."""

    def setUp(self):
        from backend.app.database import Base, SessionLocal, engine
        from backend.app.models import CanonicalWindow
        Base.metadata.create_all(bind=engine)

        # Pre-insert CanonicalWindow for test window to satisfy foreign key constraints
        db = SessionLocal()
        try:
            existing = db.query(CanonicalWindow).filter(CanonicalWindow.id == "win-test-001").first()
            if not existing:
                win = CanonicalWindow(
                    id="win-test-001",
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

        self.baseline_bundle = {
            "slice_id": "sst-1-sd-010203",
            "nf_id": "UPF-01",
            "version": "v1.0.0-anchor",
            "mean_volume_bytes": 1_000_000_000.0,
            "composition_vector": {
                "registration_ratio": 0.08,
                "session_setup_ratio": 0.90,
                "failure_ratio": 0.005,
                "other_signalling_ratio": 0.015,
            },
            "scaler_params": {
                "medians": {
                    "pdu_session_rate_per_ue": 55.63,
                    "ue_hash_entropy": 7.4,
                    "nas_failure_ratio": 0.004,
                    "pfcp_failure_ratio": 0.0,
                }
            },
        }

        # Nominal test window with potential ground-truth labels present in dictionary
        self.sample_window = {
            "window_id": "win-test-001",
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
            # Explicit ground-truth / labels that must NOT leak
            "ground_truth": {
                "is_attack": True,
                "attack_type": "SYNFlood",
                "is_growth": False,
            },
            "label": "malicious",
            "is_attack": True,
            "attack_type": "SYNFlood",
            "src_ip": "192.168.1.100",
            "imsi": "001010123456789",
        }

    def test_no_label_leakage(self):
        """Verify ground-truth fields and raw identifiers never enter feature matrix."""
        vec, feat_dict = extract_attribution_features(
            window=self.sample_window,
            baseline_bundle=self.baseline_bundle,
        )

        forbidden_keys = {
            "is_attack",
            "attack_type",
            "is_growth",
            "label",
            "ground_truth",
            "src_ip",
            "imsi",
            "user_id",
        }

        # Check feature dict keys
        extracted_keys = set(feat_dict.keys())
        leakage_keys = extracted_keys.intersection(forbidden_keys)
        self.assertEqual(len(leakage_keys), 0, f"Label leakage detected in feature dictionary: {leakage_keys}")

        # Check exact schema equality
        self.assertEqual(list(feat_dict.keys()), LEARNED_ATTRIBUTION_FEATURES)
        self.assertEqual(len(vec), len(LEARNED_ATTRIBUTION_FEATURES))

    def test_feature_order_schema_matches(self):
        """Verify extracted vector matches LEARNED_ATTRIBUTION_FEATURES in exact order."""
        vec, feat_dict = extract_attribution_features(
            window=self.sample_window,
            baseline_bundle=self.baseline_bundle,
        )

        for idx, feature_name in enumerate(LEARNED_ATTRIBUTION_FEATURES):
            expected_val = feat_dict[feature_name]
            actual_val = vec[idx]
            self.assertAlmostEqual(actual_val, expected_val, places=4, msg=f"Feature order mismatch at index {idx} ({feature_name})")

    def test_determinism(self):
        """Verify model predictions and verdicts are bitwise deterministic across repeated calls."""
        model = SmallRegularizedAttributionModel(random_seed=42)
        X_dummy = np.random.RandomState(42).randn(20, 9)
        y_dummy = np.random.RandomState(42).randint(0, 2, size=20)
        model.fit(X_dummy, y_dummy)

        test_sample = np.array([1.5, 0.02, 0.1, 0.03, 0.005, 0.0, 1.0, 1.0, 0.05], dtype=np.float32)

        prob_1 = model.predict_proba(test_sample)[0]
        prob_2 = model.predict_proba(test_sample)[0]
        self.assertEqual(prob_1, prob_2, "Model predict_proba is not deterministic.")

        attributor = LearnedAttributor(model=model)
        res_1 = attributor.attribute(self.sample_window, self.baseline_bundle, drift_detected=True)
        res_2 = attributor.attribute(self.sample_window, self.baseline_bundle, drift_detected=True)
        self.assertEqual(res_1["verdict"], res_2["verdict"], "Attributor verdict is not deterministic.")
        self.assertEqual(res_1["action"], res_2["action"], "Attributor action is not deterministic.")

    def test_held_out_family_never_seen_in_training(self):
        """Verify training data strictly uses synthetic tuning streams with isolated seed."""
        # Test seeds defined in experiment benchmark
        test_seeds = {42, 101, 2024, 777, 999}
        self.assertNotIn(TUNING_SEED, test_seeds, "Tuning seed must be strictly isolated from test seeds.")

        X, y, meta = generate_tuning_dataset(seed=TUNING_SEED, num_windows_per_scenario=5)
        scenarios_trained = {m["scenario"] for m in meta}

        # Verify real 5G-NIDD scenarios never present in training metadata
        forbidden_scenarios = {"5g_nidd", "UDPFlood", "HTTPFlood", "SYNFlood", "real_benign", "real_attacks"}
        for sc in scenarios_trained:
            self.assertNotIn(sc, forbidden_scenarios, f"Forbidden real scenario '{sc}' found in training data.")

    def test_sequential_decision_accumulation(self):
        """Verify sequential evidence horizon N dampens noise and prevents premature verdicts."""
        cfg = LearnedAttributionConfig(sequential_window_length=3)
        attributor = LearnedAttributor(config=cfg)
        attributor.reset_history("sst-1-sd-010203")

        # Clean growth window
        growth_win = deepcopy(self.sample_window)
        growth_win["raw_counters"]["total_bytes_uplink"] = 500_000_000
        growth_win["raw_counters"]["total_bytes_downlink"] = 2_000_000_000  # 2.5x volume
        growth_win["ratio_features"]["nas_failure_ratio"] = 0.002
        growth_win["ground_truth"]["is_attack"] = False
        growth_win["ground_truth"]["is_growth"] = True

        # Window 1: History length = 1 < 3 -> Must abstain on INSUFFICIENT_WINDOWS
        r1 = attributor.attribute(growth_win, self.baseline_bundle, drift_detected=True)
        self.assertEqual(r1["verdict"], AttributionVerdict.UNCERTAIN.value)
        self.assertEqual(r1["abstain_reason"], AbstainReason.INSUFFICIENT_WINDOWS.value)

        # Window 2: History length = 2 < 3 -> Still INSUFFICIENT_WINDOWS
        r2 = attributor.attribute(growth_win, self.baseline_bundle, drift_detected=True)
        self.assertEqual(r2["verdict"], AttributionVerdict.UNCERTAIN.value)
        self.assertEqual(r2["abstain_reason"], AbstainReason.INSUFFICIENT_WINDOWS.value)

        # Window 3: History length = 3 == N -> Now issues confident verdict
        r3 = attributor.attribute(growth_win, self.baseline_bundle, drift_detected=True)
        self.assertIn(r3["verdict"], [AttributionVerdict.LIKELY_BENIGN.value, AttributionVerdict.UNCERTAIN.value])

        # No single burst flipping: If a single attack window occurs in an established clean stream,
        # moving average over 3 windows prevents instant flipping to likely_attack
        burst_atk = deepcopy(self.sample_window)
        burst_atk["ratio_features"]["nas_failure_ratio"] = 0.15
        burst_atk["ratio_features"]["ue_hash_entropy"] = 2.0
        r_burst = attributor.attribute(burst_atk, self.baseline_bundle, drift_detected=True)
        # Should NOT flip to likely_attack on single burst (either likely_benign or uncertain on indicator conflict)
        self.assertNotEqual(r_burst["verdict"], AttributionVerdict.LIKELY_ATTACK.value, "Single noisy window flipped sequential verdict.")

    def test_fallback_to_rules(self):
        """Verify graceful fallback to rule-based attributor if learned model encounters an error."""
        # Unfitted model that will raise RuntimeError inside predict_proba
        broken_model = SmallRegularizedAttributionModel()
        attributor = LearnedAttributor(model=broken_model, fallback_attributor=RuleBasedAttributor())

        res = attributor.attribute(self.sample_window, self.baseline_bundle, drift_detected=True)

        self.assertIn("verdict", res)
        self.assertTrue(res["supporting_signals"].get("fallback_used", False))
        self.assertEqual(res["supporting_signals"].get("attributor_type"), "learned_fallback_rules")

    def test_backend_decision_trace_exposes_attributor(self):
        """Verify AttributionService exposes attributor_configured and produced_by in decision trace."""
        service = AttributionService(attributor_flag="rules")
        res_rules = service.analyze_window(self.sample_window, force_drift=True)
        self.assertEqual(res_rules.supporting_signals.get("attributor_configured"), "rules")
        self.assertEqual(res_rules.supporting_signals.get("produced_by"), "rules")

        service.set_attributor("learned")
        res_learned = service.analyze_window(self.sample_window, force_drift=True)
        self.assertEqual(res_learned.supporting_signals.get("attributor_configured"), "learned")
        self.assertEqual(res_learned.supporting_signals.get("produced_by"), "learned")


if __name__ == "__main__":
    unittest.main()
# CommShield AI Core
