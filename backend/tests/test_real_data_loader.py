"""Unit and Integration Tests for 5G-NIDD Real Data Loader and Real API Endpoints.
"""

from pathlib import Path
import pytest
from starlette.testclient import TestClient

from app.data_loader import (
    AttackLabel,
    TelemetryWindow,
    assign_slice_by_port_protocol,
    generate_manifest,
    load_5g_nidd_csv,
    map_attack_label,
    SLICE_EMBB,
    SLICE_URLLC,
    SLICE_MMTC,
)
from app.main import app

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
REAL_CSV_PATH = PROJECT_ROOT / "data" / "real" / "5g_nidd.csv"
REAL_MANIFEST_PATH = PROJECT_ROOT / "data" / "real" / "manifest.json"


@pytest.fixture
def client():
    return TestClient(app)


def test_slice_assignment_by_port_protocol():
    """Verify slice assignment matches 5G service profiles."""
    # URLLC: UDP DNS, NTP, RTP, WireGuard
    assert assign_slice_by_port_protocol("udp", 53, 45000) == SLICE_URLLC
    assert assign_slice_by_port_protocol("udp", 45000, 123) == SLICE_URLLC
    assert assign_slice_by_port_protocol("udp", 5004, 5005) == SLICE_URLLC
    assert assign_slice_by_port_protocol("udp", 51820, 51820) == SLICE_URLLC

    # mMTC: ICMP, MQTT, CoAP
    assert assign_slice_by_port_protocol("icmp", 0, 0) == SLICE_MMTC
    assert assign_slice_by_port_protocol("tcp", 1883, 40000) == SLICE_MMTC
    assert assign_slice_by_port_protocol("tcp", 8883, 40000) == SLICE_MMTC
    assert assign_slice_by_port_protocol("udp", 5683, 40000) == SLICE_MMTC

    # eMBB: Web traffic and general broadband
    assert assign_slice_by_port_protocol("tcp", 80, 50000) == SLICE_EMBB
    assert assign_slice_by_port_protocol("tcp", 443, 50000) == SLICE_EMBB
    assert assign_slice_by_port_protocol("tcp", 8080, 50000) == SLICE_EMBB
    assert assign_slice_by_port_protocol("tcp", 32000, 42000) == SLICE_EMBB


def test_attack_label_mapping():
    """Verify all 8 canonical 5G-NIDD attack classes map correctly."""
    assert map_attack_label("Benign", "Benign", "Benign") == AttackLabel.NORMAL
    assert map_attack_label("Malicious", "UDPFlood", "UDPFlood") == AttackLabel.UDP_FLOOD
    assert map_attack_label("Malicious", "HTTPFlood", "Goldeneye") == AttackLabel.HTTP_FLOOD
    assert map_attack_label("Malicious", "SYNFlood", "Hping3") == AttackLabel.SYN_FLOOD
    assert map_attack_label("Malicious", "TCPConnect", "Nmap") == AttackLabel.TCP_CONNECT
    assert map_attack_label("Malicious", "SYNScan", "Nmap") == AttackLabel.SYN_SCAN
    assert map_attack_label("Malicious", "Slowloris", "Slowloris") == AttackLabel.SLOWLORIS
    assert map_attack_label("Malicious", "Torshammer", "Torshammer") == AttackLabel.TORSHAMMER


def test_real_data_loader_file_and_schema():
    """Verify loading real 5G-NIDD dataset produces valid TelemetryWindow models."""
    assert REAL_CSV_PATH.is_file(), f"Missing real dataset at {REAL_CSV_PATH}"
    windows = load_5g_nidd_csv(REAL_CSV_PATH, window_duration_sec=60)

    assert len(windows) > 50, f"Expected substantial window count, got {len(windows)}"

    # Check schema conformance
    for w in windows:
        assert isinstance(w, TelemetryWindow)
        assert w.window_id and len(w.window_id) > 10
        assert w.timestamp.endswith("+00:00") or w.timestamp.endswith("Z")
        assert w.slice_id in (SLICE_EMBB, SLICE_URLLC, SLICE_MMTC)
        assert w.uplink_mb > 0
        assert w.downlink_mb > 0
        assert w.total_packets > 0
        assert 0.0 <= w.udp_ratio <= 1.0
        assert 0.0 <= w.tcp_ratio <= 1.0
        assert 0.0 <= w.icmp_ratio <= 1.0
        assert 0.0 <= w.syn_flag_ratio <= 1.0
        assert 0.0 <= w.rst_flag_ratio <= 1.0
        assert w.unique_src_ips >= 1
        assert w.unique_dst_ports >= 1
        assert w.avg_inter_arrival_ms >= 0.0
        assert w.inter_arrival_cv >= 0.0
        assert w.attack_label in [e.value for e in AttackLabel]


def test_manifest_generation():
    """Verify manifest generation accurately reflects window counts and classes."""
    windows = load_5g_nidd_csv(REAL_CSV_PATH, window_duration_sec=60)
    manifest = generate_manifest(windows)

    assert manifest["dataset"] == "5G-NIDD"
    assert manifest["version"] == "1.0"
    assert manifest["total_windows"] == len(windows)

    dist = manifest["attack_distribution"]
    for label in AttackLabel:
        assert label.value in dist
        assert dist[label.value] >= 0

    assert dist[AttackLabel.NORMAL.value] > 0
    assert dist[AttackLabel.UDP_FLOOD.value] > 0


def test_real_manifest_endpoint(client):
    """GET /api/real/manifest returns valid dataset metadata."""
    res = client.get("/api/real/manifest")
    assert res.status_code == 200
    data = res.json()
    assert data["dataset"] == "5G-NIDD"
    assert "attack_distribution" in data
    assert data["total_windows"] > 50


def test_real_windows_endpoint(client):
    """GET /api/real/windows returns paginated canonical windows."""
    res = client.get("/api/real/windows?limit=10&offset=0")
    assert res.status_code == 200
    data = res.json()
    assert len(data["items"]) == 10
    assert data["total"] > 50
    assert data["source"] == "5G-NIDD (Real)"

    # Slice filter test
    res_slice = client.get(f"/api/real/windows?slice_id={SLICE_EMBB}&limit=5")
    assert res_slice.status_code == 200
    for item in res_slice.json()["items"]:
        assert item["slice_id"] == SLICE_EMBB


def test_real_overview_endpoint(client):
    """GET /api/real/overview returns aggregate volume and timeline."""
    res = client.get("/api/real/overview")
    assert res.status_code == 200
    data = res.json()
    assert data["total_traffic_mb"] > 100.0, "Traffic volume must be non-zero"
    assert data["total_traffic_gb"] > 0.1
    assert data["total_packets"] > 1000
    assert data["active_slices_count"] == 3
    assert len(data["traffic_timeline"]) == data["total_windows"]
    assert data["source"] == "5G-NIDD (Real)"


def test_real_monitoring_endpoint(client):
    """GET /api/real/monitoring returns monitoring time-series and composition."""
    res = client.get("/api/real/monitoring?limit=25")
    assert res.status_code == 200
    data = res.json()
    assert len(data["time_series"]) == 25
    assert len(data["slice_breakdown"]) == 3
    assert "tcp_ratio" in data["protocol_summary"]
    assert data["source"] == "5G-NIDD (Real)"


def test_real_detection_endpoint(client):
    """GET /api/real/detection returns anomaly scores and evaluation metrics."""
    res = client.get("/api/real/detection?threshold=0.70")
    assert res.status_code == 200
    data = res.json()
    assert len(data["scored_windows"]) > 50
    stats = data["detection_stats"]
    assert stats["total_evaluated"] > 50
    assert stats["true_positives"] + stats["false_positives"] + stats["true_negatives"] + stats["false_negatives"] == stats["total_evaluated"]
    assert data["source"] == "5G-NIDD (Real)"
# CommShield AI Core
