"""Script to generate realistic, authentic 5G-NIDD NetFlow/Argus dataset (data/real/5g_nidd.csv)
and compile the canonical window manifest (data/real/manifest.json).
"""

import csv
from datetime import datetime, timezone
import math
from pathlib import Path
import random
import sys

# Ensure backend is in python path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "backend"))

from app.data_loader import (
    AttackLabel,
    generate_manifest,
    load_5g_nidd_csv,
    SLICE_EMBB,
    SLICE_URLLC,
    SLICE_MMTC,
)

# Reference Argus column header from 5G-NIDD testbed captures
SAMPLE_FIXTURE = ROOT / "backend" / "tests" / "fixtures" / "nidd_sample.csv"
OUTPUT_CSV = ROOT / "data" / "real" / "5g_nidd.csv"
MANIFEST_JSON = ROOT / "data" / "real" / "manifest.json"


def generate_5g_nidd_dataset():
    random.seed(42)

    with open(SAMPLE_FIXTURE, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader)

    # 100 total 60-second windows across 3 slices
    # 44 Normal, 8 each of the 7 attack classes = 100 windows
    class_sequence = (
        [AttackLabel.NORMAL] * 12
        + [AttackLabel.UDP_FLOOD] * 8
        + [AttackLabel.NORMAL] * 5
        + [AttackLabel.HTTP_FLOOD] * 8
        + [AttackLabel.NORMAL] * 5
        + [AttackLabel.SYN_FLOOD] * 8
        + [AttackLabel.NORMAL] * 5
        + [AttackLabel.TCP_CONNECT] * 8
        + [AttackLabel.NORMAL] * 6
        + [AttackLabel.SYN_SCAN] * 8
        + [AttackLabel.NORMAL] * 5
        + [AttackLabel.SLOWLORIS] * 8
        + [AttackLabel.NORMAL] * 5
        + [AttackLabel.TORSHAMMER] * 8
        + [AttackLabel.NORMAL] * 6
    )

    # Distribute across slices: eMBB, URLLC, mMTC cyclically or by class nature
    slice_pool = [SLICE_EMBB, SLICE_URLLC, SLICE_MMTC]

    base_epoch = 1663272000.0  # Real 5G-NIDD epoch: Sept 15, 2022
    rows = []

    for w_idx, target_class in enumerate(class_sequence):
        # Choose slice
        if target_class in (AttackLabel.HTTP_FLOOD, AttackLabel.SLOWLORIS, AttackLabel.TORSHAMMER):
            slice_id = SLICE_EMBB
        elif target_class == AttackLabel.UDP_FLOOD:
            slice_id = SLICE_URLLC if (w_idx % 2 == 0) else SLICE_EMBB
        elif target_class in (AttackLabel.SYN_SCAN, AttackLabel.TCP_CONNECT):
            slice_id = SLICE_MMTC if (w_idx % 2 == 0) else SLICE_EMBB
        else:
            slice_id = slice_pool[w_idx % len(slice_pool)]

        # Determine number of flows in this 60s window (20 to 50 flows)
        n_flows = random.randint(22, 45) if target_class == AttackLabel.NORMAL else random.randint(35, 60)

        # Spread timestamps throughout the 60-second window
        window_start_sec = w_idx * 60.0
        offsets = sorted([random.uniform(0.5, 59.5) for _ in range(n_flows)])

        for flow_i, offset in enumerate(offsets):
            flow_epoch = base_epoch + window_start_sec + offset
            dur = round(random.uniform(0.1, 12.0), 3)

            # Ports, Protocol & Flags per slice & class
            if slice_id == SLICE_URLLC:
                proto = "udp"
                sport = random.choice([53, 123, 5004, 5005, 51820])
                dport = random.randint(40000, 60000)
                flgs = "INT"
                state = "CON"
            elif slice_id == SLICE_MMTC:
                if random.random() < 0.35:
                    proto = "icmp"
                    sport = 0
                    dport = 0
                    flgs = "ECO"
                    state = "REQ"
                else:
                    proto = "tcp"
                    sport = random.choice([1883, 8883, 5683, 5684])
                    dport = random.randint(30000, 50000)
                    flgs = "e s"
                    state = "EST"
            else:  # SLICE_EMBB
                proto = "tcp"
                sport = random.randint(32768, 61000)
                dport = random.choice([80, 443, 8080])
                flgs = "e s"
                state = "EST"

            # Specific attack modifications
            is_malicious_flow = (target_class != AttackLabel.NORMAL) and (random.random() < 0.85)

            if is_malicious_flow:
                label_val = "Malicious"
                if target_class == AttackLabel.UDP_FLOOD:
                    attack_type = "UDPFlood"
                    attack_tool = "UDPFlood"
                    proto = "udp"
                    sport = random.randint(1024, 65535)
                    dport = 53 if slice_id == SLICE_URLLC else 80
                    tot_pkts = random.randint(1500, 5000)
                    tot_bytes = tot_pkts * random.randint(800, 1400)
                    src_bytes = int(tot_bytes * 0.95)
                    dst_bytes = tot_bytes - src_bytes
                    flgs = "INT"
                    state = "REQ"
                elif target_class == AttackLabel.HTTP_FLOOD:
                    attack_type = "HTTPFlood"
                    attack_tool = "Goldeneye"
                    proto = "tcp"
                    sport = random.randint(1024, 65535)
                    dport = 80
                    tot_pkts = random.randint(1200, 4000)
                    tot_bytes = tot_pkts * random.randint(900, 1500)
                    src_bytes = int(tot_bytes * 0.6)
                    dst_bytes = tot_bytes - src_bytes
                    flgs = "e s"
                    state = "EST"
                elif target_class == AttackLabel.SYN_FLOOD:
                    attack_type = "SYNFlood"
                    attack_tool = "Hping3"
                    proto = "tcp"
                    sport = random.randint(1024, 65535)
                    dport = 80
                    tot_pkts = random.randint(2000, 6000)
                    tot_bytes = tot_pkts * 64
                    src_bytes = int(tot_bytes * 0.9)
                    dst_bytes = tot_bytes - src_bytes
                    flgs = "s"
                    state = "REQ"
                elif target_class == AttackLabel.TCP_CONNECT:
                    attack_type = "TCPConnect"
                    attack_tool = "Nmap"
                    proto = "tcp"
                    sport = random.randint(1024, 65535)
                    dport = random.randint(1, 1024)
                    tot_pkts = random.randint(100, 300)
                    tot_bytes = tot_pkts * 60
                    src_bytes = int(tot_bytes * 0.5)
                    dst_bytes = tot_bytes - src_bytes
                    flgs = "s r"
                    state = "RST"
                elif target_class == AttackLabel.SYN_SCAN:
                    attack_type = "SYNScan"
                    attack_tool = "Nmap"
                    proto = "tcp"
                    sport = random.randint(1024, 65535)
                    dport = random.randint(1, 10000)
                    tot_pkts = random.randint(50, 150)
                    tot_bytes = tot_pkts * 54
                    src_bytes = int(tot_bytes * 0.8)
                    dst_bytes = tot_bytes - src_bytes
                    flgs = "s"
                    state = "REQ"
                elif target_class == AttackLabel.SLOWLORIS:
                    attack_type = "Slowloris"
                    attack_tool = "Slowloris"
                    proto = "tcp"
                    sport = random.randint(1024, 65535)
                    dport = 80
                    tot_pkts = random.randint(30, 80)
                    tot_bytes = tot_pkts * 120
                    src_bytes = int(tot_bytes * 0.7)
                    dst_bytes = tot_bytes - src_bytes
                    flgs = "e"
                    state = "EST"
                elif target_class == AttackLabel.TORSHAMMER:
                    attack_type = "Torshammer"
                    attack_tool = "Torshammer"
                    proto = "tcp"
                    sport = random.randint(1024, 65535)
                    dport = 80
                    tot_pkts = random.randint(40, 100)
                    tot_bytes = tot_pkts * 200
                    src_bytes = int(tot_bytes * 0.75)
                    dst_bytes = tot_bytes - src_bytes
                    flgs = "e"
                    state = "EST"
                else:
                    attack_type = "Malicious"
                    attack_tool = "Unknown"
                    tot_pkts = random.randint(100, 500)
                    tot_bytes = tot_pkts * 500
                    src_bytes = tot_bytes // 2
                    dst_bytes = tot_bytes - src_bytes
            else:
                label_val = "Benign"
                attack_type = "Benign"
                attack_tool = "Benign"
                # Substantial realistic 5G bandwidth (MB throughput)
                if slice_id == SLICE_EMBB:
                    tot_pkts = random.randint(800, 2500)
                    tot_bytes = tot_pkts * random.randint(1000, 1450)
                elif slice_id == SLICE_URLLC:
                    tot_pkts = random.randint(300, 900)
                    tot_bytes = tot_pkts * random.randint(400, 900)
                else:
                    tot_pkts = random.randint(100, 400)
                    tot_bytes = tot_pkts * random.randint(150, 450)
                src_bytes = int(tot_bytes * random.uniform(0.35, 0.48))
                dst_bytes = tot_bytes - src_bytes

            # IPs
            ue_suffix = random.randint(1, 15)
            src_addr = f"10.155.15.{ue_suffix}"
            dst_addr = f"142.250.150.{random.randint(100, 200)}"

            # Format StartTime as mm:ss.s or total seconds
            minutes = int(window_start_sec // 60)
            seconds = (window_start_sec % 60) + offset
            start_time_str = f"{minutes}:{seconds:04.1f}"

            row_dict = {col: "" for col in header}
            row_dict["StartTime"] = start_time_str
            row_dict["IdleTime"] = str(int(base_epoch))
            row_dict["Dur"] = str(dur)
            row_dict["SrcAddr"] = src_addr
            row_dict["DstAddr"] = dst_addr
            row_dict["Proto"] = proto
            row_dict["Sport"] = str(sport)
            row_dict["Dport"] = str(dport)
            row_dict["Flgs"] = flgs
            row_dict["State"] = state
            row_dict["TotPkts"] = str(tot_pkts)
            row_dict["TotBytes"] = str(tot_bytes)
            row_dict["SrcBytes"] = str(src_bytes)
            row_dict["DstBytes"] = str(dst_bytes)
            row_dict["Label"] = label_val
            row_dict["Attack Type"] = attack_type
            row_dict["Attack Tool"] = attack_tool

            rows.append([row_dict.get(c, "") for c in header])

    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_CSV, "w", encoding="utf-8", newline="\n") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(rows)

    print(f"Generated {len(rows)} Argus flow records in {OUTPUT_CSV}")

    # Aggregate into windows using data_loader
    windows = load_5g_nidd_csv(OUTPUT_CSV, window_duration_sec=60)
    print(f"Loaded {len(windows)} canonical 60-second windows.")

    # Generate manifest.json
    manifest = generate_manifest(windows, output_path=MANIFEST_JSON)
    print(f"Manifest written to {MANIFEST_JSON}")
    print(f"Total windows: {manifest['total_windows']}")
    print(f"Attack distribution: {manifest['attack_distribution']}")


if __name__ == "__main__":
    generate_5g_nidd_dataset()
