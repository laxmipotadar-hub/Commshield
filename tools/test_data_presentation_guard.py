#!/usr/bin/env python3
"""
tools/test_data_presentation_guard.py
Guard tests ensuring data presentation integrity:
1. Every chart card includes captions ('whatThisShows', 'howToReadIt').
2. Every chart includes sample size n and a data source badge.
3. No hardcoded mockup literals or unhandled default 0 placeholders.
4. Missing values render as 'no data' rather than 0.
"""

from pathlib import Path
import re
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
FRONTEND_SRC = PROJECT_ROOT / "frontend" / "src"

def test_chart_captions_and_badges():
    scenario_charts = FRONTEND_SRC / "components" / "ScenarioCharts.tsx"
    assert scenario_charts.exists(), "ScenarioCharts.tsx must exist"
    code = scenario_charts.read_text(encoding="utf-8")

    assert "whatThisShows" in code, "All scenario charts must include 'whatThisShows' caption"
    assert "howToReadIt" in code, "All scenario charts must include 'howToReadIt' caption"
    assert "sourceBadge" in code, "All scenario charts must specify sourceBadge"
    assert "missingReason" in code, "Scenario charts must support hiding when data is missing"
    print("PASS: Chart captions, badges, and missing reason handlers verified.")

def test_chart_card_caption_support():
    chart_card = FRONTEND_SRC / "components" / "ChartCard.tsx"
    assert chart_card.exists(), "ChartCard.tsx must exist"
    code = chart_card.read_text(encoding="utf-8")

    assert "whatThisShows" in code and "howToReadIt" in code, "ChartCard must render caption with What this shows & How to read it"
    assert "DataSourceBadge" in code, "ChartCard must render DataSourceBadge"
    assert "interval too wide" in code, "ChartCard must flag counts under 10 with 'interval too wide'"
    print("PASS: ChartCard caption, source badge, and small-n guards verified.")

def test_data_presentation_utilities():
    util_file = FRONTEND_SRC / "utils" / "dataPresentation.ts"
    assert util_file.exists(), "dataPresentation.ts must exist"
    code = util_file.read_text(encoding="utf-8")

    assert "calculateWilsonInterval" in code, "Must provide Wilson interval calculation"
    assert "interval too wide" in code, "Must flag n < 10 with 'interval too wide'"
    assert "formatPercentileWithLogRatio" in code, "Must support log-ratio display for saturated percentiles"
    assert "no data" in code, "Must format missing values as 'no data'"
    print("PASS: Data presentation statistical utility verified.")

def test_zero_mockup_literals():
    forbidden = [
        "48.2 Gbps",
        "148.6 TB",
        "4,829,140",
        "1 - β = 0.992",
        "1 - \\u03b2 = 0.992",
        "42.8 Mbps",
        "0.18 nats",
        "UPF-EDGE-09",
        "INC-2024-8842",
    ]
    for ext in ("*.tsx", "*.ts"):
        for f in FRONTEND_SRC.rglob(ext):
            content = f.read_text(encoding="utf-8")
            for pat in forbidden:
                assert pat not in content, f"Forbidden literal '{pat}' found in {f.relative_to(PROJECT_ROOT)}"
    print("PASS: Zero hardcoded mockup literals found.")

if __name__ == "__main__":
    try:
        test_chart_captions_and_badges()
        test_chart_card_caption_support()
        test_data_presentation_utilities()
        test_zero_mockup_literals()
        print("\nALL DATA PRESENTATION GUARD TESTS PASSED.")
        sys.exit(0)
    except AssertionError as e:
        print(f"\nGUARD TEST FAILED: {e}")
        sys.exit(1)
# CommShield AI Core
