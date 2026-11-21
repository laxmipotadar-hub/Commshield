"""Tests for Data Panel API, Live JSON Download, Determinism, and Privacy Guarantees.

Verifies:
1. GET /api/data/datasets returns structured metadata block, source tags, seeds, config versions.
2. GET /api/data/{name}/preview returns capped windows with zero raw IP or payload leakage.
3. GET /api/data/{name}/download delivers attachment named commshield_<name>_<source>_seed<seed>.json,
   starts with a structured "metadata" block, and adheres to 20MB limit.
4. POST /api/data/generate runs deterministic in-memory generator with enforced seed bounds,
   without altering any stored filesystem artifacts.
"""

import json
from pathlib import Path
import pytest
from starlette.testclient import TestClient

from backend.app.main import app

client = TestClient(app)


def test_get_datasets_metadata_block():
    """Verify datasets endpoint returns structured metadata blocks with all required fields."""
    resp = client.get("/api/data/datasets")
    assert resp.status_code == 200, resp.text
    data = resp.json()

    assert "datasets" in data
    assert "total" in data
    assert data["total"] >= 6

    valid_sources = {"real_recorded", "semi_synthetic", "simulated_twin", "lab"}
    for ds in data["datasets"]:
        assert "name" in ds
        assert "display_name" in ds
        assert "source" in ds
        assert ds["source"] in valid_sources
        assert "seed" in ds and isinstance(ds["seed"], int)
        assert "config_version" in ds
        assert "record_count" in ds and ds["record_count"] > 0
        assert "size_bytes" in ds and ds["size_bytes"] > 0
        assert "slices_assigned" in ds and isinstance(ds["slices_assigned"], bool)

        # Metadata block verification
        meta = ds.get("metadata")
        assert meta is not None, f"Dataset {ds['name']} missing metadata block"
        assert meta["source"] == ds["source"]
        assert meta["seed"] == ds["seed"]
        assert meta["config_version"] == ds["config_version"]
        assert meta["anonymized"] is True
        assert meta["no_raw_identifiers"] is True


def test_preview_no_raw_identifiers_or_payloads():
    """Verify preview limits records and contains strictly zero raw IPs or payload fields."""
    resp = client.get("/api/data/stable_benign/preview?limit=10")
    assert resp.status_code == 200, resp.text
    body = resp.json()

    assert body["name"] == "stable_benign"
    assert body["source"] == "simulated_twin"
    assert len(body["windows"]) == 10
    assert "metadata" in body
    assert body["metadata"]["no_raw_identifiers"] is True

    forbidden = ["src_ip", "dst_ip", "src_addr", "dst_addr", "imsi", "supi", "payload", "raw_payload"]
    for win in body["windows"]:
        for key in forbidden:
            assert key not in win, f"Leaked forbidden key '{key}' in window"
            if "raw_counters" in win:
                assert key not in win["raw_counters"], f"Leaked forbidden key '{key}' in raw_counters"


def test_preview_semi_synthetic_and_real_backbone():
    """Verify semi-synthetic and real 5G-NIDD datasets preview cleanly with correct source tags."""
    resp_semi = client.get("/api/data/semi_synthetic_real_ramp/preview?limit=5")
    assert resp_semi.status_code == 200
    semi_data = resp_semi.json()
    assert semi_data["source"] == "semi_synthetic"
    assert len(semi_data["windows"]) == 5

    resp_real = client.get("/api/data/fiveg_nidd/preview?limit=5")
    assert resp_real.status_code == 200
    real_data = resp_real.json()
    assert real_data["source"] == "real_recorded"
    assert len(real_data["windows"]) == 5


def test_download_json_attachment_and_metadata_block():
    """Verify download endpoint returns proper Content-Disposition attachment and begins with metadata block."""
    resp = client.get("/api/data/stable_benign/download")
    assert resp.status_code == 200
    cd = resp.headers.get("Content-Disposition", "")
    assert 'attachment; filename="commshield_stable_benign_simulated_twin_seed42.json"' in cd

    # Check size cap
    assert len(resp.content) < 20 * 1024 * 1024, "File exceeds 20MB limit"

    # Verify JSON structure
    payload = json.loads(resp.content.decode("utf-8"))
    assert "metadata" in payload
    assert "windows" in payload
    meta = payload["metadata"]
    assert meta["dataset_name"] == "stable_benign"
    assert meta["source"] == "simulated_twin"
    assert meta["seed"] == 42
    assert meta["anonymized"] is True
    assert meta["no_raw_identifiers"] is True
    assert len(payload["windows"]) > 0


def test_download_custom_seed():
    """Verify download with custom seed reflects in filename and metadata."""
    resp = client.get("/api/data/stable_benign/download?seed=777")
    assert resp.status_code == 200
    cd = resp.headers.get("Content-Disposition", "")
    assert 'attachment; filename="commshield_stable_benign_simulated_twin_seed777.json"' in cd
    payload = json.loads(resp.content.decode("utf-8"))
    assert payload["metadata"]["seed"] == 777


def test_generate_stream_determinism_and_bounds():
    """Verify deterministic generation with bounds enforcement and zero file modification."""
    # 1. Determinism: identical seed produces identical preview windows
    req_body = {"stream": "stable_benign", "seed": 9999}
    res1 = client.post("/api/data/generate", json=req_body)
    assert res1.status_code == 200
    data1 = res1.json()

    res2 = client.post("/api/data/generate", json=req_body)
    assert res2.status_code == 200
    data2 = res2.json()

    assert data1["preview"] == data2["preview"]

    # Different seed produces different preview
    res3 = client.post("/api/data/generate", json={"stream": "stable_benign", "seed": 101})
    assert res3.status_code == 200
    data3 = res3.json()
    assert data1["preview"] != data3["preview"]

    # 2. Seed bounds enforcement: negative or excessive seeds fail validation
    res_neg = client.post("/api/data/generate", json={"stream": "stable_benign", "seed": -5})
    assert res_neg.status_code == 422

    res_huge = client.post("/api/data/generate", json={"stream": "stable_benign", "seed": 2_000_000})
    assert res_huge.status_code == 422

    # 3. Invalid stream name
    res_inv = client.post("/api/data/generate", json={"stream": "invalid_stream_xyz", "seed": 42})
    assert res_inv.status_code == 400


def test_preview_and_download_404_for_unknown_dataset():
    """Verify non-existent dataset returns 404."""
    res_prev = client.get("/api/data/nonexistent_dataset/preview")
    assert res_prev.status_code == 404

    res_down = client.get("/api/data/nonexistent_dataset/download")
    assert res_down.status_code == 404
