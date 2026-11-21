#!/usr/bin/env python3
"""
verify_frontend_numbers.py
Audits frontend source code to ensure that mockup numbers and hardcoded telemetry
from the Stitch design exports are not statically embedded into the production UI.
"""
from pathlib import Path
import sys

# Disallowed hardcoded mockup numbers/strings from the Stitch export mockups
MOCKUP_PATTERNS = [
    "48.2 Gbps",
    "148.6 TB",
    "4,829,140",
    "1 - β = 0.992",
    "1 - \\u03b2 = 0.992",
    "42.8 Mbps",
    "0.18 nats",
    "4.82 (0.12)",
    "3.4σ",
    "3.4\\u03c3",
    "0.001%",
    "UPF-EDGE-09",
    "ENCLAVE 04",
    "Sarah Jenkins",
    "INC-2024-8842",
]

FRONTEND_SRC = Path(__file__).resolve().parent.parent / "frontend" / "src"

def check_files():
    violations = []
    files_checked = 0

    if not FRONTEND_SRC.exists():
        print(f"Error: {FRONTEND_SRC} does not exist.")
        sys.exit(1)

    for ext in ("*.tsx", "*.ts"):
        for filepath in FRONTEND_SRC.rglob(ext):
            files_checked += 1
            content = filepath.read_text(encoding="utf-8")
            for pattern in MOCKUP_PATTERNS:
                if pattern in content:
                    violations.append((filepath.relative_to(FRONTEND_SRC.parent), pattern))

    print(f"Checked {files_checked} frontend source files in {FRONTEND_SRC}")
    if violations:
        print(f"FAILED: Found {len(violations)} unsourced mockup patterns:")
        for file_rel, pat in violations:
            print(f"  - {file_rel}: contains forbidden mockup literal '{pat}'")
        return False
    else:
        print("PASSED: Zero unsourced mockup literals found in frontend source code.")
        return True

if __name__ == "__main__":
    success = check_files()
    sys.exit(0 if success else 1)
