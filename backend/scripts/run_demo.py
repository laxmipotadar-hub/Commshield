"""CommShield Reproducible End-to-End Pipeline Demo Runner.

Generates synthetic telemetry if missing, trains anchor baselines,
replays a chosen scenario end-to-end (ingestion, multi-model detection,
ADWIN drift attribution, quarantine isolation, and candidate governance),
and prints an auditable operational summary table.
"""

import argparse
from datetime import datetime, timezone
import json
import logging
from pathlib import Path
import sys

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.database import SessionLocal, engine, Base
from backend.app.models import (
    AnomalyAlert,
    Baseline,
    BaselineRegistry,
    CandidateBaseline,
    CanonicalWindow,
    DriftEvent,
    QuarantineWindow,
)
from backend.app.services.replay import replay_service
from backend.app.services.system import reset_runtime_database
from ml_engine.baseline.trainer import train_all_baselines
from ml_engine.preprocessing.synthetic_generator import generate_and_save_all_scenarios

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("commshield.demo")

DATA_DIR = PROJECT_ROOT / "data" / "synthetic"
BASELINES_DIR = PROJECT_ROOT / "data" / "processed" / "baselines"


def check_and_generate_synthetic_data():
    """Ensure all synthetic scenarios and training files exist."""
    required_files = [
        "stable_benign.json",
        "legitimate_growth.json",
        "slow_attack_ramp.json",
        "attack_in_growth.json",
        "mimicry_attack.json",
        "training_embb.json",
        "training_urllc.json",
        "training_mmtc.json",
    ]
    missing = [f for f in required_files if not (DATA_DIR / f).is_file()]
    if missing:
        print(f"[run_demo] Missing synthetic files: {missing}. Generating synthetic dataset...")
        generate_and_save_all_scenarios(output_dir=DATA_DIR)
        print("[run_demo] Synthetic dataset generation completed.")
    else:
        print("[run_demo] Synthetic scenario datasets verified.")


def check_and_train_baselines(db):
    """Ensure anchor baselines are calibrated and registered for all 3 network slices."""
    reg_count = db.query(BaselineRegistry).count()
    base_count = db.query(Baseline).filter(Baseline.is_anchor == True).count()
    if reg_count < 3 or base_count < 3:
        print("[run_demo] Calibrated slice baselines missing in database. Training baselines...")
        train_all_baselines(db=db)
        print("[run_demo] Baseline calibration and registration completed.")
    else:
        print("[run_demo] Calibrated slice baselines verified in registry.")


def run_pipeline_demo(scenario: str, data_source: str = "synthetic", reset_db: bool = False, max_windows: int = 60):
    """Execute end-to-end scenario replay and print formatted summary."""
    # Ensure tables exist
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        # 1. Reset database if requested
        if reset_db:
            print(f"[run_demo] Resetting runtime database tables (--reset-db passed)...")
            reset_runtime_database(db=db)

        # 2. Check and generate synthetic data if needed
        check_and_generate_synthetic_data()

        # 3. Check and train baselines if needed
        check_and_train_baselines(db)

        # 4. Load and step through scenario
        print(f"\n[run_demo] Starting end-to-end replay for scenario: '{scenario}' (source: {data_source})...")
        replay_service.start_sync(scenario, data_source=data_source)
        total_available = replay_service.total_windows
        step_count = min(max_windows, total_available)

        print(f"[run_demo] Replaying {step_count}/{total_available} windows through detection, attribution, and governance...")
        processed = replay_service.step_sync(count=step_count)
        print(f"[run_demo] Processed {processed} windows successfully.\n")

        # 5. Collect metrics from database
        stored_windows = db.query(CanonicalWindow).count()
        alerts_fired = db.query(AnomalyAlert).count()
        drift_events = db.query(DriftEvent).count()
        quarantined = db.query(QuarantineWindow).count()
        candidates = db.query(CandidateBaseline).all()
        active_baseline = db.query(Baseline).filter(Baseline.is_active == True).first()

        # Attribution verdicts breakdown
        drift_rows = db.query(DriftEvent).all()
        benign_count = sum(1 for d in drift_rows if (d.attribution or {}).get("verdict") == "likely_benign")
        attack_count = sum(1 for d in drift_rows if (d.attribution or {}).get("verdict") == "likely_attack")
        uncertain_count = sum(1 for d in drift_rows if (d.attribution or {}).get("verdict") == "uncertain")

        cand_status = "None"
        gates_passed = "N/A"
        if candidates:
            c = candidates[-1]
            cand_status = f"{c.candidate_version} ({c.status})"
            gates_passed = "YES" if (c.gate_metrics or {}).get("all_mandatory_passed") else "NO"

        # 6. Print Summary Table
        print("=" * 80)
        print("                 COMMSHIELD PIPELINE REPLAY SUMMARY")
        print("=" * 80)
        print(f"Scenario Identifier        : {scenario}")
        print(f"Telemetry Data Source      : {data_source}")
        if data_source == "fiveg_nidd" or "5g_nidd" in scenario.lower():
            print(f"Slice Assignment Status    : Assigned Topology (BS1 -> eMBB, BS2 -> URLLC; not real 3GPP slices)")
        print(f"Execution Timestamp        : {datetime.now(timezone.utc).isoformat()}")
        print("-" * 80)
        print(f"Windows Stored in DB       : {stored_windows}")
        print(f"Anomaly Alerts Fired       : {alerts_fired}")
        print(f"ADWIN Drift Events         : {drift_events}")
        print(f"  - Likely Benign Growth   : {benign_count}")
        print(f"  - Likely Attack          : {attack_count}")
        print(f"  - Uncertain (Abstained)  : {uncertain_count}")
        print(f"Quarantined Windows Pool   : {quarantined} (isolated from model training)")
        print(f"Shadow Candidate Baseline  : {cand_status}")
        print(f"Mandatory Gates Passed     : {gates_passed}")
        print(f"Active Serving Baseline    : {active_baseline.version if active_baseline else 'v1.0.0-anchor'}")
        print("=" * 80)
        print("[run_demo] Pipeline execution completed with full empirical reproducibility.\n")

    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(description="CommShield Reproducible End-to-End Pipeline Demo")
    parser.add_argument(
        "--scenario",
        type=str,
        default="legitimate_growth",
        choices=["stable_benign", "legitimate_growth", "slow_attack_ramp", "attack_in_growth", "mimicry_attack", "5g_nidd_portscan_growth", "fiveg_nidd"],
        help="Scenario to replay end-to-end",
    )
    parser.add_argument(
        "--data-source",
        type=str,
        default="synthetic",
        choices=["synthetic", "fiveg_nidd"],
        help="Telemetry data source: synthetic or fiveg_nidd",
    )
    parser.add_argument(
        "--reset-db",
        action="store_true",
        help="Reset runtime database tables before executing replay",
    )
    parser.add_argument(
        "--windows",
        type=int,
        default=60,
        help="Maximum windows to replay (default 60)",
    )
    args = parser.parse_args()

    # If scenario is 5g_nidd or fiveg_nidd, default data_source to fiveg_nidd
    data_src = args.data_source
    if args.scenario in ("5g_nidd_portscan_growth", "fiveg_nidd"):
        data_src = "fiveg_nidd"

    run_pipeline_demo(
        scenario=args.scenario,
        data_source=data_src,
        reset_db=args.reset_db,
        max_windows=args.windows,
    )


if __name__ == "__main__":
    main()
# CommShield AI Core
