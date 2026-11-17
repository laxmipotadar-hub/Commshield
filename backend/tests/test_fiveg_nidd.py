"""Tests for 5G-NIDD Real-Data Adapter, Canonical Schema Compliance, and Chronological Splitting.

Verifies:
1. Parsing flow-level records from tiny test fixture (tests/fixtures/nidd_sample.csv).
2. Canonical schema validation matching CONTRACTS.md via Pydantic CanonicalTrafficWindow.
3. Zero label leakage into feature dictionaries (raw_counters, ratio_features, composition_vector).
4. Strict non-overlapping chronological train, validation, and test periods.
5. Window-level ground truth mapping with attack_threshold and attack type persistence.
6. Assigned network slice mapping and labelled proxy metadata.
"""

from datetime import datetime, timezone
from pathlib import Path
import pytest

from backend.app.schemas.windows import CanonicalTrafficWindow
from ml_engine.preprocessing.adapters.fiveg_nidd import (
    BS1_SLICE_ID,
    BS2_SLICE_ID,
    FiveGNIDDAdapter,
    LABELLED_PROXIES,
    MISSING_CANONICAL_FIELDS,
    assign_slice_id,
    split_chronologically,
)
from ml_engine.preprocessing.windowing import RobustScaler

FIXTURE_PATH = Path(__file__).resolve().parent / "fixtures" / "nidd_sample.csv"


def test_fixture_exists_and_uncommitted():
    """Verify fixture is present in test directory and raw dataset is excluded."""
    assert FIXTURE_PATH.is_file(), f"Fixture file missing at {FIXTURE_PATH}"
    # File must be tiny (< 100 KB)
    assert FIXTURE_PATH.stat().st_size < 100_000, "Test fixture must be tiny sample only"


def test_adapter_parses_records_and_aggregates_canonical_windows():
    """Verify FiveGNIDDAdapter parses records and produces schema-compliant canonical windows."""
    adapter = FiveGNIDDAdapter(default_attack_threshold=0.05)
    records = list(adapter.parse_records(FIXTURE_PATH))
    assert len(records) > 0, "Adapter must parse records from CSV fixture"

    # Verify per-record normalized fields
    rec = records[0]
    assert "timestamp" in rec and isinstance(rec["timestamp"], datetime)
    assert "src_addr" in rec
    assert "tot_pkts" in rec
    assert "label" in rec

    # Adapt into 60s windows
    windows = adapter.adapt(records, slice_id=BS1_SLICE_ID, nf_id="UPF-01", window_duration_sec=60)
    assert len(windows) >= 3, "Fixture must aggregate into multiple 60s windows"

    # Validate each window against CanonicalTrafficWindow Pydantic schema
    for w in windows:
        validated = CanonicalTrafficWindow.model_validate(w)
        assert validated.window_id == w["window_id"]
        assert validated.slice_id == BS1_SLICE_ID
        assert validated.nf_id == "UPF-01"
        assert validated.duration_sec == 60

        # Raw counters check
        raw = w["raw_counters"]
        assert "active_ue_count" in raw
        assert "total_bytes_uplink" in raw
        assert "total_bytes_downlink" in raw
        assert "total_packets" in raw
        # Missing control plane counters default to 0 without fabrication
        assert raw["registration_attempts"] == 0
        assert raw["registration_failures"] == 0
        assert raw["nas_messages_total"] == 0
        assert raw["pfcp_association_messages"] == 0

        # Ratio features check
        ratios = w["ratio_features"]
        assert "pdu_session_rate_per_ue" in ratios
        assert "bytes_per_session" in ratios
        assert "packets_per_session" in ratios
        assert "ue_hash_entropy" in ratios
        assert "new_ue_rate" in ratios
        assert ratios["registrations_per_active_ue"] == 0.0
        assert ratios["nas_failure_ratio"] == 0.0
        assert ratios["pfcp_failure_ratio"] == 0.0

        # Composition vector check (sums to 1.0)
        comp = w["composition_vector"]
        assert comp["registration_ratio"] == 0.0
        assert comp["other_signalling_ratio"] == 1.0


def test_no_label_leakage_into_features():
    """Verify absolute absence of label or ground truth information in feature spaces."""
    adapter = FiveGNIDDAdapter()
    windows = adapter.adapt(FIXTURE_PATH, slice_id=BS1_SLICE_ID, nf_id="UPF-01", window_duration_sec=60)

    forbidden_keys = {
        "label", "Label", "attack_type", "Attack Type", "attack_tool", "Attack Tool",
        "is_attack", "malicious", "ground_truth"
    }

    for w in windows:
        # Check raw_counters
        for k in w["raw_counters"]:
            assert k not in forbidden_keys, f"Label leakage in raw_counters key: {k}"
        # Check ratio_features
        for k in w["ratio_features"]:
            assert k not in forbidden_keys, f"Label leakage in ratio_features key: {k}"
        # Check composition_vector
        for k in w["composition_vector"]:
            assert k not in forbidden_keys, f"Label leakage in composition_vector key: {k}"

        # Ground truth is isolated exclusively under 'ground_truth'
        assert "ground_truth" in w
        gt = w["ground_truth"]
        assert "is_attack" in gt
        assert isinstance(gt["is_attack"], bool)


def test_chronological_splitting_non_overlapping():
    """Verify chronological split guarantees non-overlapping train, validation, and test periods."""
    adapter = FiveGNIDDAdapter(default_attack_threshold=0.05)
    windows = adapter.adapt(FIXTURE_PATH, slice_id=BS1_SLICE_ID, nf_id="UPF-01", window_duration_sec=60)
    assert len(windows) >= 3

    train_w, val_w, test_w = split_chronologically(
        windows,
        train_ratio=0.4,
        val_ratio=0.3,
        benign_only_train=True,
    )

    assert len(train_w) > 0, "Training partition must not be empty"
    assert len(val_w) > 0, "Validation partition must not be empty"
    assert len(test_w) > 0, "Test partition must not be empty"

    # 1. Non-overlapping time ranges
    train_end = max(w["window_end"] for w in train_w)
    val_start = min(w["window_start"] for w in val_w)
    val_end = max(w["window_end"] for w in val_w)
    test_start = min(w["window_start"] for w in test_w)

    assert train_end <= val_start, f"Train ({train_end}) overlaps with Val ({val_start})"
    assert val_end <= test_start, f"Val ({val_end}) overlaps with Test ({test_start})"

    # 2. Benign purity in training set
    for w in train_w:
        assert w["ground_truth"]["is_attack"] is False, "Training period must contain strictly benign windows"

    # 3. Test set captures attack campaign
    has_test_attack = any(w["ground_truth"]["is_attack"] for w in test_w)
    assert has_test_attack is True, "Test period must contain attack windows from fixture"


def test_scaler_fit_strictly_on_train_data():
    """Verify that RobustScaler fit only on training windows transforms test windows without leaking."""
    adapter = FiveGNIDDAdapter()
    windows = adapter.adapt(FIXTURE_PATH, slice_id=BS1_SLICE_ID, nf_id="UPF-01", window_duration_sec=60)
    train_w, val_w, test_w = split_chronologically(windows, train_ratio=0.5, val_ratio=0.2, benign_only_train=True)

    scaler = RobustScaler()
    scaler.fit(train_w)
    assert scaler.fitted is True

    init_medians = dict(scaler.medians)
    init_iqrs = dict(scaler.iqrs)

    # Transform test windows
    transformed_test = scaler.transform(test_w)
    assert len(transformed_test) == len(test_w)
    assert "scaled_features" in transformed_test[0]

    # Invariant: Scaler parameters must be identical after transforming test windows
    assert scaler.medians == init_medians
    assert scaler.iqrs == init_iqrs


def test_assigned_slices_and_proxies_metadata():
    """Verify slice assignment definition and labelled proxy tracking in window metadata."""
    adapter = FiveGNIDDAdapter()

    assert assign_slice_id("BS1") == BS1_SLICE_ID
    assert assign_slice_id("BTS1") == BS1_SLICE_ID
    assert assign_slice_id("BS2") == BS2_SLICE_ID
    assert assign_slice_id("BTS2") == BS2_SLICE_ID

    window = adapter.aggregate_window(
        [],
        slice_id=BS2_SLICE_ID,
        nf_id="UPF-01",
        window_duration_sec=60,
    )

    meta = window.get("metadata", {})
    assert meta.get("dataset") == "fiveg_nidd"
    assert meta.get("is_assigned_slice") is True
    assert "labelled_proxies" in meta
    assert set(LABELLED_PROXIES).issubset(set(meta["labelled_proxies"]))
    assert set(MISSING_CANONICAL_FIELDS).issubset(set(meta["missing_canonical_fields"]))
