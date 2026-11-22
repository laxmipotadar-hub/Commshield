#!/usr/bin/env bash
# CommShield Open5GS and UERANSIM Lab Environment Setup Script
#
# NOTE: This script is exclusively for live Linux lab host setup.
# Nothing outside lab/ depends on this script.
# On Windows and CI systems without root/SCTP access, the adapter
# executes fully offline on sample logs in lab/sample_logs/.

set -euo pipefail

echo "================================================================="
echo "CommShield 5G Lab Testbed Setup (Open5GS + UERANSIM)"
echo "================================================================="

# 1. Check OS
if [[ "$(uname -s)" != "Linux" ]]; then
    echo "Notice: Live Open5GS kernel daemons require Linux. On Windows, use offline replay:"
    echo "  python -m lab.adapter"
    echo "  python -m lab.validate data\\lab\\windows.jsonl"
    exit 0
fi

# 2. Open5GS Installation (Ubuntu 22.04 / 24.04 LTS)
echo "[1/4] Installing Open5GS repository and packages..."
if command -v apt-get &> /dev/null; then
    sudo apt-get update -y
    sudo apt-get install -y software-properties-common curl
    sudo add-apt-repository -y ppa:open5gs/latest || true
    sudo apt-get update -y
    sudo apt-get install -y open5gs || echo "Open5GS package installation skipped (requires root)."
fi

# 3. TUN Interface Setup for UPF (ogstun)
echo "[2/4] Configuring 5G Core TUN interface (ogstun)..."
if command -v ip &> /dev/null; then
    sudo ip tuntap add name ogstun mode tun || true
    sudo ip addr add 10.45.0.1/16 dev ogstun || true
    sudo ip link set ogstun up || true
fi

# 4. UERANSIM Build Dependencies
echo "[3/4] Checking UERANSIM prerequisites..."
if command -v apt-get &> /dev/null; then
    sudo apt-get install -y make gcc g++ libsctp-dev lksctp-tools iproute2 cmake || true
fi

# 5. Telemetry Capture Hook
echo "[4/4] Verifying telemetry capture directory..."
mkdir -p lab/sample_logs
mkdir -p data/lab

echo "================================================================="
echo "Lab setup script finished. To run the adapter offline on sample logs:"
echo "  python3 -m lab.adapter"
echo "  python3 -m lab.validate data/lab/windows.jsonl"
echo "================================================================="
# CommShield AI Core
