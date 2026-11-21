#!/usr/bin/env python3
"""CommShield Demo and Results Verification Tool.

Starts the CommShield backend server, invokes the presentation demo and result
endpoints, verifies that every displayed number appears in a saved result JSON,
checks that no badge displays 'Live lab' unless data/lab/windows.jsonl validates,
and reports PASS/FAIL per check.

Usage:
  python tools/demo_check.py
"""

import json
from pathlib import Path
import platform
import socket
import subprocess
import sys
import time
from typing import Any, Dict, List, Set, Tuple
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parent.parent


def find_free_port() -> int:
    """Find an available TCP port on localhost."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def get_python_executable() -> str:
    """Find appropriate Python interpreter for running uvicorn backend."""
    candidates = [
        ROOT / "backend" / "venv" / "bin" / "python",
        ROOT / "backend" / "venv" / "Scripts" / "python.exe",
        Path(sys.executable),
    ]
    for c in candidates:
        if c.is_file():
            return str(c)
    return sys.executable


def http_get_json(url: str, timeout: float = 10.0) -> Tuple[int, Any]:
    """Perform HTTP GET and return (status_code, parsed_json_or_text)."""
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = resp.read().decode("utf-8")
            return resp.status, json.loads(data)
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8")
    except Exception as e:
        return 0, str(e)


def collect_numbers_from_result_jsons(root: Path) -> Set[float]:
    """Recursively collect all numeric values from persisted result JSON files."""
    numbers: Set[float] = set()

    def _extract(val: Any) -> None:
        if isinstance(val, (int, float)) and not isinstance(val, bool):
            numbers.add(round(float(val), 4))
        elif isinstance(val, dict):
            for v in val.values():
                _extract(v)
        elif isinstance(val, list):
            for item in val:
                _extract(item)

    # Key result files
    target_patterns = [
        root / "experiments" / "results" / "twin" / "three_arm_twin_summary.json",
        root / "experiments" / "results" / "twin" / "window_counts.json",
        root / "data" / "twin" / "provisioning.json",
        root / "data" / "twin" / "change_events.json",
        root / "experiments" / "results" / "three_arm_summary.json",
        root / "experiments" / "results" / "experiment_summary.json",
        root / "experiments" / "results" / "device_model" / "conformal_evaluation.json",
        root / "experiments" / "results" / "attribution" / "learned_vs_rules_summary.json",
    ]

    for p in target_patterns:
        if p.is_file():
            try:
                content = json.loads(p.read_text(encoding="utf-8"))
                _extract(content)
            except Exception as e:
                print(f"  [WARN] Failed to parse {p.name}: {e}")

    # Also glob all other result JSONs and JSONL files
    for p in root.glob("experiments/results/**/*.json"):
        if p.is_file():
            try:
                _extract(json.loads(p.read_text(encoding="utf-8")))
            except Exception:
                pass

    for p in [root / "data" / "lab" / "windows.jsonl"]:
        if p.is_file():
            try:
                with open(p, "r", encoding="utf-8", newline="\n") as f:
                    for line in f:
                        if line.strip():
                            _extract(json.loads(line))
            except Exception:
                pass

    return numbers


def check_lab_validated_directly(root: Path) -> bool:
    """Check if data/lab/windows.jsonl exists and validates against schema."""
    lab_file = root / "data" / "lab" / "windows.jsonl"
    if not lab_file.is_file():
        return False
    try:
        if str(root) not in sys.path:
            sys.path.insert(0, str(root))
        from ml_engine.provisioning.schema import validate_window
        with open(lab_file, "r", encoding="utf-8", newline="\n") as f:
            lines = [l.strip() for l in f if l.strip()]
            if not lines:
                return False
            for line in lines:
                w = json.loads(line)
                validate_window(w)
        return True
    except Exception:
        return False


def run_checks() -> int:
    """Execute full suite of demo and result verification checks."""
    print("=" * 75)
    print("CommShield Demo & Result Endpoint Verification (tools/demo_check.py)")
    print("=" * 75)

    py_exe = get_python_executable()
    port = find_free_port()
    base_url = f"http://127.0.0.1:{port}"

    passed = 0
    failed = 0

    def record(name: str, success: bool, detail: str = ""):
        nonlocal passed, failed
        if success:
            passed += 1
            print(f"PASS: {name}{' - ' + detail if detail else ''}")
        else:
            failed += 1
            print(f"FAIL: {name}{' - ' + detail if detail else ''}")

    # 1. Start Backend Subprocess
    cmd = [
        py_exe,
        "-m",
        "uvicorn",
        "backend.app.main:app",
        "--host",
        "127.0.0.1",
        "--port",
        str(port),
        "--log-level",
        "warning",
    ]

    print(f"Starting backend on {base_url} using {py_exe}...")
    proc = subprocess.Popen(cmd, cwd=str(ROOT))

    try:
        # Wait for health check
        healthy = False
        health_url = f"{base_url}/api/health"
        for _ in range(30):
            time.sleep(0.5)
            status, data = http_get_json(health_url, timeout=1.0)
            if status == 200 and isinstance(data, dict) and data.get("status") == "ok":
                healthy = True
                break

        record("Backend startup & health check", healthy, f"Responsive at {health_url}")
        if not healthy:
            print("ERROR: Backend did not start in time. Aborting remaining checks.")
            return 1

        # 2. Check Demo Scenarios Endpoint
        demo_url = f"{base_url}/api/demo/scenarios"
        status, demo_data = http_get_json(demo_url)
        is_demo_ok = (status == 200 and isinstance(demo_data, dict) and "scenarios" in demo_data)
        record("GET /api/demo/scenarios status 200", is_demo_ok)

        scenarios = demo_data.get("scenarios", []) if is_demo_ok else []
        has_4_scenes = (len(scenarios) == 4)
        record("Demo scenario count is exactly 4", has_4_scenes, f"Found {len(scenarios)} scenes")

        # Scene Order Check
        expected_order = ["baseline", "approved_onboarding", "unprovisioned_device", "hidden_ramp"]
        actual_order = [s.get("id") for s in scenarios]
        order_ok = (actual_order == expected_order)
        record(
            "Demo scenes strictly ordered: (1) baseline, (2) approved onboarding, (3) unprovisioned, (4) hidden ramp",
            order_ok,
            f"Order: {actual_order}",
        )

        # Check key events and captions
        all_captions_valid = True
        for sc in scenarios:
            events = sc.get("key_events", [])
            if not events:
                all_captions_valid = False
            for ev in events:
                caption = ev.get("caption", "")
                if not caption or "\n" in caption.strip() or len(caption) < 10:
                    all_captions_valid = False
        record("All demo key events contain single-line human-readable captions", all_captions_valid)

        # 3. Check Result Endpoints (Digital Twin across all 4 scenarios & Experiments)
        twin_streams = [
            "approved_onboarding",
            "unprovisioned_burst",
            "provisioned_burst_no_event",
            "slow_ramp_in_onboarding",
        ]
        twin_data_map: Dict[str, Any] = {}
        all_twin_ok = True

        for st in twin_streams:
            st_url = f"{base_url}/api/digital-twin?scenario={st}&time_step=15"
            t_status, t_data = http_get_json(st_url)
            if t_status == 200 and isinstance(t_data, dict) and "topology" in t_data:
                twin_data_map[st] = t_data
            else:
                all_twin_ok = False
        record("GET /api/digital-twin responsive across all 4 streams", all_twin_ok)

        # Experiments results endpoint
        exp_url = f"{base_url}/api/experiments/results?data_source=synthetic"
        exp_status, exp_data = http_get_json(exp_url)
        exp_ok = (exp_status == 200 and isinstance(exp_data, dict))
        record("GET /api/experiments/results responsive", exp_ok)

        # 4. Check Displayed Numbers Appear in Result JSONs
        known_numbers = collect_numbers_from_result_jsons(ROOT)
        print(f"Collected {len(known_numbers)} verified numerical figures from result JSON files.")

        displayed_numbers: Set[float] = set()

        # Extract displayed numbers from demo scenarios
        for sc in scenarios:
            summary = sc.get("three_arm_summary")
            if summary and "arms" in summary:
                for arm in summary["arms"].values():
                    if "contamination" in arm:
                        displayed_numbers.add(round(float(arm["contamination"]), 4))
                    if "fpr" in arm:
                        displayed_numbers.add(round(float(arm["fpr"]), 4))
                    if "adaptations" in arm:
                        displayed_numbers.add(round(float(arm["adaptations"]), 4))

        # Extract displayed numbers from digital twin endpoints
        for st, tw in twin_data_map.items():
            card = tw.get("provisioning_card", {})
            if "total_catalog_sims" in card:
                displayed_numbers.add(round(float(card["total_catalog_sims"]), 4))
            if "total_batches" in card:
                displayed_numbers.add(round(float(card["total_batches"]), 4))
            if "provisioned_share" in card:
                displayed_numbers.add(round(float(card["provisioned_share"]), 4))

            meters = tw.get("contamination_meters", {})
            for m in meters.values():
                if "contamination_mean" in m:
                    displayed_numbers.add(round(float(m["contamination_mean"]), 4))
                if "fpr_mean" in m:
                    displayed_numbers.add(round(float(m["fpr_mean"]), 4))
                if "onboardings_adapted" in m:
                    displayed_numbers.add(round(float(m["onboardings_adapted"]), 4))

            ref = tw.get("saved_metrics_reference", {})
            for k in ["aggregate_windows", "device_windows", "slice_windows"]:
                if k in ref:
                    displayed_numbers.add(round(float(ref[k]), 4))

        unmatched = [n for n in displayed_numbers if n not in known_numbers]
        numbers_valid = (len(unmatched) == 0 and len(displayed_numbers) > 0)
        record(
            "Every displayed number in demo & twin endpoints appears in saved result JSONs",
            numbers_valid,
            f"Verified {len(displayed_numbers)} numbers (unmatched: {unmatched})",
        )

        # 5. Check 'Live lab' Badge Rule
        # Rule: No badge says 'Live lab' unless data/lab/windows.jsonl validates
        lab_valid = check_lab_validated_directly(ROOT)
        badges_compliant = True
        violation_reason = ""

        # In demo scenarios:
        for sc in scenarios:
            badge = sc.get("source_badge", "")
            src = sc.get("source", "")
            if src == "simulated_twin" and badge == "Live lab":
                badges_compliant = False
                violation_reason = f"Scene {sc.get('id')} has source='simulated_twin' but badge='Live lab'"
            if badge == "Live lab" and not lab_valid:
                badges_compliant = False
                violation_reason = f"Scene {sc.get('id')} displays 'Live lab' but lab file is not validated"

        # In digital twin responses:
        for st, tw in twin_data_map.items():
            badge = tw.get("source_badge", "")
            src = tw.get("source", "")
            if src == "simulated_twin" and badge == "Live lab":
                badges_compliant = False
                violation_reason = f"Twin stream {st} has source='simulated_twin' but badge='Live lab'"
            if badge == "Live lab" and not lab_valid:
                badges_compliant = False
                violation_reason = f"Twin stream {st} displays 'Live lab' but lab file is not validated"

        # Explicit check with ?source=simulated_twin
        sim_url = f"{base_url}/api/digital-twin?source=simulated_twin"
        sim_st, sim_data = http_get_json(sim_url)
        if sim_st == 200 and sim_data.get("source_badge") == "Live lab":
            badges_compliant = False
            violation_reason = "Endpoint returned 'Live lab' when explicitly querying source=simulated_twin"

        record(
            "No badge says 'Live lab' unless lab file validates against canonical schema",
            badges_compliant,
            violation_reason if not badges_compliant else f"Lab validated={lab_valid}, badges strictly compliant",
        )

    finally:
        # 6. Terminate Subprocess
        print("Terminating backend process...")
        proc.terminate()
        try:
            proc.wait(timeout=5.0)
            record("Backend process terminated cleanly", True)
        except subprocess.TimeoutExpired:
            proc.kill()
            record("Backend process killed after timeout", True)

    print("=" * 75)
    print(f"Summary: {passed} PASSED, {failed} FAILED")
    print("=" * 75)

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(run_checks())
