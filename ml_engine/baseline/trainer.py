"""Per-slice baseline trainer for CommShield.

Fits RobustScaler and IsolationForest exclusively on clean benign training data.
Serializes artifacts with joblib into data/processed/baselines/ and registers
each baseline in the baseline_registry and baselines tables as the trusted anchor
and active baseline.
"""

from datetime import datetime, timezone
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
import uuid

import joblib
import numpy as np
from sqlalchemy.orm import Session

from backend.app.database import SessionLocal, engine, Base
from backend.app.models import Baseline, BaselineRegistry
from ml_engine.detection.isolation_forest import IsolationForestDetector
from ml_engine.preprocessing.windowing import FEATURE_NAMES, RobustScaler

logger = logging.getLogger("commshield.baseline")

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
SYNTHETIC_DATA_DIR = PROJECT_ROOT / "data" / "synthetic"
PROCESSED_BASELINES_DIR = PROJECT_ROOT / "data" / "processed" / "baselines"


SLICE_TRAINING_CONFIGS = [
    {
        "slice_name": "eMBB",
        "slice_id": "sst-1-sd-010203",
        "nf_id": "UPF-01",
        "training_file": SYNTHETIC_DATA_DIR / "training_embb.json",
        "version": "v1.0.0-anchor",
    },
    {
        "slice_name": "URLLC",
        "slice_id": "sst-2-sd-010203",
        "nf_id": "UPF-01",
        "training_file": SYNTHETIC_DATA_DIR / "training_urllc.json",
        "version": "v1.0.0-anchor",
    },
    {
        "slice_name": "mMTC",
        "slice_id": "sst-3-sd-010203",
        "nf_id": "UPF-01",
        "training_file": SYNTHETIC_DATA_DIR / "training_mmtc.json",
        "version": "v1.0.0-anchor",
    },
]


def train_slice_baseline(
    slice_id: str,
    training_windows: List[Dict[str, Any]],
    nf_id: str = "UPF-01",
    version: str = "v1.0.0-anchor",
    output_dir: Optional[Path] = None,
    db: Optional[Session] = None,
    threshold_percentile: float = 95.0,
    contamination: float = 0.05,
    random_state: int = 42,
) -> Dict[str, Any]:
    """Train and persist a baseline for a single slice on its training windows."""
    if not training_windows:
        raise ValueError(f"No training windows provided for slice {slice_id}")

    target_dir = output_dir or PROCESSED_BASELINES_DIR
    target_dir.mkdir(parents=True, exist_ok=True)

    # 1. Fit RobustScaler exclusively on training windows
    scaler = RobustScaler(feature_names=FEATURE_NAMES)
    scaler.fit(training_windows)

    # 2. Extract and transform feature matrix
    X_list: List[List[float]] = []
    start_times: List[datetime] = []
    end_times: List[datetime] = []

    for w in training_windows:
        ratios = w.get("ratio_features", {})
        scaled = scaler.transform_vector(ratios)
        row = [scaled[f] for f in FEATURE_NAMES]
        X_list.append(row)

        w_start = w.get("window_start")
        w_end = w.get("window_end")
        if isinstance(w_start, str):
            start_times.append(datetime.fromisoformat(w_start.replace("Z", "+00:00")))
        elif isinstance(w_start, datetime):
            start_times.append(w_start)

        if isinstance(w_end, str):
            end_times.append(datetime.fromisoformat(w_end.replace("Z", "+00:00")))
        elif isinstance(w_end, datetime):
            end_times.append(w_end)

    X = np.array(X_list, dtype=np.float32)

    # 3. Fit Isolation Forest detector
    detector = IsolationForestDetector(
        n_estimators=100,
        contamination=contamination,
        random_state=random_state,
        threshold_percentile=threshold_percentile,
    )
    detector.fit(X)

    # 4. Serialize model and scaler artifacts with joblib
    artifact_filename = f"{slice_id}_{version}.joblib"
    artifact_path = target_dir / artifact_filename

    bundle = {
        "slice_id": slice_id,
        "nf_id": nf_id,
        "version": version,
        "detector": detector,
        "scaler": scaler,
        "scaler_params": scaler.to_dict(),
        "threshold_params": {
            "threshold_percentile": threshold_percentile,
            "cusum_threshold": 4.5,
        },
        "feature_schema": {"features": FEATURE_NAMES},
        "training_window_count": len(training_windows),
        "training_window_start": min(start_times) if start_times else datetime.now(timezone.utc),
        "training_window_end": max(end_times) if end_times else datetime.now(timezone.utc),
        "created_at": datetime.now(timezone.utc),
    }

    joblib.dump(bundle, artifact_path)
    logger.info("Saved baseline artifact to %s", artifact_path)

    # 5. Register in baseline_registry and baselines tables
    owns_db = False
    if db is None:
        db = SessionLocal()
        owns_db = True

    try:
        shared_id = str(uuid.uuid4())
        # Check existing in baseline_registry
        existing_reg = (
            db.query(BaselineRegistry)
            .filter(BaselineRegistry.slice_id == slice_id, BaselineRegistry.version == version)
            .first()
        )
        if not existing_reg:
            reg_entry = BaselineRegistry(
                id=shared_id,
                slice_id=slice_id,
                nf_id=nf_id,
                version=version,
                is_anchor=True,
                is_active=True,
                training_window_count=len(training_windows),
                training_window_start=bundle["training_window_start"],
                training_window_end=bundle["training_window_end"],
                model_artifact_path=str(artifact_path),
                scaler_params=bundle["scaler_params"],
                threshold_params=bundle["threshold_params"],
                feature_schema=bundle["feature_schema"],
                created_at=bundle["created_at"],
            )
            db.add(reg_entry)

        # Check existing in baselines table
        existing_base = (
            db.query(Baseline)
            .filter(Baseline.slice_id == slice_id, Baseline.version == version)
            .first()
        )
        if not existing_base:
            base_entry = Baseline(
                id=shared_id,
                slice_id=slice_id,
                nf_id=nf_id,
                version=version,
                is_anchor=True,
                is_active=True,
                training_window_start=bundle["training_window_start"],
                training_window_end=bundle["training_window_end"],
                model_artifact_path=str(artifact_path),
                scaler_params=bundle["scaler_params"],
                threshold_params=bundle["threshold_params"],
                feature_schema=bundle["feature_schema"],
                created_at=bundle["created_at"],
            )
            db.add(base_entry)

        db.commit()
    except Exception as e:
        db.rollback()
        logger.error("Failed to register baseline for %s: %s", slice_id, e)
        raise
    finally:
        if owns_db:
            db.close()

    return bundle


def train_all_baselines(db: Optional[Session] = None) -> List[Dict[str, Any]]:
    """Train anchor baselines for all configured slices from synthetic training files."""
    # Ensure database tables exist
    Base.metadata.create_all(bind=engine)

    results: List[Dict[str, Any]] = []
    for cfg in SLICE_TRAINING_CONFIGS:
        t_file = cfg["training_file"]
        if not t_file.is_file():
            logger.warning("Training file not found: %s", t_file)
            continue

        with open(t_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            windows = data.get("windows", [])

        res = train_slice_baseline(
            slice_id=cfg["slice_id"],
            training_windows=windows,
            nf_id=cfg["nf_id"],
            version=cfg["version"],
            db=db,
        )
        results.append(res)

    return results
