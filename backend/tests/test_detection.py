"""Tests for baseline learning, Isolation Forest detection, alerts, and evaluation metrics."""

import json
from pathlib import Path
import pytest
from httpx import ASGITransport, AsyncClient
import numpy as np

from backend.app.database import SessionLocal
from backend.app.main import app
from backend.app.models import AnomalyAlert, Baseline, BaselineRegistry, CanonicalWindow
from backend.app.services.detection import detection_service
from ml_engine.detection.isolation_forest import IsolationForestDetector

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
SYNTHETIC_DIR = PROJECT_ROOT / "data" / "synthetic"


@pytest.fixture
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac


def test_baseline_version_registration():
    """Verify that a baseline per slice is registered in baseline_registry with version, creation time, and window count."""
    db = SessionLocal()
    try:
        registrations = db.query(BaselineRegistry).all()
        assert len(registrations) >= 3, "Expected at least 3 slice baselines in baseline_registry"

        slices = {r.slice_id: r for r in registrations}
        expected_slices = ["sst-1-sd-010203", "sst-2-sd-010203", "sst-3-sd-010203"]

        for s_id in expected_slices:
            assert s_id in slices, f"Slice {s_id} missing in baseline_registry"
            entry = slices[s_id]
            assert entry.version == "v1.0.0-anchor"
            assert entry.is_anchor is True
            assert entry.is_active is True
            assert entry.training_window_count == 60
            assert entry.created_at is not None
            assert Path(entry.model_artifact_path).is_file()
            assert "features" in entry.feature_schema

        # Also verify baseline table synchronization
        baselines = db.query(Baseline).filter(Baseline.version == "v1.0.0-anchor").all()
        assert len(baselines) >= 3
    finally:
        db.close()


def test_percentile_scores_stay_within_0_to_100():
    """Verify that calibrated percentile scores stay strictly within [0.0, 100.0] for any input."""
    # Fit detector on synthetic benign points
    rng = np.random.RandomState(42)
    X_train = rng.normal(loc=0.0, scale=1.0, size=(100, 9))
    detector = IsolationForestDetector(n_estimators=50, random_state=42)
    detector.fit(X_train)

    # Test extreme negative, extreme positive, normal, and outlier raw scores
    test_scores = [-1000.0, -10.0, -0.5, 0.0, 0.45, 0.85, 10.0, 1000.0]
    for raw_score in test_scores:
        pct = detector.score_percentile(raw_score)
        assert 0.0 <= pct <= 100.0, f"Percentile {pct} out of bounds [0, 100] for raw score {raw_score}"

    # Test random evaluation vectors
    X_test = rng.uniform(-10.0, 10.0, size=(50, 9))
    for x in X_test:
        raw, pct, flagged = detector.evaluate_sample(x)
        assert 0.0 <= pct <= 100.0, f"Percentile {pct} out of bounds [0, 100] for vector"
        assert isinstance(flagged, bool)


def test_alerts_produced_for_attack_windows():
    """Verify that alerts are produced for attack windows in the obvious attack scenario."""
    attack_file = SYNTHETIC_DIR / "attack_in_growth.json"
    assert attack_file.is_file(), f"File {attack_file} missing"

    with open(attack_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    windows = data.get("windows", [])

    attack_windows = [w for w in windows if w.get("ground_truth", {}).get("is_attack")]
    assert len(attack_windows) > 0, "No attack windows found in attack_in_growth scenario"

    db = SessionLocal()
    initial_alerts_count = db.query(AnomalyAlert).count()
    db.close()

    flagged_count = 0
    for w in attack_windows:
        output = detection_service.analyze_window(w)
        if output.fusion.is_anomalous:
            flagged_count += 1
            assert output.isolation_forest.is_flagged is True
            assert output.isolation_forest.benign_percentile >= output.isolation_forest.threshold_percentile

    assert flagged_count > 0, "Expected at least one alert to be produced for obvious attack windows"

    db = SessionLocal()
    try:
        final_alerts_count = db.query(AnomalyAlert).count()
        assert final_alerts_count > initial_alerts_count, "Expected anomaly_alerts table to contain new alert records"
    finally:
        db.close()


@pytest.mark.anyio
async def test_endpoint_detection_analyze(client: AsyncClient):
    """Test POST /api/detection/analyze per CONTRACTS.md."""
    sample_file = SYNTHETIC_DIR / "slow_attack_ramp.json"
    with open(sample_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    sample_window = data["windows"][0]

    payload = {"window": sample_window}
    response = await client.post("/api/detection/analyze", json=payload)
    assert response.status_code == 200
    res_data = response.json()

    assert res_data["window_id"] == sample_window["window_id"]
    assert res_data["slice_id"] == sample_window["slice_id"]
    assert res_data["baseline_version"] == "v1.0.0-anchor"
    assert "isolation_forest" in res_data
    assert "raw_score_negated" in res_data["isolation_forest"]
    assert "benign_percentile" in res_data["isolation_forest"]
    assert 0.0 <= res_data["isolation_forest"]["benign_percentile"] <= 100.0

    # autoencoder and cusum must NOT be null per prompt and CONTRACTS.md
    assert res_data["autoencoder"] is not None
    assert "reconstruction_mse" in res_data["autoencoder"]
    assert "benign_percentile" in res_data["autoencoder"]
    assert 0.0 <= res_data["autoencoder"]["benign_percentile"] <= 100.0

    assert res_data["cusum"] is not None
    assert "accumulated_statistic" in res_data["cusum"]
    assert "alarm_threshold" in res_data["cusum"]
    assert "is_alarm" in res_data["cusum"]

    # fused percentile equals max of IF and AE percentiles
    assert res_data["fusion"]["fused_percentile"] >= res_data["isolation_forest"]["benign_percentile"]
    assert res_data["is_placeholder"] is False


@pytest.mark.anyio
async def test_endpoint_alerts(client: AsyncClient):
    """Test GET /api/alerts per CONTRACTS.md."""
    response = await client.get("/api/alerts?limit=10")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    if len(data) > 0:
        alert = data[0]
        assert "id" in alert
        assert "window_id" in alert
        assert "slice_id" in alert
        assert "detector_output" in alert
        assert alert["is_placeholder"] is False


@pytest.mark.anyio
async def test_endpoint_baselines(client: AsyncClient):
    """Test GET /api/baselines per CONTRACTS.md."""
    response = await client.get("/api/baselines?slice_id=sst-1-sd-010203")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    b = data[0]
    assert b["slice_id"] == "sst-1-sd-010203"
    assert b["version"] == "v1.0.0-anchor"
    assert b["is_anchor"] is True
    assert b["is_active"] is True
    assert b["is_placeholder"] is False


@pytest.mark.anyio
async def test_endpoint_dashboard_overview(client: AsyncClient):
    """Test GET /api/dashboard/overview per CONTRACTS.md."""
    response = await client.get("/api/dashboard/overview")
    assert response.status_code == 200
    data = response.json()
    assert "total_traffic_bytes" in data
    assert "active_slices_count" in data
    assert "anomaly_alerts_count" in data
    assert "drift_status" in data
    assert "quarantined_windows_count" in data
    assert "active_baseline_version" in data
    assert "recent_alerts" in data
    assert "traffic_over_time" in data
    assert data["is_placeholder"] is False


def test_scenario_metrics_and_print():
    """Replay each scenario, compute detection recall and FPR against ground truth, and print honest numbers."""
    scenarios = [
        "stable_benign",
        "legitimate_growth",
        "slow_attack_ramp",
        "attack_in_growth",
        "mimicry_attack",
    ]

    metrics = {}
    print("\n--- Empirical Scenario Detection Metrics ---")
    for sc in scenarios:
        scenario_file = SYNTHETIC_DIR / f"{sc}.json"
        assert scenario_file.is_file(), f"Missing scenario file {scenario_file}"
        with open(scenario_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        windows = data.get("windows", [])
        tp = fp = tn = fn = 0

        for w in windows:
            gt = w.get("ground_truth", {})
            is_attack = bool(gt.get("is_attack", False))
            out = detection_service.analyze_window(w)
            pred = bool(out.fusion.is_anomalous)

            if is_attack and pred:
                tp += 1
            elif is_attack and not pred:
                fn += 1
            elif not is_attack and pred:
                fp += 1
            else:
                tn += 1

        total_pos = tp + fn
        total_neg = tn + fp
        recall = (tp / total_pos) if total_pos > 0 else 0.0
        fpr = (fp / total_neg) if total_neg > 0 else 0.0

        metrics[sc] = {
            "windows": len(windows),
            "tp": tp,
            "fn": fn,
            "fp": fp,
            "tn": tn,
            "recall": recall,
            "fpr": fpr,
        }

        print(
            f"{sc:18s} | Windows: {len(windows):2d} | Pos: {total_pos:2d} (TP:{tp:2d}, FN:{fn:2d}) "
            f"| Neg: {total_neg:2d} (FP:{fp:2d}, TN:{tn:2d}) | Recall: {recall:.4f} | FPR: {fpr:.4f}"
        )

    # Sanity checks without asserting artificial thresholds
    assert len(metrics) == 5
    for sc, m in metrics.items():
        assert 0.0 <= m["recall"] <= 1.0
        assert 0.0 <= m["fpr"] <= 1.0
