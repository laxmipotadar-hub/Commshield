"""Canary attack retention and rescaling for CommShield Governance.

Checks that adapting to legitimate growth has not degraded detector sensitivity
to malicious attack behaviors. Evaluates held-out attack windows (canaries)
rescaled to the current traffic level.
"""

from copy import deepcopy
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from ml_engine.preprocessing.windowing import FEATURE_NAMES
from .config import (
    CANARY_RECALL_MARGIN_DELTA,
    CANARY_SCALE_METHOD,
    DRIFT_BUDGET_CANARY_SHIFT_B_CAN,
)

logger = logging.getLogger("commshield.governance.canary")

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
SYNTHETIC_DIR = PROJECT_ROOT / "data" / "synthetic"


def load_canary_dataset(
    slice_id: Optional[str] = None,
    exclude_scenario: Optional[str] = None,
    max_canaries: int = 40,
) -> List[Dict[str, Any]]:
    """Load held-out attack windows from synthetic scenario files as canaries."""
    canaries: List[Dict[str, Any]] = []
    scenario_files = ["slow_attack_ramp.json", "attack_in_growth.json", "mimicry_attack.json"]

    for fname in scenario_files:
        scenario_name = fname.replace(".json", "")
        if exclude_scenario and scenario_name == exclude_scenario:
            continue

        fpath = SYNTHETIC_DIR / fname
        if not fpath.is_file():
            continue

        try:
            with open(fpath, "r", encoding="utf-8") as f:
                data = json.load(f)
            windows = data.get("windows", [])
            for w in windows:
                gt = w.get("ground_truth", {})
                if gt.get("is_attack"):
                    canary = deepcopy(w)
                    canary["canary_category"] = gt.get("attack_type", scenario_name)
                    canary["source_scenario"] = scenario_name
                    if slice_id and canary.get("slice_id") != slice_id:
                        canary["slice_id"] = slice_id
                    canaries.append(canary)
        except Exception as e:
            logger.warning("Error reading canary file %s: %s", fname, e)

    # Subsample deterministically across categories if too large
    if len(canaries) > max_canaries:
        step = max(1, len(canaries) // max_canaries)
        canaries = canaries[::step][:max_canaries]

    return canaries


def rescale_canary_window(
    canary_window: Dict[str, Any],
    volume_multiplier: float = 1.0,
    mode: str = CANARY_SCALE_METHOD,
) -> Dict[str, Any]:
    """Rescale an attack canary window to the current traffic volume level.

    As required by COMMSHIELD_SPEC_v9.md Section B:
    An old attack replayed at its old volume would be less anomalous after
    legitimate growth and would wrongly penalize good adaptation.
    Express count-like features proportional to k, while preserving
    bounded ratios and anomaly signals.
    """
    rescaled = deepcopy(canary_window)
    k = max(0.1, float(volume_multiplier))

    if mode == "fixed" or abs(k - 1.0) < 1e-4:
        return rescaled

    # Proportional rescaling for raw counters
    raw = rescaled.get("raw_counters", {})
    if "total_bytes_uplink" in raw:
        raw["total_bytes_uplink"] = int(raw["total_bytes_uplink"] * k)
    if "total_bytes_downlink" in raw:
        raw["total_bytes_downlink"] = int(raw["total_bytes_downlink"] * k)
    if "total_packets" in raw:
        raw["total_packets"] = int(raw["total_packets"] * k)
    if "active_ue_count" in raw:
        raw["active_ue_count"] = max(1, int(raw["active_ue_count"] * k))
    if "pdu_sessions_established" in raw:
        raw["pdu_sessions_established"] = max(1, int(raw["pdu_sessions_established"] * k))

    # Ratio features: per-UE volume scales with k, but anomaly ratios (failures, session rates) stay intact
    ratios = rescaled.get("ratio_features", {})
    if "gtpu_volume_per_ue" in ratios:
        ratios["gtpu_volume_per_ue"] = float(ratios["gtpu_volume_per_ue"]) * k
    if "bytes_per_session" in ratios:
        ratios["bytes_per_session"] = float(ratios["bytes_per_session"]) * k

    return rescaled


def _score_windows_with_bundle(
    windows: List[Dict[str, Any]],
    bundle: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """Score a sequence of canonical windows using a baseline artifact bundle."""
    scaler = bundle.get("scaler")
    detectors = bundle.get("detectors") or {}
    if not detectors and "detector" in bundle:
        detectors = {"isolation_forest": bundle["detector"]}
    if_det = detectors.get("isolation_forest") or bundle.get("isolation_forest")
    ae_det = detectors.get("autoencoder") or bundle.get("autoencoder")

    threshold_pct = float(bundle.get("threshold_params", {}).get("threshold_percentile", 95.0))
    results: List[Dict[str, Any]] = []

    for w in windows:
        ratios = w.get("ratio_features", {})
        if scaler is not None:
            scaled = scaler.transform_vector(ratios)
            x_vec = np.array([[scaled[f] for f in FEATURE_NAMES]], dtype=np.float32)
        else:
            x_vec = np.array([[ratios.get(f, 0.0) for f in FEATURE_NAMES]], dtype=np.float32)

        if_pct = 50.0
        ae_pct = 50.0

        if if_det is not None:
            try:
                _, if_pct, _ = if_det.evaluate_sample(x_vec)
            except Exception:
                raw_score = float(if_det.score(x_vec)[0])
                if_pct = if_det.score_percentile(raw_score)

        if ae_det is not None:
            try:
                _, ae_pct, _ = ae_det.evaluate_sample(x_vec)
            except Exception:
                raw_score = float(ae_det.score(x_vec)[0])
                ae_pct = ae_det.score_percentile(raw_score)

        fused_pct = max(if_pct, ae_pct)
        is_flagged = fused_pct >= threshold_pct

        results.append({
            "fused_percentile": fused_pct,
            "if_percentile": if_pct,
            "ae_percentile": ae_pct,
            "is_flagged": is_flagged,
            "category": w.get("canary_category", "general_attack"),
        })

    return results


def evaluate_canary_retention(
    active_bundle: Dict[str, Any],
    candidate_bundle: Dict[str, Any],
    canary_windows: List[Dict[str, Any]],
    volume_multiplier: float = 1.0,
    margin_delta: float = CANARY_RECALL_MARGIN_DELTA,
) -> Dict[str, Any]:
    """Execute canary retention test comparing active and candidate models.

    Returns:
        Dict with overall pass, active_recall, candidate_recall, recall_delta,
        delta_canary score degradation, and per-category recall breakdowns.
    """
    if not canary_windows:
        logger.warning("No canary windows available for canary retention test.")
        return {
            "passed": True,
            "active_recall": 1.0,
            "candidate_recall": 1.0,
            "recall_delta": 0.0,
            "delta_canary": 0.0,
            "category_recalls": {},
            "canary_count": 0,
        }

    # Rescale canaries to current volume level
    rescaled_canaries = [
        rescale_canary_window(w, volume_multiplier=volume_multiplier)
        for w in canary_windows
    ]

    # Score on active and candidate models
    active_scores = _score_windows_with_bundle(rescaled_canaries, active_bundle)
    candidate_scores = _score_windows_with_bundle(rescaled_canaries, candidate_bundle)

    n_total = len(rescaled_canaries)
    active_hits = sum(1 for s in active_scores if s["is_flagged"])
    candidate_hits = sum(1 for s in candidate_scores if s["is_flagged"])

    active_recall = active_hits / max(1, n_total)
    candidate_recall = candidate_hits / max(1, n_total)
    recall_delta = active_recall - candidate_recall

    # Delta_canary: median difference in detection strength
    score_diffs = [
        act["fused_percentile"] - cand["fused_percentile"]
        for act, cand in zip(active_scores, candidate_scores)
    ]
    delta_can = float(np.median(score_diffs)) if score_diffs else 0.0

    # Per-category evaluation
    categories = sorted(list(set(s["category"] for s in active_scores)))
    category_recalls: Dict[str, Any] = {}
    categories_passed = True

    for cat in categories:
        cat_act_hits = sum(1 for s in active_scores if s["category"] == cat and s["is_flagged"])
        cat_cand_hits = sum(1 for s in candidate_scores if s["category"] == cat and s["is_flagged"])
        cat_total = sum(1 for s in active_scores if s["category"] == cat)

        cat_act_rec = cat_act_hits / max(1, cat_total)
        cat_cand_rec = cat_cand_hits / max(1, cat_total)
        cat_delta = cat_act_rec - cat_cand_rec
        cat_passed = cat_delta <= margin_delta

        category_recalls[cat] = {
            "active_recall": round(cat_act_rec, 4),
            "candidate_recall": round(cat_cand_rec, 4),
            "recall_delta": round(cat_delta, 4),
            "passed": cat_passed,
            "count": cat_total,
        }
        if not cat_passed:
            categories_passed = False

    overall_passed = (recall_delta <= margin_delta) and categories_passed

    return {
        "passed": bool(overall_passed),
        "active_recall": round(active_recall, 4),
        "candidate_recall": round(candidate_recall, 4),
        "recall_delta": round(recall_delta, 4),
        "delta_canary": round(delta_can, 4),
        "category_recalls": category_recalls,
        "canary_count": n_total,
    }
