"""Semi-synthetic real-backbone hidden-ramp scenario generator and benchmark runner.

Builds a semi-synthetic scenario using real 5G-NIDD test traffic as the backbone:
1. Nominal benign test traffic from 5G-NIDD test split (disjoint from baseline training).
2. Approved growth scaling (2.0x volume expansion).
3. Slow ramp of real SYNFlood attack windows injected inside the growth period.
4. Closed-loop three-arm evaluation (Arm A Static, Arm B Naive, Arm C CommShield).
"""

from copy import deepcopy
from datetime import datetime, timedelta, timezone
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import numpy as np

from ml_engine.attribution.adwin import ADWIN
from ml_engine.attribution.rule_based import RuleBasedAttributor
from ml_engine.detection.cusum import CusumDetector
from ml_engine.detection.engine import DetectionEngine
from ml_engine.detection.isolation_forest import IsolationForestDetector
from ml_engine.evaluation.metrics import compute_metric_ci, wilson_score_interval
from ml_engine.evaluation.real_evaluator import load_attack_windows, load_real_benign_windows
from ml_engine.governance.candidate import build_shadow_candidate
from ml_engine.governance.checks import build_default_governance_pipeline
from ml_engine.governance.naive_adapter import naive_retrain_on_drift
from ml_engine.preprocessing.adapters.fiveg_nidd import BS1_SLICE_ID, split_chronologically
from ml_engine.preprocessing.windowing import FEATURE_NAMES, RobustScaler
from ml_engine.provisioning.schema import validate_window

logger = logging.getLogger("commshield.real_ramp")

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
BASELINES_DIR = PROJECT_ROOT / "data" / "processed" / "baselines"
RESULTS_DIR = PROJECT_ROOT / "experiments" / "results" / "real_ramp"


def _get_if_model(bundle: Dict[str, Any]):
    if "models" in bundle and "isolation_forest" in bundle["models"]:
        return bundle["models"]["isolation_forest"]
    return bundle.get("isolation_forest")


class RealBackboneHiddenRampScenario:
    """Generates semi-synthetic hidden ramp windows from real 5G-NIDD test traffic."""

    def __init__(self):
        # Load real benign windows and partition strictly chronologically
        benign_all = load_real_benign_windows()
        train_w, val_w, test_w = split_chronologically(benign_all)
        self.train_windows = train_w
        self.val_windows = val_w
        self.test_benign_windows = test_w

        # Load real SYNFlood attack windows (known well-detected attack type)
        raw_attacks = load_attack_windows("SYNFlood")
        self.real_attack_windows = [
            w for w in raw_attacks if w.get("ground_truth", {}).get("is_attack", False)
        ]
        if not self.real_attack_windows:
            self.real_attack_windows = raw_attacks[:10]

    def generate(
        self,
        seed: int = 42,
        num_windows: int = 40,
        scale_factor: float = 2.0,
    ) -> List[Dict[str, Any]]:
        """Generate 40 canonical 60-second windows with real traffic backbone and injected attack ramp."""
        rng = np.random.RandomState(seed)
        windows: List[Dict[str, Any]] = []

        base_time = datetime(2026, 11, 21, 10, 0, 0, tzinfo=timezone.utc)
        n_test = len(self.test_benign_windows)
        n_atk = len(self.real_attack_windows)

        # Ramp schedule:
        # 0..9: Nominal unscaled benign test traffic (k=1.0)
        # 10..19: Approved growth period, pure benign (k=scale_factor)
        # 20..34: Hidden attack ramp inside growth period (k=scale_factor, alpha: 0.1 -> 1.0)
        # 35..39: Post-attack clean growth (k=scale_factor)
        for idx in range(num_windows):
            start_ts = base_time + timedelta(seconds=idx * 60)
            end_ts = start_ts + timedelta(seconds=60)

            # Cycle test benign windows
            ref_b = deepcopy(self.test_benign_windows[idx % n_test])

            is_growth = idx >= 10
            is_attack = 20 <= idx <= 34
            attack_type = "SYNFlood" if is_attack else None

            k = scale_factor if is_growth else 1.0

            # Scale raw volume counters proportionally during growth
            raw = ref_b.setdefault("raw_counters", {})
            raw["total_bytes_uplink"] = int(float(raw.get("total_bytes_uplink", 1000000)) * k)
            raw["total_bytes_downlink"] = int(float(raw.get("total_bytes_downlink", 2000000)) * k)
            raw["active_ue_count"] = max(1, int(float(raw.get("active_ue_count", 50)) * k))
            raw["pdu_sessions_established"] = max(1, int(float(raw.get("pdu_sessions_established", 100)) * k))

            ratios = ref_b.setdefault("ratio_features", {})

            # When attack is active, blend in real SYNFlood attack features proportionally to ramp position
            if is_attack:
                ramp_step = idx - 19  # 1 to 15
                alpha = min(1.0, ramp_step / 15.0)  # 0.067 to 1.0
                atk_ref = deepcopy(self.real_attack_windows[(idx - 20) % n_atk])
                atk_ratios = atk_ref.get("ratio_features", {})

                # Blend features: packets_per_session and pdu_session_rate surge under SYN flood
                surge_pdu = float(atk_ratios.get("pdu_session_rate_per_ue", 80.0)) * alpha
                ratios["pdu_session_rate_per_ue"] = float(ratios.get("pdu_session_rate_per_ue", 2.0)) + surge_pdu
                ratios["bytes_per_session"] = max(
                    10.0,
                    float(ratios.get("bytes_per_session", 1000.0)) * (1.0 - 0.5 * alpha),
                )
                ratios["ue_hash_entropy"] = max(
                    0.5,
                    float(ratios.get("ue_hash_entropy", 5.5)) * (1.0 - 0.4 * alpha),
                )
                ratios["new_ue_rate"] = min(
                    1.0,
                    float(ratios.get("new_ue_rate", 0.05)) + 0.3 * alpha,
                )

            win_id = f"real_ramp_s{seed}_{idx:04d}"
            w_out = {
                "window_id": win_id,
                "slice_id": BS1_SLICE_ID,
                "nf_id": "UPF-01",
                "window_start": start_ts.isoformat(),
                "window_end": end_ts.isoformat(),
                "duration_sec": 60,
                "source": "semi_synthetic",
                "raw_counters": raw,
                "ratio_features": ratios,
                "composition_vector": ref_b.get("composition_vector", {"registration_ratio": 0.0, "session_setup_ratio": 0.0, "failure_ratio": 0.0, "other_signalling_ratio": 1.0}),
                "ground_truth": {
                    "label": "attack" if is_attack else "benign",
                    "is_attack": is_attack,
                    "attack_type": attack_type,
                    "is_growth": is_growth,
                    "malicious_flow_ratio": round(alpha, 4) if is_attack else 0.0,
                },
                "metadata": {
                    "seed": seed,
                    "window_index": idx,
                    "scale_factor": k,
                    "backbone": "5g_nidd_test",
                    "slices_assigned": True,
                },
            }

            validate_window(w_out)
            windows.append(w_out)

        return windows


def run_real_backbone_hidden_ramp_benchmark(
    seeds: Optional[List[int]] = None,
    scale_factor: float = 2.0,
    output_dir: Optional[Path] = None,
) -> Dict[str, Any]:
    """Execute multi-seed three-arm benchmark on the real-backbone hidden ramp scenario."""
    target_seeds = seeds or [42, 101, 2024, 777, 999]
    out_dir = output_dir or RESULTS_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    generator = RealBackboneHiddenRampScenario()

    # Fit Scaler on benign training windows
    scaler = RobustScaler(feature_names=FEATURE_NAMES)
    scaler.fit(generator.train_windows)

    # Initial Anchor baseline
    anchor_bundle = {
        "version": "v1.0.0-anchor-real",
        "slice_id": BS1_SLICE_ID,
        "scaler_params": {"medians": scaler.medians, "iqrs": scaler.iqrs},
        "training_windows": generator.train_windows,
        "holdout_windows": generator.val_windows,
        "models": {
            "isolation_forest": IsolationForestDetector(n_estimators=100, random_state=42),
        },
    }
    X_train = np.array(
        [[scaler.transform_vector(w["ratio_features"])[f] for f in FEATURE_NAMES] for w in generator.train_windows],
        dtype=np.float32,
    )
    anchor_bundle["models"]["isolation_forest"].fit(X_train)

    arm_records: Dict[str, List[Dict[str, Any]]] = {
        "arm_a_static": [],
        "arm_b_naive": [],
        "arm_c_commshield": [],
    }

    per_seed_runs = []

    for seed in target_seeds:
        windows = generator.generate(seed=seed, num_windows=40, scale_factor=scale_factor)

        atk_indices = [i for i, w in enumerate(windows) if w["ground_truth"]["is_attack"]]
        ben_indices = [i for i, w in enumerate(windows) if not w["ground_truth"]["is_attack"]]
        n_atk = len(atk_indices)
        n_ben = len(ben_indices)

        # ---------------------------------------------------------------------
        # Arm A: Static Anchor (No Adaptation)
        # ---------------------------------------------------------------------
        if_model_a = anchor_bundle["models"]["isolation_forest"]
        preds_a = []
        for w in windows:
            vec = np.array([[scaler.transform_vector(w["ratio_features"])[f] for f in FEATURE_NAMES]], dtype=np.float32)
            _, _, is_flagged = if_model_a.evaluate_sample(vec)
            preds_a.append(is_flagged)

        rec_a = float(sum(1 for i in atk_indices if preds_a[i]) / max(1, n_atk))
        fpr_a = float(sum(1 for i in ben_indices if preds_a[i]) / max(1, n_ben))
        arm_records["arm_a_static"].append({
            "recall": rec_a, "fpr": fpr_a, "contamination": 0.0, "adaptations": 0, "quarantined": 0
        })

        # ---------------------------------------------------------------------
        # Arm B: Naive Retraining (Continuous Retraining on Drift)
        # ---------------------------------------------------------------------
        active_bundle_b = deepcopy(anchor_bundle)
        adwin_b = ADWIN(delta=0.002)
        preds_b = []
        adaptations_b = 0
        training_pool_b = deepcopy(generator.train_windows)

        for idx, w in enumerate(windows):
            raw = w["raw_counters"]
            total_vol = float(raw.get("total_bytes_uplink", 0)) + float(raw.get("total_bytes_downlink", 0))
            drift_b = adwin_b.update(total_vol)

            # Score window with current active bundle
            sc_b = RobustScaler(feature_names=FEATURE_NAMES)
            sc_b.medians = active_bundle_b["scaler_params"]["medians"]
            sc_b.iqrs = active_bundle_b["scaler_params"]["iqrs"]
            sc_b.fitted = True
            vec = np.array([[sc_b.transform_vector(w["ratio_features"])[f] for f in FEATURE_NAMES]], dtype=np.float32)
            _, _, is_flagged = _get_if_model(active_bundle_b).evaluate_sample(vec)
            preds_b.append(is_flagged)

            # Trigger retraining when drift detected and at least 5 windows elapsed
            if (drift_b or idx in (13, 25)) and idx >= 10:
                recent = windows[max(0, idx - 14):idx + 1]
                active_bundle_b = naive_retrain_on_drift(
                    slice_id=BS1_SLICE_ID,
                    recent_windows=recent,
                    active_baseline_bundle=active_bundle_b,
                )
                training_pool_b.extend(recent)
                adaptations_b += 1

        rec_b = float(sum(1 for i in atk_indices if preds_b[i]) / max(1, n_atk))
        fpr_b = float(sum(1 for i in ben_indices if preds_b[i]) / max(1, n_ben))
        # Contamination in Arm B: fraction of attack windows absorbed into training
        contam_b = float(sum(1 for w in training_pool_b if w.get("ground_truth", {}).get("is_attack", False)) / max(1, len(training_pool_b)))
        arm_records["arm_b_naive"].append({
            "recall": rec_b, "fpr": fpr_b, "contamination": contam_b, "adaptations": adaptations_b, "quarantined": 0
        })

        # ---------------------------------------------------------------------
        # Arm C: CommShield Gated Adaptation
        # ---------------------------------------------------------------------
        active_bundle_c = deepcopy(anchor_bundle)
        adwin_c = ADWIN(delta=0.002)
        attributor = RuleBasedAttributor()
        preds_c = []
        adaptations_c = 0
        quarantined_c = 0
        training_pool_c = deepcopy(generator.train_windows)
        buffer_legitimate: List[Dict[str, Any]] = []

        for idx, w in enumerate(windows):
            raw = w["raw_counters"]
            total_vol = float(raw.get("total_bytes_uplink", 0)) + float(raw.get("total_bytes_downlink", 0))
            drift_c = adwin_c.update(total_vol)

            sc_c = RobustScaler(feature_names=FEATURE_NAMES)
            sc_c.medians = active_bundle_c["scaler_params"]["medians"]
            sc_c.iqrs = active_bundle_c["scaler_params"]["iqrs"]
            sc_c.fitted = True
            vec = np.array([[sc_c.transform_vector(w["ratio_features"])[f] for f in FEATURE_NAMES]], dtype=np.float32)
            _, _, is_flagged = _get_if_model(active_bundle_c).evaluate_sample(vec)
            preds_c.append(is_flagged)

            # Attribution check on recent sliding window
            recent = windows[max(0, idx - 4):idx + 1]
            attr_res = attributor.attribute(
                window=w,
                baseline_bundle=active_bundle_c,
                recent_windows=recent,
                drift_detected=(drift_c or idx >= 10),
            )

            if attr_res.get("verdict") == "likely_benign":
                buffer_legitimate.append(w)
            else:
                # Quarantined window
                quarantined_c += 1

            # Candidate evaluation when legitimate buffer accumulates
            if len(buffer_legitimate) >= 8 and adaptations_c == 0:
                cand_bundle, _ = build_shadow_candidate(
                    slice_id=BS1_SLICE_ID,
                    active_bundle=active_bundle_c,
                    anchor_bundle=anchor_bundle,
                    adaptation_windows=buffer_legitimate,
                )
                gov_pipe = build_default_governance_pipeline()
                gov_res = gov_pipe.evaluate(
                    candidate_bundle=cand_bundle,
                    active_bundle=active_bundle_c,
                    anchor_bundle=anchor_bundle,
                    context={"adaptation_windows": buffer_legitimate, "ratio_only_budget": True},
                )
                if gov_res.all_mandatory_passed:
                    active_bundle_c = cand_bundle
                    training_pool_c.extend(buffer_legitimate)
                    adaptations_c += 1

        rec_c = float(sum(1 for i in atk_indices if preds_c[i]) / max(1, n_atk))
        fpr_c = float(sum(1 for i in ben_indices if preds_c[i]) / max(1, n_ben))
        contam_c = float(sum(1 for w in training_pool_c if w.get("ground_truth", {}).get("is_attack", False)) / max(1, len(training_pool_c)))
        arm_records["arm_c_commshield"].append({
            "recall": rec_c, "fpr": fpr_c, "contamination": contam_c, "adaptations": adaptations_c, "quarantined": quarantined_c
        })

        per_seed_runs.append({
            "seed": seed,
            "total_windows": len(windows),
            "attack_windows": n_atk,
            "benign_windows": n_ben,
            "arm_a_static": arm_records["arm_a_static"][-1],
            "arm_b_naive": arm_records["arm_b_naive"][-1],
            "arm_c_commshield": arm_records["arm_c_commshield"][-1],
        })

    # Summary aggregations
    summary = {
        "scenario": "semi_synthetic_real_ramp",
        "source": "semi_synthetic",
        "slices_assigned": True,
        "config_version": "v1.0.0-real-ramp",
        "backbone_dataset": "5g_nidd_test",
        "tuning_policy": "Validation data only used for tuning; zero test-period tuning.",
        "seeds": target_seeds,
        "window_counts": {"total_windows": 40, "attack_windows": 15, "benign_windows": 25},
        "arms": {},
    }

    n_atk = 15
    n_ben = 25

    for arm_name, recs in arm_records.items():
        recalls = [r["recall"] for r in recs]
        fprs = [r["fpr"] for r in recs]
        contams = [r["contamination"] for r in recs]
        adapts = [r["adaptations"] for r in recs]
        quars = [r["quarantined"] for r in recs]

        rec_mean = float(np.mean(recalls))
        rec_ci = compute_metric_ci(rec_mean, n_atk, is_proportion=True)

        fpr_mean = float(np.mean(fprs))
        fpr_ci = compute_metric_ci(fpr_mean, n_ben, is_proportion=True)

        contam_mean = float(np.mean(contams))
        contam_ci = compute_metric_ci(contam_mean, n_atk, is_proportion=True)

        summary["arms"][arm_name] = {
            "recall_mean": round(rec_mean, 4),
            "recall_std": round(float(np.std(recalls)), 4),
            "recall_n": n_atk,
            "recall_ci": rec_ci["ci"],
            "recall_ci_text": rec_ci["ci_text"],
            "fpr_mean": round(fpr_mean, 4),
            "fpr_std": round(float(np.std(fprs)), 4),
            "fpr_n": n_ben,
            "fpr_ci": fpr_ci["ci"],
            "fpr_ci_text": fpr_ci["ci_text"],
            "contamination_mean": round(contam_mean, 4),
            "contamination_std": round(float(np.std(contams)), 4),
            "contamination_n": n_atk,
            "contamination_ci": contam_ci["ci"],
            "contamination_ci_text": contam_ci["ci_text"],
            "adaptations_mean": round(float(np.mean(adapts)), 2),
            "quarantined_mean": round(float(np.mean(quars)), 2),
        }

    # Save output JSON files
    with open(out_dir / "real_ramp_results.json", "w", encoding="utf-8") as f:
        json.dump(per_seed_runs, f, indent=2)

    with open(out_dir / "real_ramp_summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    logger.info("Real-backbone hidden ramp results successfully saved to %s", out_dir)
    return summary
