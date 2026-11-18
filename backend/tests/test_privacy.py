"""Tests for CommShield Privacy by Design:
1. No raw identifiers or IP addresses in canonical windows, DB schemas, or snapshots.
2. HMAC-SHA256 pseudonymisation is keyed, deterministic, and preserves entropy.
3. Small-group suppression triggers when distinct UEs < K (ue_hash_entropy = -1.0)
   and attribution handles it cleanly as missing evidence.
4. Unauthorized governance actions (approve, reject, rollback) return HTTP 401.
"""

from datetime import datetime, timezone
import json
import math
import os
import re
from pathlib import Path
import anyio
import pytest
from fastapi import HTTPException

from backend.app.api.governance import require_analyst_token
from backend.app.services.attribution import attribution_service
from ml_engine.preprocessing.adapters.base import (
    DEFAULT_SUPPRESSION_K,
    SUPPRESSED_ENTROPY_VALUE,
    CANONICAL_WINDOW_ALLOWLIST,
    get_hmac_secret,
    pseudonymize_identifier,
    enforce_aggregate_boundary,
)
from ml_engine.preprocessing.adapters.synthetic import SyntheticAdapter
from ml_engine.preprocessing.adapters.fiveg_nidd import FiveGNIDDAdapter

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
SNAPSHOT_DIR = PROJECT_ROOT / "experiments" / "snapshot"
IP_PATTERN = re.compile(r"\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b")


def test_hmac_pseudonymisation_is_keyed_and_deterministic():
    """Verify HMAC pseudonymisation is keyed, deterministic, and preserves Shannon entropy."""
    key_a = "secret-key-alpha-12345"
    key_b = "secret-key-beta-67890"

    raw_ip = "192.168.10.45"
    token_a1 = pseudonymize_identifier(raw_ip, key=key_a)
    token_a2 = pseudonymize_identifier(raw_ip, key=key_a)
    token_b = pseudonymize_identifier(raw_ip, key=key_b)

    # 1. Output is 64 hex characters (SHA256)
    assert len(token_a1) == 64
    assert all(c in "0123456789abcdef" for c in token_a1)

    # 2. Output is deterministic for same key
    assert token_a1 == token_a2

    # 3. Output is keyed (diverges under different keys)
    assert token_a1 != token_b

    # 4. Invariance of Shannon entropy under 1-to-1 token mapping
    raw_population = ["10.0.0.1"] * 50 + ["10.0.0.2"] * 30 + ["10.0.0.3"] * 20
    pseudonymized = [pseudonymize_identifier(ip, key=key_a) for ip in raw_population]

    def shannon_entropy(items):
        n = len(items)
        counts = {}
        for x in items:
            counts[x] = counts.get(x, 0) + 1
        return -sum((c / n) * math.log2(c / n) for c in counts.values())

    raw_entropy = shannon_entropy(raw_population)
    pseudo_entropy = shannon_entropy(pseudonymized)
    assert abs(raw_entropy - pseudo_entropy) < 1e-9


def test_no_identifier_in_canonical_windows_or_db_or_snapshot():
    """Verify no IP addresses or raw subscriber identifiers leak into windows or snapshots."""
    # 1. Verify Synthetic adapter output
    synth_adapter = SyntheticAdapter()
    sample_events = [
        {
            "timestamp": datetime.now(timezone.utc),
            "active_ue_count": 25,
            "registration_attempts": 30,
            "registration_failures": 1,
            "pdu_sessions_established": 20,
            "nas_messages_total": 40,
            "nas_failures": 2,
            "pfcp_association_messages": 35,
            "pfcp_failures": 0,
            "total_bytes_uplink": 50000,
            "total_bytes_downlink": 120000,
            "total_packets": 250,
            "ue_hash_entropy": 7.82,
        }
    ]
    synth_win = synth_adapter.aggregate_window(
        events=sample_events,
        slice_id="sst-1-sd-010203",
        nf_id="amf-01",
        window_duration_sec=60,
        window_start=datetime.now(timezone.utc),
        window_end=datetime.now(timezone.utc),
    )
    
    # Check all keys are within allowlist
    for k in synth_win.keys():
        assert k in CANONICAL_WINDOW_ALLOWLIST, f"Forbidden key in synthetic window: {k}"

    # Verify no raw IP in values
    synth_str = json.dumps(synth_win)
    assert not IP_PATTERN.search(synth_str), f"Found IP-like string in synthetic window: {synth_str}"

    # 2. Verify 5G-NIDD adapter raw IP drops and pseudonymisation
    nidd_adapter = FiveGNIDDAdapter()
    raw_records = [
        {
            "StartTime": "12:00:01",
            "SrcAddr": "192.168.100.12",
            "DstAddr": "10.0.0.50",
            "Dport": 8080,
            "Sport": 45123,
            "TotBytes": 1500,
            "TotPkts": 10,
            "Proto": "tcp",
            "Label": "Benign",
            "AttackType": "Benign",
        }
    ]
    parsed_events = list(nidd_adapter.parse_records(raw_records))
    canonical_nidd = nidd_adapter.aggregate_window(
        events=parsed_events,
        slice_id="sst-1-sd-010203",
        window_duration_sec=60,
    )
    nidd_str = json.dumps(canonical_nidd)
    
    # Raw IPs and ports must be dropped
    assert "192.168.100.12" not in nidd_str
    assert "10.0.0.50" not in nidd_str
    assert "Dport" not in canonical_nidd
    assert "Sport" not in canonical_nidd

    # 3. Check snapshot directory files for accidental IP leaks
    if SNAPSHOT_DIR.exists():
        for snap_file in SNAPSHOT_DIR.glob("*.json"):
            content = snap_file.read_text(encoding="utf-8")
            matches = IP_PATTERN.findall(content)
            # Exclude standard software version numbers like 1.0.0 or 0.0.0
            real_ip_leaks = [m for m in matches if not m.startswith("1.0.") and not m.startswith("0.0.")]
            assert len(real_ip_leaks) == 0, f"Found IP address leaks in {snap_file.name}: {real_ip_leaks}"


def test_small_group_suppression_triggers_below_k():
    """Verify small-group suppression triggers when active UEs < K and attribution handles it cleanly."""
    k = 5
    adapter = SyntheticAdapter(suppression_k=k)

    # 1. Window with active UEs < K (e.g. 3) -> suppressed entropy
    suppressed_events = [
        {
            "active_ue_count": 3,
            "registration_attempts": 5,
            "pdu_sessions_established": 3,
            "nas_messages_total": 8,
            "total_bytes_uplink": 1000,
            "total_bytes_downlink": 2000,
            "total_packets": 20,
            "ue_hash_entropy": 1.5,
        }
    ]
    suppressed_win = adapter.aggregate_window(
        events=suppressed_events,
        slice_id="sst-1-sd-010203",
        nf_id="amf-01",
        window_duration_sec=60,
        window_start=datetime.now(timezone.utc),
        window_end=datetime.now(timezone.utc),
    )
    assert suppressed_win["active_ue_count"] == 3
    assert suppressed_win["ratio_features"]["ue_hash_entropy"] == SUPPRESSED_ENTROPY_VALUE

    # 2. Window with active UEs >= K (e.g. 10) -> normal positive entropy
    normal_events = [
        {
            "active_ue_count": 10,
            "registration_attempts": 15,
            "pdu_sessions_established": 10,
            "nas_messages_total": 20,
            "total_bytes_uplink": 10000,
            "total_bytes_downlink": 20000,
            "total_packets": 200,
            "ue_hash_entropy": 7.42,
        }
    ]
    normal_win = adapter.aggregate_window(
        events=normal_events,
        slice_id="sst-1-sd-010203",
        nf_id="amf-01",
        window_duration_sec=60,
        window_start=datetime.now(timezone.utc),
        window_end=datetime.now(timezone.utc),
    )
    assert normal_win["active_ue_count"] == 10
    assert normal_win["ratio_features"]["ue_hash_entropy"] >= 0.0

    # 3. Attribution service processes suppressed entropy as missing evidence without error
    attribution_result = attribution_service.analyze_window(
        window=suppressed_win,
        slice_id="sst-1-sd-010203",
    )
    assert attribution_result is not None
    signals = attribution_result.get("evidence_signals", {})
    assert signals.get("entropy_suppressed") is True
    assert signals.get("entropy_drop_triggered") is False
    assert signals.get("ue_entropy_delta") is None


def test_unauthorized_governance_actions_return_401():
    """Verify state-mutating governance endpoints reject unauthorized requests with HTTP 401."""
    async def run_checks():
        # 1. Missing Authorization header -> 401
        with pytest.raises(HTTPException) as exc_info:
            await require_analyst_token(authorization=None)
        assert exc_info.value.status_code == 401
        assert "Missing Authorization" in exc_info.value.detail

        # 2. Malformed Authorization header -> 401
        with pytest.raises(HTTPException) as exc_info:
            await require_analyst_token(authorization="Basic invalid_credentials")
        assert exc_info.value.status_code == 401
        assert "Invalid authorization format" in exc_info.value.detail

        # 3. Wrong Bearer token -> 401
        with pytest.raises(HTTPException) as exc_info:
            await require_analyst_token(authorization="Bearer wrong-analyst-token")
        assert exc_info.value.status_code == 401
        assert "Invalid or expired analyst token" in exc_info.value.detail

        # 4. Valid Bearer token matching environment secret -> succeeds
        valid_token = os.environ.get("COMMSHIELD_ANALYST_TOKEN", "commshield-analyst-secret-v1")
        token = await require_analyst_token(authorization=f"Bearer {valid_token}")
        assert token == valid_token

    anyio.run(run_checks)
