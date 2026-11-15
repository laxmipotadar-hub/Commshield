"""Shadow candidate baseline creator for CommShield Governance.

When traffic distribution drift is attributed as likely_benign, trains a candidate
baseline per slice on the active baseline's training data plus only windows
attributed as legitimate.
Strictly guarantees that quarantined or uncertain windows never enter training.
Saves candidate artifacts separately without modifying active baseline artifacts.
"""

from copy import deepcopy
from datetime import datetime, timezone
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
import uuid

import joblib
import numpy as np
from sqlalchemy.orm import Session

from backend.app.models import Baseline, CandidateBaseline, QuarantineWindow
from ml_engine.detection.autoencoder import AutoencoderDetector
from ml_engine.detection.isolation_forest import IsolationForestDetector
from ml_engine.preprocessing.windowing import FEATURE_NAMES, RobustScaler

logger = logging.getLogger("commshield.governance.candidate")

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
SYNTHETIC_DIR = PROJECT_ROOT / "data" / "synthetic"
CANDIDATES_DIR = PROJECT_ROOT / "data" / "processed" / "candidates"


def load_base_training_windows(slice_id: str) -> List[Dict[str, Any]]:
    """Load original clean benign training windows for a slice."""
    slice_map = {
        "sst-1-sd-010203": "training_embb.json",
        "sst-2-sd-010203": "training_urllc.json",
        "sst-3-sd-010203": "training_mmtc.json",
    }
    fname = slice_map.get(slice_id, "training_embb.json")
    fpath = SYNTHETIC_DIR / fname
    if not fpath.is_file():
        logger.warning("Slice training file %s not found.", fpath)
        return []

    with open(fpath, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("windows", [])


def build_shadow_candidate(
    slice_id: str,
    active_bundle: Dict[str, Any],
    anchor_bundle: Dict[str, Any],
    adaptation_windows: List[Dict[str, Any]],
    quarantined_window_ids: Optional[Set[str]] = None,
    candidate_version: Optional[str] = None,
    db: Optional[Session] = None,
    output_dir: Optional[Path] = None,
) -> Tuple[Dict[str, Any], CandidateBaseline]:
    """Build and train an isolated shadow candidate baseline.

    Args:
        slice_id: S-NSSAI identifier.
        active_bundle: Currently active serving baseline bundle.
        anchor_bundle: Trusted anchor baseline bundle.
        adaptation_windows: Windows attributed as legitimate growth to incorporate.
        quarantined_window_ids: Set of window IDs currently in quarantine.
        candidate_version: Semantic version identifier for the new candidate.
        db: Optional database session for persistence and validation.
        output_dir: Output directory for candidate artifact joblib file.

    Returns:
        Tuple of (candidate_bundle, CandidateBaseline DB record).
    """
    target_dir = output_dir or CANDIDATES_DIR
    target_dir.mkdir(parents=True, exist_ok=True)

    # 1. Enforce strict isolation: Quarantined & uncertain windows MUST NEVER enter training
    known_quarantined = set(quarantined_window_ids or [])
    if db is not None:
        db_q = db.query(QuarantineWindow.window_id).filter(QuarantineWindow.slice_id == slice_id).all()
        for row in db_q:
            known_quarantined.add(row[0])

    for w in adaptation_windows:
        w_id = w.get("window_id") or w.get("id")
        assert w_id not in known_quarantined, (
            f"SECURITY VIOLATION: Quarantined window {w_id} attempted to enter candidate training!"
        )

        attr = w.get("attribution") or {}
        verdict = attr.get("verdict") or w.get("verdict")
        assert verdict not in ("uncertain", "likely_attack"), (
            f"SECURITY VIOLATION: Window {w_id} with verdict '{verdict}' attempted to enter candidate training!"
        )

        gt = w.get("ground_truth") or {}
        if gt.get("is_attack"):
            raise AssertionError(
                f"SECURITY VIOLATION: Ground truth attack window {w_id} attempted to enter candidate training!"
            )

    # 2. Collect base training data + verified legitimate adaptation windows
    base_windows = load_base_training_windows(slice_id)
    combined_windows: List[Dict[str, Any]] = list(base_windows) + list(adaptation_windows)

    if not combined_windows:
        raise ValueError(f"No training windows available to build shadow candidate for slice {slice_id}")

    # Extract exact window IDs used
    training_window_ids = [
        w.get("window_id") or w.get("id") or f"win-{i}"
        for i, w in enumerate(combined_windows)
    ]

    # 3. Fit new RobustScaler on combined windows
    scaler = RobustScaler(feature_names=FEATURE_NAMES)
    scaler.fit(combined_windows)

    # Transform feature matrix
    X_list: List[List[float]] = []
    volume_list: List[float] = []
    comp_accum: Dict[str, float] = {}

    for w in combined_windows:
        ratios = w.get("ratio_features", {})
        scaled = scaler.transform_vector(ratios)
        X_list.append([scaled[f] for f in FEATURE_NAMES])

        raw = w.get("raw_counters", {})
        up_b = float(raw.get("total_bytes_uplink", 0))
        dn_b = float(raw.get("total_bytes_downlink", 0))
        volume_list.append(up_b + dn_b)

        comp = w.get("composition_vector", {})
        for k_cat, val in comp.items():
            comp_accum[k_cat] = comp_accum.get(k_cat, 0.0) + float(val)

    X = np.array(X_list, dtype=np.float32)
    n_win = max(1, len(combined_windows))
    mean_volume = float(np.mean(volume_list)) if volume_list else 1_000_000_000.0
    mean_composition = {k: round(v / n_win, 5) for k, v in comp_accum.items()}

    # 4. Train shadow detectors
    threshold_percentile = float(active_bundle.get("threshold_params", {}).get("threshold_percentile", 95.0))
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

    # 5. Versioning and artifact serialization (Separate from active baseline)
    parent_version = active_bundle.get("version", "v1.0.0-anchor")
    if not candidate_version:
        ts = int(datetime.now(timezone.utc).timestamp())
        candidate_version = f"v1.1.0-cand-{ts}"

    candidate_id = str(uuid.uuid4())
    artifact_filename = f"{slice_id}_{candidate_version}.joblib"
    artifact_path = target_dir / artifact_filename

    candidate_bundle = {
        "candidate_id": candidate_id,
        "slice_id": slice_id,
        "nf_id": active_bundle.get("nf_id", "UPF-01"),
        "version": candidate_version,
        "parent_version": parent_version,
        "candidate_version": candidate_version,
        "detector": if_detector,
        "isolation_forest": if_detector,
        "autoencoder": ae_detector,
        "detectors": {
            "isolation_forest": if_detector,
            "autoencoder": ae_detector,
        },
        "scaler": scaler,
        "scaler_params": scaler.to_dict(),
        "mean_volume_bytes": mean_volume,
        "composition_vector": mean_composition,
        "threshold_params": {
            "threshold_percentile": threshold_percentile,
            "cusum_threshold": 4.5,
        },
        "feature_schema": {"features": FEATURE_NAMES},
        "training_window_count": len(combined_windows),
        "adaptation_window_count": len(adaptation_windows),
        "training_window_ids": training_window_ids,
        "model_artifact_path": str(artifact_path),
        "created_at": datetime.now(timezone.utc),
    }

    # Save to disk separately; active baseline artifact is never overwritten!
    joblib.dump(candidate_bundle, artifact_path)
    logger.info("Saved shadow candidate baseline artifact to %s", artifact_path)

    # 6. Database record in candidate_baselines
    active_baseline_id = active_bundle.get("id") or str(uuid.uuid4())
    anchor_baseline_id = anchor_bundle.get("id") or str(uuid.uuid4())

    if db is not None:
        # Resolve active and anchor IDs from DB if possible
        act_row = db.query(Baseline).filter(Baseline.slice_id == slice_id, Baseline.is_active == True).first()
        anc_row = db.query(Baseline).filter(Baseline.slice_id == slice_id, Baseline.is_anchor == True).first()
        if act_row:
            active_baseline_id = act_row.id
        if anc_row:
            anchor_baseline_id = anc_row.id

    cand_row = CandidateBaseline(
        id=candidate_id,
        slice_id=slice_id,
        candidate_version=candidate_version,
        parent_version=parent_version,
        active_baseline_id=active_baseline_id,
        anchor_baseline_id=anchor_baseline_id,
        status="PENDING",
        gate_metrics={},
        decision_trace=[
            f"Candidate {candidate_version} created for slice {slice_id} from parent {parent_version} "
            f"with {len(combined_windows)} total windows ({len(adaptation_windows)} adaptation windows). "
            f"Quarantine isolation enforced."
        ],
        training_window_ids=training_window_ids,
        model_artifact_path=str(artifact_path),
        created_at=datetime.now(timezone.utc),
    )

    if db is not None:
        db.add(cand_row)
        db.commit()
        db.refresh(cand_row)

    return candidate_bundle, cand_row
