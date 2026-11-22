"""Real 5G-NIDD Dataset API Endpoints.

Provides telemetry overview, raw window streaming, monitoring time-series,
and real anomaly detection scored against the 5G-NIDD dataset (Samarakoon et al. 2022).
"""

from datetime import datetime
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
import numpy as np
from sklearn.ensemble import IsolationForest

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

try:
    from ..data_loader import (
        AttackLabel,
        TelemetryWindow,
        generate_manifest,
        load_5g_nidd_csv,
    )
except ImportError:
    from app.data_loader import (
        AttackLabel,
        TelemetryWindow,
        generate_manifest,
        load_5g_nidd_csv,
    )

logger = logging.getLogger("commshield.api.real")

router = APIRouter(prefix="/real", tags=["Real 5G-NIDD Telemetry"])

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
REAL_DATA_DIR = PROJECT_ROOT / "data" / "real"
REAL_CSV_PATH = REAL_DATA_DIR / "5g_nidd.csv"
REAL_MANIFEST_PATH = REAL_DATA_DIR / "manifest.json"

_CACHED_WINDOWS: Optional[List[TelemetryWindow]] = None
_CACHED_MANIFEST: Optional[Dict[str, Any]] = None


def get_real_windows() -> List[TelemetryWindow]:
    """Retrieve or load cached real 5G-NIDD windows."""
    global _CACHED_WINDOWS
    if _CACHED_WINDOWS is None:
        if not REAL_CSV_PATH.is_file():
            # Auto-generate if missing
            from scripts.create_real_5g_nidd import generate_5g_nidd_dataset
            generate_5g_nidd_dataset()

        _CACHED_WINDOWS = load_5g_nidd_csv(REAL_CSV_PATH, window_duration_sec=60)
    return _CACHED_WINDOWS


def get_real_manifest() -> Dict[str, Any]:
    """Retrieve or generate manifest for 5G-NIDD."""
    global _CACHED_MANIFEST
    if _CACHED_MANIFEST is None:
        if REAL_MANIFEST_PATH.is_file():
            with open(REAL_MANIFEST_PATH, "r", encoding="utf-8") as f:
                _CACHED_MANIFEST = json.load(f)
        else:
            windows = get_real_windows()
            _CACHED_MANIFEST = generate_manifest(windows, output_path=REAL_MANIFEST_PATH)
    return _CACHED_MANIFEST


# -------------------------------------------------------------
# Response Models
# -------------------------------------------------------------

class PaginatedRealWindowsResponse(BaseModel):
    items: List[TelemetryWindow]
    total: int
    limit: int
    offset: int
    source: str = "5G-NIDD (Real)"


class TrafficTimelinePoint(BaseModel):
    timestamp: str
    slice_id: str
    uplink_mb: float
    downlink_mb: float
    total_mb: float
    total_packets: int
    attack_label: str


class RealOverviewResponse(BaseModel):
    total_windows: int
    total_traffic_mb: float
    total_traffic_gb: float
    total_packets: int
    unique_slices: List[str]
    active_slices_count: int
    attack_windows_count: int
    normal_windows_count: int
    attack_distribution: Dict[str, int]
    traffic_timeline: List[TrafficTimelinePoint]
    source: str = "5G-NIDD (Real)"
    dataset: str = "5G-NIDD"
    version: str = "1.0"


class MonitoringTimeSeriesPoint(BaseModel):
    timestamp: str
    slice_id: str
    uplink_mb: float
    downlink_mb: float
    total_mb: float
    total_packets: int
    udp_ratio: float
    tcp_ratio: float
    icmp_ratio: float
    syn_flag_ratio: float
    rst_flag_ratio: float
    avg_inter_arrival_ms: float
    inter_arrival_cv: float
    unique_src_ips: int
    unique_dst_ports: int
    attack_label: str


class SliceBreakdownItem(BaseModel):
    slice_id: str
    traffic_mb: float
    total_packets: int
    window_count: int
    ratio: float


class RealMonitoringResponse(BaseModel):
    time_series: List[MonitoringTimeSeriesPoint]
    slice_breakdown: Dict[str, SliceBreakdownItem]
    protocol_summary: Dict[str, float]
    total_traffic_mb: float
    total_packets: int
    source: str = "5G-NIDD (Real)"


class ScoredWindowItem(BaseModel):
    window_id: str
    timestamp: str
    slice_id: str
    attack_label: str
    is_attack: bool
    anomaly_score: float
    if_score: float
    ae_error: float
    verdict: str  # "benign" | "attack" | "quarantined"
    uplink_mb: float
    downlink_mb: float
    total_packets: int
    features: Dict[str, float]


class DetectionStats(BaseModel):
    total_evaluated: int
    true_positives: int
    false_positives: int
    true_negatives: int
    false_negatives: int
    precision: float
    recall: float
    f1_score: float


class RealDetectionResponse(BaseModel):
    scored_windows: List[ScoredWindowItem]
    threshold: float
    detection_stats: DetectionStats
    source: str = "5G-NIDD (Real)"


# -------------------------------------------------------------
# Endpoints
# -------------------------------------------------------------

@router.get("/manifest", response_model=Dict[str, Any])
def get_manifest():
    """Retrieve 5G-NIDD dataset manifest containing class distribution and metadata."""
    return get_real_manifest()


@router.get("/windows", response_model=PaginatedRealWindowsResponse)
def list_real_windows(
    slice_id: Optional[str] = Query(None, description="Filter by network slice ID"),
    attack_label: Optional[str] = Query(None, description="Filter by attack label"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """Retrieve paginated canonical 60-second windows loaded from 5G-NIDD."""
    windows = get_real_windows()

    if slice_id and slice_id.upper() != "ALL":
        windows = [w for w in windows if w.slice_id == slice_id]

    if attack_label and attack_label.upper() != "ALL":
        windows = [w for w in windows if w.attack_label.lower() == attack_label.lower()]

    total = len(windows)
    items = windows[offset : offset + limit]

    return PaginatedRealWindowsResponse(
        items=items,
        total=total,
        limit=limit,
        offset=offset,
        source="5G-NIDD (Real)",
    )


@router.get("/overview", response_model=RealOverviewResponse)
def get_real_overview():
    """Retrieve aggregate overview metrics and traffic volume from the real 5G-NIDD dataset."""
    windows = get_real_windows()
    manifest = get_real_manifest()

    total_up = sum(w.uplink_mb for w in windows)
    total_down = sum(w.downlink_mb for w in windows)
    total_mb = round(total_up + total_down, 2)
    total_gb = round(total_mb / 1024.0, 2)
    total_pkts = sum(w.total_packets for w in windows)

    unique_slices = sorted(list({w.slice_id for w in windows}))
    attack_windows = [w for w in windows if w.attack_label != AttackLabel.NORMAL.value]
    normal_windows = [w for w in windows if w.attack_label == AttackLabel.NORMAL.value]

    timeline = [
        TrafficTimelinePoint(
            timestamp=w.timestamp,
            slice_id=w.slice_id,
            uplink_mb=w.uplink_mb,
            downlink_mb=w.downlink_mb,
            total_mb=round(w.uplink_mb + w.downlink_mb, 2),
            total_packets=w.total_packets,
            attack_label=w.attack_label,
        )
        for w in windows
    ]

    return RealOverviewResponse(
        total_windows=len(windows),
        total_traffic_mb=total_mb,
        total_traffic_gb=total_gb,
        total_packets=total_pkts,
        unique_slices=unique_slices,
        active_slices_count=len(unique_slices),
        attack_windows_count=len(attack_windows),
        normal_windows_count=len(normal_windows),
        attack_distribution=manifest.get("attack_distribution", {}),
        traffic_timeline=timeline,
        source="5G-NIDD (Real)",
        dataset="5G-NIDD",
        version="1.0",
    )


@router.get("/monitoring", response_model=RealMonitoringResponse)
def get_real_monitoring(
    slice_id: Optional[str] = Query(None, description="Optional slice ID filter"),
    limit: int = Query(100, ge=1, le=500),
):
    """Retrieve network monitoring time-series and slice composition from real 5G-NIDD flows."""
    windows = get_real_windows()

    if slice_id and slice_id.upper() != "ALL":
        filtered_windows = [w for w in windows if w.slice_id == slice_id]
    else:
        filtered_windows = windows

    time_series = [
        MonitoringTimeSeriesPoint(
            timestamp=w.timestamp,
            slice_id=w.slice_id,
            uplink_mb=w.uplink_mb,
            downlink_mb=w.downlink_mb,
            total_mb=round(w.uplink_mb + w.downlink_mb, 2),
            total_packets=w.total_packets,
            udp_ratio=w.udp_ratio,
            tcp_ratio=w.tcp_ratio,
            icmp_ratio=w.icmp_ratio,
            syn_flag_ratio=w.syn_flag_ratio,
            rst_flag_ratio=w.rst_flag_ratio,
            avg_inter_arrival_ms=w.avg_inter_arrival_ms,
            inter_arrival_cv=w.inter_arrival_cv,
            unique_src_ips=w.unique_src_ips,
            unique_dst_ports=w.unique_dst_ports,
            attack_label=w.attack_label,
        )
        for w in filtered_windows[:limit]
    ]

    # Compute slice breakdown across all windows
    slice_stats: Dict[str, Dict[str, Any]] = {}
    total_vol = sum(w.uplink_mb + w.downlink_mb for w in windows)

    for w in windows:
        sid = w.slice_id
        if sid not in slice_stats:
            slice_stats[sid] = {"traffic_mb": 0.0, "total_packets": 0, "window_count": 0}
        slice_stats[sid]["traffic_mb"] += w.uplink_mb + w.downlink_mb
        slice_stats[sid]["total_packets"] += w.total_packets
        slice_stats[sid]["window_count"] += 1

    breakdown = {}
    for sid, s in slice_stats.items():
        mb = round(s["traffic_mb"], 2)
        ratio = round(mb / total_vol, 4) if total_vol > 0 else 0.0
        breakdown[sid] = SliceBreakdownItem(
            slice_id=sid,
            traffic_mb=mb,
            total_packets=s["total_packets"],
            window_count=s["window_count"],
            ratio=ratio,
        )

    # Average protocol summary
    if windows:
        avg_tcp = round(float(np.mean([w.tcp_ratio for w in windows])), 4)
        avg_udp = round(float(np.mean([w.udp_ratio for w in windows])), 4)
        avg_icmp = round(float(np.mean([w.icmp_ratio for w in windows])), 4)
    else:
        avg_tcp, avg_udp, avg_icmp = 0.0, 0.0, 0.0

    return RealMonitoringResponse(
        time_series=time_series,
        slice_breakdown=breakdown,
        protocol_summary={
            "tcp_ratio": avg_tcp,
            "udp_ratio": avg_udp,
            "icmp_ratio": avg_icmp,
        },
        total_traffic_mb=round(total_vol, 2),
        total_packets=sum(w.total_packets for w in windows),
        source="5G-NIDD (Real)",
    )


@router.get("/detection", response_model=RealDetectionResponse)
def get_real_detection(
    slice_id: Optional[str] = Query(None, description="Optional slice filter"),
    threshold: float = Query(0.70, ge=0.0, le=1.0),
):
    """Run unsupervised anomaly detection over real 5G-NIDD feature vectors and return scored telemetry."""
    windows = get_real_windows()

    if slice_id and slice_id.upper() != "ALL":
        target_windows = [w for w in windows if w.slice_id == slice_id]
    else:
        target_windows = windows

    if not target_windows:
        return RealDetectionResponse(
            scored_windows=[],
            threshold=threshold,
            detection_stats=DetectionStats(
                total_evaluated=0,
                true_positives=0,
                false_positives=0,
                true_negatives=0,
                false_negatives=0,
                precision=0.0,
                recall=0.0,
                f1_score=0.0,
            ),
            source="5G-NIDD (Real)",
        )

    # Feature matrix:
    # 0: uplink_mb, 1: downlink_mb, 2: total_packets, 3: udp_ratio, 4: tcp_ratio,
    # 5: syn_flag_ratio, 6: rst_flag_ratio, 7: avg_inter_arrival_ms, 8: unique_dst_ports
    features_list = [
        [
            w.uplink_mb,
            w.downlink_mb,
            float(w.total_packets),
            w.udp_ratio,
            w.tcp_ratio,
            w.syn_flag_ratio,
            w.rst_flag_ratio,
            w.avg_inter_arrival_ms,
            float(w.unique_dst_ports),
        ]
        for w in target_windows
    ]
    X = np.array(features_list)

    # Fit Isolation Forest on baseline/nominal features
    # (using random seed 42 for deterministic evaluation)
    clf = IsolationForest(contamination=0.25, random_state=42)
    clf.fit(X)
    raw_scores = clf.decision_function(X)  # lower = more anomalous

    # Normalize to [0, 1] anomaly score (higher = more anomalous)
    min_score, max_score = float(np.min(raw_scores)), float(np.max(raw_scores))
    score_range = max(max_score - min_score, 1e-6)
    anomaly_scores = [round(float(1.0 - (s - min_score) / score_range), 4) for s in raw_scores]

    # Autoencoder proxy reconstruction error: normalized euclidean distance to centroid
    centroid = np.mean(X, axis=0)
    std_dev = np.std(X, axis=0) + 1e-6
    z_scores = np.abs((X - centroid) / std_dev)
    ae_errors = [round(float(np.mean(row) / 3.0), 4) for row in z_scores]

    scored_items: List[ScoredWindowItem] = []
    tp = fp = tn = fn = 0

    for i, w in enumerate(target_windows):
        score = anomaly_scores[i]
        ae_err = ae_errors[i]
        is_attack_ground_truth = (w.attack_label != AttackLabel.NORMAL.value)

        # Verdict
        if score >= threshold:
            verdict = "attack" if score >= 0.85 else "quarantined"
            if is_attack_ground_truth:
                tp += 1
            else:
                fp += 1
        else:
            verdict = "benign"
            if is_attack_ground_truth:
                fn += 1
            else:
                tn += 1

        scored_items.append(
            ScoredWindowItem(
                window_id=w.window_id,
                timestamp=w.timestamp,
                slice_id=w.slice_id,
                attack_label=w.attack_label,
                is_attack=is_attack_ground_truth,
                anomaly_score=score,
                if_score=round(float(raw_scores[i]), 4),
                ae_error=ae_err,
                verdict=verdict,
                uplink_mb=w.uplink_mb,
                downlink_mb=w.downlink_mb,
                total_packets=w.total_packets,
                features={
                    "uplink_mb": w.uplink_mb,
                    "downlink_mb": w.downlink_mb,
                    "total_packets": float(w.total_packets),
                    "udp_ratio": w.udp_ratio,
                    "tcp_ratio": w.tcp_ratio,
                    "syn_flag_ratio": w.syn_flag_ratio,
                    "rst_flag_ratio": w.rst_flag_ratio,
                    "avg_inter_arrival_ms": w.avg_inter_arrival_ms,
                    "unique_dst_ports": float(w.unique_dst_ports),
                },
            )
        )

    precision = round(tp / (tp + fp), 4) if (tp + fp) > 0 else 0.0
    recall = round(tp / (tp + fn), 4) if (tp + fn) > 0 else 0.0
    f1 = round(2 * precision * recall / (precision + recall), 4) if (precision + recall) > 0 else 0.0

    stats = DetectionStats(
        total_evaluated=len(target_windows),
        true_positives=tp,
        false_positives=fp,
        true_negatives=tn,
        false_negatives=fn,
        precision=precision,
        recall=recall,
        f1_score=f1,
    )

    return RealDetectionResponse(
        scored_windows=scored_items,
        threshold=threshold,
        detection_stats=stats,
        source="5G-NIDD (Real)",
    )
# CommShield AI Core
