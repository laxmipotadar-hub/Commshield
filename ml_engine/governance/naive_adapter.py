"""Naive Adaptation Helper (Arm B Benchmark).

WARNING: RESEARCH BENCHMARK ONLY.
This module implements the un-gated, continuous retraining strategy (Arm B)
frequently seen in naive MLOps architectures (e.g. Gupta-style continuous training).

Whenever a drift alarm fires, naive adaptation unconditionally retrains the baseline
on recent windows without:
  1. Attribution filtering (attacks and normal shifts are treated identically).
  2. Quarantine exclusions (uncertain/suspicious windows are absorbed).
  3. Canary retention testing (attack blindness is not checked).
  4. Cumulative drift budgeting (parameter drift from anchor is unmonitored).
  5. Operator review and approval.

This serves as the critical contrast mechanism demonstrating baseline contamination
and attack blinding in the centrepiece three-arm evaluation experiment.
"""

from datetime import datetime, timezone
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
import uuid

import joblib
import numpy as np
from sqlalchemy.orm import Session

from backend.app.models import Baseline, BaselineRegistry
from ml_engine.detection.autoencoder import AutoencoderDetector
from ml_engine.detection.isolation_forest import IsolationForestDetector
from ml_engine.preprocessing.windowing import FEATURE_NAMES, RobustScaler

logger = logging.getLogger("commshield.governance.naive_adapter")

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
NAIVE_BASELINES_DIR = PROJECT_ROOT / "data" / "processed" / "naive_baselines"


def naive_retrain_on_drift(
    slice_id: str,
    recent_windows: List[Dict[str, Any]],
    active_baseline_bundle: Dict[str, Any],
    db: Optional[Session] = None,
    output_dir: Optional[Path] = None,
) -> Dict[str, Any]:
    """Retrain baseline unconditionally on recent traffic windows upon drift.

    Args:
        slice_id: S-NSSAI slice identifier.
        recent_windows: Recent streaming windows, regardless of attribution or ground truth.
        active_baseline_bundle: Previous active baseline bundle.
        db: Optional database session for updating Arm B state.
        output_dir: Artifact output directory.

    Returns:
        New naively updated baseline bundle.
    """
    target_dir = output_dir or NAIVE_BASELINES_DIR
    target_dir.mkdir(parents=True, exist_ok=True)

    if not recent_windows:
        logger.warning("Naive retrain called with empty windows for slice %s; retaining current.", slice_id)
        return active_baseline_bundle

    logger.warning(
        "[ARM B NAIVE ADAPTATION] Unconditionally retraining baseline for slice %s on %d windows "
        "WITHOUT attribution verification or canary checks.",
        slice_id,
        len(recent_windows),
    )

    # 1. Fit scaler directly on recent windows (including any attack contamination)
    scaler = RobustScaler(feature_names=FEATURE_NAMES)
    scaler.fit(recent_windows)

    X_list: List[List[float]] = []
    volume_list: List[float] = []
    comp_accum: Dict[str, float] = {}

    for w in recent_windows:
        ratios = w.get("ratio_features", {})
        scaled = scaler.transform_vector(ratios)
        X_list.append([scaled[f] for f in FEATURE_NAMES])

        raw = w.get("raw_counters", {})
        volume_list.append(float(raw.get("total_bytes_uplink", 0)) + float(raw.get("total_bytes_downlink", 0)))

        comp = w.get("composition_vector", {})
        for k_cat, val in comp.items():
            comp_accum[k_cat] = comp_accum.get(k_cat, 0.0) + float(val)

    X = np.array(X_list, dtype=np.float32)
    n_win = max(1, len(recent_windows))
    mean_vol = float(np.mean(volume_list)) if volume_list else 1_000_000_000.0
    mean_comp = {k: round(v / n_win, 5) for k, v in comp_accum.items()}

    # 2. Retrain detectors directly on contaminated data
    threshold_percentile = float(active_baseline_bundle.get("threshold_params", {}).get("threshold_percentile", 95.0))
    if_detector = IsolationForestDetector(
        n_estimators=100,
        contamination=0.05,
        random_state=42,
        threshold_percentile=threshold_percentile,
    )
    if_detector.fit(X)

    ae_detector = AutoencoderDetector(
        input_dim=len(FEATURE_NAMES),
        threshold_percentile=threshold_percentile,
        random_state=42,
    )
    ae_detector.fit(X)

    ts = int(datetime.now(timezone.utc).timestamp())
    naive_version = f"v-naive-arm-b-{ts}"
    artifact_path = target_dir / f"{slice_id}_{naive_version}.joblib"

    naive_bundle = {
        "slice_id": slice_id,
        "nf_id": active_baseline_bundle.get("nf_id", "UPF-01"),
        "version": naive_version,
        "is_anchor": False,
        "is_active": True,
        "detector": if_detector,
        "isolation_forest": if_detector,
        "autoencoder": ae_detector,
        "detectors": {
            "isolation_forest": if_detector,
            "autoencoder": ae_detector,
        },
        "scaler": scaler,
        "scaler_params": scaler.to_dict(),
        "mean_volume_bytes": mean_vol,
        "composition_vector": mean_comp,
        "threshold_params": {
            "threshold_percentile": threshold_percentile,
            "cusum_threshold": 4.5,
        },
        "feature_schema": {"features": FEATURE_NAMES},
        "training_window_count": len(recent_windows),
        "model_artifact_path": str(artifact_path),
        "created_at": datetime.now(timezone.utc),
    }

    joblib.dump(naive_bundle, artifact_path)

    return naive_bundle
