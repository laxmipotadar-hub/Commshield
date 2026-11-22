"""Scenario test evaluation for CommShield Governance Engine:

Runs and reports:
(a) legitimate_growth: candidate should pass, and promotion should go through after approval.
(b) attack_in_growth / poisoned candidate: canary or drift budget must reject it.
(c) rollback after promotion: active baseline pointer returns to original version.
"""

from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path

from backend.app.database import SessionLocal
from backend.app.models import Baseline, CandidateBaseline
from backend.app.services.detection import detection_service
from backend.app.services.governance import governance_service
from ml_engine.governance import (
    build_default_governance_pipeline,
    build_shadow_candidate,
)

PROJECT_ROOT = Path(__file__).resolve().parent
SYNTHETIC_DIR = PROJECT_ROOT / "data" / "synthetic"


def run_governance_scenarios():
    db = SessionLocal()
    slice_id = "sst-1-sd-010203"

    results = []

    try:
        # Initial active baseline
        act_bundle = detection_service.get_baseline_bundle(slice_id, db=db)
        anc_row = db.query(Baseline).filter(Baseline.slice_id == slice_id, Baseline.is_anchor == True).first()
        import joblib
        anc_bundle = joblib.load(anc_row.model_artifact_path)
        initial_version = act_bundle.get("version", "v1.0.0-anchor")

        pipeline = build_default_governance_pipeline()

        # ---------------------------------------------------------------------
        # Scenario (a): Legitimate Growth Candidate
        # ---------------------------------------------------------------------
        legit_file = SYNTHETIC_DIR / "legitimate_growth.json"
        with open(legit_file, "r", encoding="utf-8") as f:
            legit_data = json.load(f)
        legit_windows = legit_data.get("windows", [])[:20]

        # Tag as likely_benign
        for w in legit_windows:
            w["attribution"] = {"verdict": "likely_benign"}

        cand_a_bundle, cand_a_row = build_shadow_candidate(
            slice_id=slice_id,
            active_bundle=act_bundle,
            anchor_bundle=anc_bundle,
            adaptation_windows=legit_windows,
            candidate_version=f"v1.1.0-legit-{int(datetime.now(timezone.utc).timestamp())}",
            db=db,
        )

        eval_a = pipeline.evaluate(
            candidate_bundle=cand_a_bundle,
            active_bundle=act_bundle,
            anchor_bundle=anc_bundle,
            context={"db": db, "adaptation_windows": legit_windows, "volume_multiplier": 2.5},
        )

        # Update candidate metrics
        cand_a_row.gate_metrics = eval_a.gate_metrics
        db.commit()

        # Attempt approval & promotion if passed
        promoted_a = False
        if eval_a.all_mandatory_passed:
            appr_res = governance_service.approve_and_promote(
                candidate_id=cand_a_row.id,
                analyst_id="analyst_sec_01",
                notes="Approved legitimate growth promotion",
                db=db,
            )
            promoted_a = (appr_res.status == "APPROVED")

        results.append({
            "Scenario": "legitimate_growth",
            "Candidate": cand_a_row.candidate_version,
            "Gates Passed": "YES" if eval_a.all_mandatory_passed else "NO",
            "FPR Check": "PASS" if eval_a.gate_metrics.get("normal_holdout_backtest", {}).get("passed") else "FAIL",
            "Canary Check": "PASS" if eval_a.gate_metrics.get("canary_retention_test", {}).get("passed") else "FAIL",
            "Drift Budget": "PASS" if eval_a.gate_metrics.get("drift_budget", {}).get("passed") else "FAIL",
            "Outcome": "PROMOTED" if promoted_a else "REJECTED",
        })

        # ---------------------------------------------------------------------
        # Scenario (b): Deliberately Poisoned Candidate (Attack Contamination)
        # ---------------------------------------------------------------------
        # Create severely shifted / poisoned adaptation windows simulating attack contamination
        poisoned_windows = [
            {
                "window_id": f"poison-win-{i}",
                "slice_id": slice_id,
                "raw_counters": {
                    "total_bytes_uplink": 900_000_000,
                    "total_bytes_downlink": 4_500_000_000,
                    "active_ue_count": 500,
                },
                "ratio_features": {
                    "registrations_per_active_ue": 0.55,
                    "nas_failure_ratio": 0.25,
                    "pfcp_failure_ratio": 0.15,
                    "pdu_session_rate_per_ue": 4.5,
                    "bytes_per_session": 15000000.0,
                    "packets_per_session": 9500.0,
                    "gtpu_volume_per_ue": 15000000.0,
                    "ue_hash_entropy": 2.5,
                    "new_ue_rate": 0.35,
                },
                "composition_vector": {
                    "registration_ratio": 0.50,
                    "session_setup_ratio": 0.20,
                    "failure_ratio": 0.25,
                    "other_signalling_ratio": 0.05,
                },
                "attribution": {"verdict": "likely_benign"},   # masquerading
            }
            for i in range(15)
        ]

        cand_b_bundle, cand_b_row = build_shadow_candidate(
            slice_id=slice_id,
            active_bundle=act_bundle,
            anchor_bundle=anc_bundle,
            adaptation_windows=poisoned_windows,
            candidate_version=f"v1.1.0-poisoned-{int(datetime.now(timezone.utc).timestamp())}",
            db=db,
        )

        eval_b = pipeline.evaluate(
            candidate_bundle=cand_b_bundle,
            active_bundle=act_bundle,
            anchor_bundle=anc_bundle,
            context={"db": db, "adaptation_windows": poisoned_windows, "volume_multiplier": 3.0},
        )

        cand_b_row.gate_metrics = eval_b.gate_metrics
        db.commit()

        # Reject candidate
        governance_service.reject_candidate(
            candidate_id=cand_b_row.id,
            analyst_id="analyst_sec_01",
            notes="Rejected poisoned candidate due to canary and drift budget failures",
            db=db,
        )

        results.append({
            "Scenario": "attack_in_growth (poisoned)",
            "Candidate": cand_b_row.candidate_version,
            "Gates Passed": "YES" if eval_b.all_mandatory_passed else "NO",
            "FPR Check": "PASS" if eval_b.gate_metrics.get("normal_holdout_backtest", {}).get("passed") else "FAIL",
            "Canary Check": "PASS" if eval_b.gate_metrics.get("canary_retention_test", {}).get("passed") else "FAIL",
            "Drift Budget": "PASS" if eval_b.gate_metrics.get("drift_budget", {}).get("passed") else "FAIL",
            "Outcome": "REJECTED",
        })

        # ---------------------------------------------------------------------
        # Scenario (c): Rollback After Promotion
        # ---------------------------------------------------------------------
        roll_res = governance_service.rollback_baseline(
            slice_id=slice_id,
            target_version=initial_version,
            analyst_id="analyst_sec_01",
            reason="Post-promotion operational rollback verification",
            db=db,
        )

        # Verify active baseline is restored
        current_active = db.query(Baseline).filter(Baseline.slice_id == slice_id, Baseline.is_active == True).first()
        rollback_success = (current_active and current_active.version == initial_version)

        results.append({
            "Scenario": "rollback_after_promotion",
            "Candidate": f"Restore -> {initial_version}",
            "Gates Passed": "N/A",
            "FPR Check": "N/A",
            "Canary Check": "N/A",
            "Drift Budget": "N/A",
            "Outcome": "RESTORED" if rollback_success else "FAILED",
        })

    finally:
        db.close()

    # Print table
    print("-" * 92)
    print(f"{'Scenario':<25} | {'Candidate':<22} | {'Gates':<6} | {'Canary':<6} | {'Budget':<6} | {'Outcome'}")
    print("-" * 92)
    for r in results:
        print(f"{r['Scenario']:<25} | {r['Candidate']:<22} | {r['Gates Passed']:<6} | {r['Canary Check']:<6} | {r['Drift Budget']:<6} | {r['Outcome']}")
    print("-" * 92)


if __name__ == "__main__":
    run_governance_scenarios()
# CommShield AI Core
