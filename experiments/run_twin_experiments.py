"""Experiment Runner for Digital Twin Telemetry Streams.

Generates the four labelled streams:
(a) approved_onboarding
(b) unprovisioned_burst
(c) provisioned_burst_no_event
(d) slow_ramp_in_onboarding

Evaluates single-seed (tuning) and multi-seed (10 test seeds) generation.
Saves stream plots and window counts to experiments/results/twin/.
Enforces zero raw ID leakage across all output artifacts.
"""

import binascii
from datetime import datetime, timezone
import json
import math
import os
from pathlib import Path
import struct
import sys
from typing import Any, Dict, List, Optional, Tuple
import zlib

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ml_engine.provisioning.loader import ProvisioningLoader, hash_sim_id
from ml_engine.scenarios.twin_generator import (
    TwinScenarioGenerator,
    TUNING_SEED,
    TEST_SEEDS,
    STREAM_NAMES,
)

RESULTS_DIR = Path(__file__).resolve().parent / "results" / "twin"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)


# =====================================================================
# Pure-Python Standalone PNG Canvas (Zero External Dependencies)
# =====================================================================

class PurePNGCanvas:
    """Lightweight 24-bit RGB rasterizer exporting standard PNG files."""

    def __init__(self, width: int, height: int, bg_color: Tuple[int, int, int] = (255, 255, 255)):
        self.width = width
        self.height = height
        self.buffer = bytearray(width * height * 3)
        # Fill background
        r, g, b = bg_color
        for i in range(width * height):
            self.buffer[i * 3] = r
            self.buffer[i * 3 + 1] = g
            self.buffer[i * 3 + 2] = b

    def set_pixel(self, x: int, y: int, color: Tuple[int, int, int]) -> None:
        if 0 <= x < self.width and 0 <= y < self.height:
            idx = (y * self.width + x) * 3
            self.buffer[idx] = color[0]
            self.buffer[idx + 1] = color[1]
            self.buffer[idx + 2] = color[2]

    def fill_rect(self, x1: int, y1: int, x2: int, y2: int, color: Tuple[int, int, int]) -> None:
        x_start = max(0, min(x1, x2))
        x_end = min(self.width, max(x1, x2) + 1)
        y_start = max(0, min(y1, y2))
        y_end = min(self.height, max(y1, y2) + 1)
        for y in range(y_start, y_end):
            row_idx = y * self.width * 3
            for x in range(x_start, x_end):
                idx = row_idx + x * 3
                self.buffer[idx] = color[0]
                self.buffer[idx + 1] = color[1]
                self.buffer[idx + 2] = color[2]

    def draw_line(self, x0: int, y0: int, x1: int, y1: int, color: Tuple[int, int, int], thickness: int = 1) -> None:
        dx = abs(x1 - x0)
        dy = abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx - dy

        half = thickness // 2
        while True:
            for tx in range(-half, half + 1):
                for ty in range(-half, half + 1):
                    self.set_pixel(x0 + tx, y0 + ty, color)
            if x0 == x1 and y0 == y1:
                break
            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                x0 += sx
            if e2 < dx:
                err += dx
                y0 += sy

    def draw_polyline(self, points: List[Tuple[int, int]], color: Tuple[int, int, int], thickness: int = 2) -> None:
        for i in range(len(points) - 1):
            self.draw_line(points[i][0], points[i][1], points[i + 1][0], points[i + 1][1], color, thickness)

    def save(self, filepath: Path) -> None:
        raw_scanlines = bytearray()
        stride = self.width * 3
        for y in range(self.height):
            raw_scanlines.append(0)  # Filter type 0 (None)
            start = y * stride
            raw_scanlines.extend(self.buffer[start:start + stride])

        compressed_data = zlib.compress(bytes(raw_scanlines), level=6)

        def make_chunk(chunk_type: bytes, data: bytes) -> bytes:
            length = struct.pack(">I", len(data))
            chunk = chunk_type + data
            crc = struct.pack(">I", binascii.crc32(chunk) & 0xFFFFFFFF)
            return length + chunk + crc

        png_header = b"\x89PNG\r\n\x1a\n"
        ihdr_data = struct.pack(">IIBBBBB", self.width, self.height, 8, 2, 0, 0, 0)
        ihdr_chunk = make_chunk(b"IHDR", ihdr_data)
        idat_chunk = make_chunk(b"IDAT", compressed_data)
        iend_chunk = make_chunk(b"IEND", b"")

        filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, "wb") as f:
            f.write(png_header + ihdr_chunk + idat_chunk + iend_chunk)


def plot_stream_telemetry(stream_result: Dict[str, Any], output_png: Path) -> None:
    """Generate and save telemetry plot for a stream (using PurePNGCanvas)."""
    slice_windows = stream_result["slice_windows"]
    if not slice_windows:
        return

    width = 900
    height = 550
    canvas = PurePNGCanvas(width, height, bg_color=(250, 252, 255))

    # Margins and panel coordinates
    margin_l = 80
    margin_r = 50
    p1_y_top = 60
    p1_y_bot = 240
    p2_y_top = 310
    p2_y_bot = 490

    plot_w = width - margin_l - margin_r

    # Time series data
    num_pts = len(slice_windows)
    # Aggregate packets across slices per time window index
    time_indices: Dict[str, Dict[str, Any]] = {}
    for sw in slice_windows:
        w_start = sw["window_start"]
        if w_start not in time_indices:
            time_indices[w_start] = {
                "packets": 0,
                "bytes": 0,
                "is_attack": False,
                "classes": {"sensor": 0, "camera": 0, "AGV": 0},
            }
        time_indices[w_start]["packets"] += sw["raw_counters"]["total_packets"]
        time_indices[w_start]["bytes"] += (sw["raw_counters"]["total_bytes_uplink"] + sw["raw_counters"]["total_bytes_downlink"])
        if sw["ground_truth"]["is_attack"]:
            time_indices[w_start]["is_attack"] = True
        for cls_name, cnt in sw["device_count_by_class"].items():
            if cls_name in time_indices[w_start]["classes"]:
                time_indices[w_start]["classes"][cls_name] += cnt

    sorted_times = sorted(list(time_indices.keys()))
    N = max(1, len(sorted_times))

    # Determine scales
    max_packets = max(max(v["packets"] for v in time_indices.values()), 100)
    max_devices = max(max(sum(v["classes"].values()) for v in time_indices.values()), 10)

    # Draw shaded attack intervals
    for idx, t in enumerate(sorted_times):
        info = time_indices[t]
        x1 = margin_l + int((idx / float(N)) * plot_w)
        x2 = margin_l + int(((idx + 1) / float(N)) * plot_w)
        if info["is_attack"]:
            canvas.fill_rect(x1, p1_y_top, x2, p1_y_bot, (255, 225, 225))  # Light red
            canvas.fill_rect(x1, p2_y_top, x2, p2_y_bot, (255, 225, 225))
        else:
            canvas.fill_rect(x1, p1_y_top, x2, p1_y_bot, (235, 245, 235))  # Light green
            canvas.fill_rect(x1, p2_y_top, x2, p2_y_bot, (235, 245, 235))

    # Draw panel borders and axes
    canvas.draw_line(margin_l, p1_y_top, margin_l, p1_y_bot, (160, 160, 160), 2)
    canvas.draw_line(margin_l, p1_y_bot, margin_l + plot_w, p1_y_bot, (160, 160, 160), 2)
    canvas.draw_line(margin_l, p2_y_top, margin_l, p2_y_bot, (160, 160, 160), 2)
    canvas.draw_line(margin_l, p2_y_bot, margin_l + plot_w, p2_y_bot, (160, 160, 160), 2)

    # Panel 1: Aggregate Packet Rate Curve
    packet_points = []
    for idx, t in enumerate(sorted_times):
        pkts = time_indices[t]["packets"]
        x = margin_l + int((idx / float(max(1, N - 1))) * plot_w)
        y = p1_y_bot - int((pkts / float(max_packets)) * (p1_y_bot - p1_y_top))
        packet_points.append((x, y))

    canvas.draw_polyline(packet_points, color=(30, 90, 200), thickness=3)

    # Panel 2: Device Counts by Class
    sensor_pts = []
    camera_pts = []
    agv_pts = []
    for idx, t in enumerate(sorted_times):
        classes = time_indices[t]["classes"]
        x = margin_l + int((idx / float(max(1, N - 1))) * plot_w)
        y_sensor = p2_y_bot - int((classes["sensor"] / float(max_devices)) * (p2_y_bot - p2_y_top))
        y_camera = p2_y_bot - int((classes["camera"] / float(max_devices)) * (p2_y_bot - p2_y_top))
        y_agv = p2_y_bot - int((classes["AGV"] / float(max_devices)) * (p2_y_bot - p2_y_top))

        sensor_pts.append((x, y_sensor))
        camera_pts.append((x, y_camera))
        agv_pts.append((x, y_agv))

    canvas.draw_polyline(sensor_pts, color=(40, 160, 60), thickness=2)    # Green for Sensor
    canvas.draw_polyline(camera_pts, color=(220, 100, 20), thickness=2)   # Orange for Camera
    canvas.draw_polyline(agv_pts, color=(140, 40, 180), thickness=2)     # Purple for AGV

    canvas.save(output_png)


# =====================================================================
# Main Experiment Execution and Artifact Auditing
# =====================================================================

def run_twin_experiments():
    print("=" * 70)
    print("CommShield Digital Twin Telemetry Streams Benchmark")
    print(f"Timestamp : {datetime.now(timezone.utc).isoformat()}")
    print(f"Tuning Seed : {TUNING_SEED}")
    print(f"Test Seeds  : {TEST_SEEDS} (Count: {len(TEST_SEEDS)})")
    print("=" * 70)

    loader = ProvisioningLoader()

    # 1. Tuning Runs (Seed 42)
    generator_tuning = TwinScenarioGenerator(seed=TUNING_SEED, loader=loader)
    tuning_results: Dict[str, Any] = {}

    stream_window_counts: Dict[str, Any] = {}
    aggregate_device_counts = {"sensor": 0, "camera": 0, "AGV": 0}

    total_slice_windows = 0
    total_device_windows = 0
    total_benign_windows = 0
    total_attack_windows = 0

    for stream_name in STREAM_NAMES:
        res = generator_tuning.generate_stream(stream_name=stream_name, num_windows=30)
        tuning_results[stream_name] = res

        plot_file = RESULTS_DIR / f"{stream_name}.png"
        plot_stream_telemetry(res, plot_file)
        print(f"  ✓ Saved stream plot: {plot_file.name}")

        counts = res["counts"]
        dev_by_class = counts["device_by_class"]
        for cls_name, c in dev_by_class.items():
            aggregate_device_counts[cls_name] += c

        total_slice_windows += res["total_slice_windows"]
        total_device_windows += res["total_device_windows"]
        total_benign_windows += (counts["slice_benign"] + counts["device_benign"])
        total_attack_windows += (counts["slice_attack"] + counts["device_attack"])

        stream_window_counts[stream_name] = {
            "slice_windows": res["total_slice_windows"],
            "device_windows": res["total_device_windows"],
            "slice_benign": counts["slice_benign"],
            "slice_attack": counts["slice_attack"],
            "device_benign": counts["device_benign"],
            "device_attack": counts["device_attack"],
            "device_by_class": dev_by_class,
        }

    # Record window counts file
    window_counts_artifact = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "tuning_seed": TUNING_SEED,
        "total_streams": len(STREAM_NAMES),
        "total_slice_windows": total_slice_windows,
        "total_device_windows": total_device_windows,
        "total_windows_all": total_slice_windows + total_device_windows,
        "total_benign_windows": total_benign_windows,
        "total_attack_windows": total_attack_windows,
        "aggregate_device_counts": aggregate_device_counts,
        "streams": stream_window_counts,
    }

    counts_path = RESULTS_DIR / "window_counts.json"
    with open(counts_path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(window_counts_artifact, f, indent=2)
    print(f"  ✓ Saved window counts to: {counts_path.name}")

    # 2. Multi-Seed Test Evaluation (10 Test Seeds)
    print("\nRunning Multi-Seed Test Evaluation Across 10 Test Seeds...")
    multi_seed_results: Dict[int, Dict[str, Any]] = {}

    for t_seed in TEST_SEEDS:
        gen = TwinScenarioGenerator(seed=t_seed, loader=loader)
        seed_summary: Dict[str, Any] = {}
        for stream_name in STREAM_NAMES:
            res = gen.generate_stream(stream_name=stream_name, num_windows=30)
            seed_summary[stream_name] = {
                "slice_windows": res["total_slice_windows"],
                "device_windows": res["total_device_windows"],
                "slice_attack": res["counts"]["slice_attack"],
                "device_attack": res["counts"]["device_attack"],
            }
        multi_seed_results[t_seed] = seed_summary

    summary_artifact = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "tuning_seed": TUNING_SEED,
        "test_seeds": TEST_SEEDS,
        "tuning_stream_counts": stream_window_counts,
        "multi_seed_test_runs": multi_seed_results,
    }

    summary_path = RESULTS_DIR / "twin_summary.json"
    with open(summary_path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(summary_artifact, f, indent=2)
    print(f"  ✓ Saved multi-seed test summary to: {summary_path.name}")

    # 3. Privacy Audit: Ensure zero raw SIM IDs exist in any generated artifacts
    prov_file = Path(__file__).resolve().parent.parent / "data" / "twin" / "provisioning.json"
    with open(prov_file, "r", encoding="utf-8", newline="\n") as f:
        raw_sims = [sim["sim_id"] for sim in json.load(f)["sims"]]

    for json_file in RESULTS_DIR.glob("*.json"):
        with open(json_file, "r", encoding="utf-8", newline="\n") as f:
            content = f.read()
            for raw_sim in raw_sims:
                if raw_sim in content:
                    raise ValueError(f"CRITICAL PRIVACY VIOLATION: Raw SIM ID {raw_sim} leaked in {json_file}")

    print("\n  ✓ Privacy Verification Passed: ZERO raw SIM IDs found in results artifacts.")
    print("=" * 70)
    print(f"Summary Window Counts per Device Class:")
    print(f"  sensor : {aggregate_device_counts['sensor']} windows")
    print(f"  camera : {aggregate_device_counts['camera']} windows")
    print(f"  AGV    : {aggregate_device_counts['AGV']} windows")
    print(f"Total Device Windows : {total_device_windows}")
    print(f"Total Slice Windows  : {total_slice_windows}")
    print("=" * 70)


if __name__ == "__main__":
    run_twin_experiments()
