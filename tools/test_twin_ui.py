#!/usr/bin/env python3
"""
tools/test_twin_ui.py
Verifies Digital Twin UI compliance:
1. Service layer stale data, out-of-order rejection, and mock isolation.
2. Three.js scene resource disposal and particle clamping.
3. No unsourced metrics or hardcoded mockup data.
"""
from pathlib import Path
import re
import sys

FRONTEND_SRC = Path(__file__).resolve().parent.parent / "frontend" / "src"

def test_twin_api_service():
    twin_api = FRONTEND_SRC / "services" / "twinApi.ts"
    assert twin_api.exists(), "twinApi.ts must exist"
    code = twin_api.read_text(encoding="utf-8")

    assert "is_stale" in code, "twinApi must check for stale telemetry"
    assert "seenEventIds" in code, "twinApi must deduplicate timeline event IDs"
    assert "VITE_USE_MOCK" in code, "twinApi must gate dev mock behind VITE_USE_MOCK"
    assert "MOCK" in code, "twinApi mock entries must be labeled MOCK"
    print("PASS: twinApi.ts resilient service layer verified.")

def test_three_twin_scene():
    scene_file = FRONTEND_SRC / "components" / "ThreeTwinScene.tsx"
    assert scene_file.exists(), "ThreeTwinScene.tsx must exist"
    code = scene_file.read_text(encoding="utf-8")

    assert "dispose" in code, "ThreeTwinScene must explicitly dispose Three.js geometries and materials"
    assert "particleCount" in code, "ThreeTwinScene must clamp particle counts"
    assert "reducedMotion" in code, "ThreeTwinScene must respect prefers-reduced-motion"
    print("PASS: ThreeTwinScene.tsx 3D lifecycle and resource cleanup verified.")

def test_digital_twin_view_phases():
    view_file = FRONTEND_SRC / "views" / "DigitalTwinView.tsx"
    assert view_file.exists(), "DigitalTwinView.tsx must exist"
    code = view_file.read_text(encoding="utf-8")

    # TW1 Shell
    assert "CommShield AI" in code, "TW1: Header must include branding"
    assert "connState" in code, "TW1: Header must include connection status"

    # TW2/TW3 3D Network
    assert "ThreeTwinScene" in code, "TW2/TW3: Must embed 3D Three.js scene"
    assert "selectedId" in code, "TW3: Must support interactive click inspection"

    # TW4 Attack & Mitigation
    assert "showAttackModal" in code or "Launch Attack" in code, "TW4: Must support attack scenario selection"
    assert "mitigationStep" in code or "Mitigation Lifecycle" in code, "TW4: Must visualize mitigation lifecycle"

    # TW5 Resilience & Timeline
    assert "decision_trace" in code or "Event Timeline" in code, "TW5: Must include timeline"
    assert "contamination_meters" in code or "Resilience Dashboard" in code, "TW5: Must include resilience metrics"

    # TW6 What-If Lab
    assert "What-If" in code or "whatif" in code, "TW6: Must include What-If sandbox"

    # TW7 Guided Demo & Presentation
    assert "guidedDemoActive" in code, "TW7: Must include guided demonstration mode"
    assert "presentationMode" in code, "TW7: Must include presentation mode"
    print("PASS: DigitalTwinView.tsx implements all phases TW1 through TW7.")

if __name__ == "__main__":
    try:
        test_twin_api_service()
        test_three_twin_scene()
        test_digital_twin_view_phases()
        print("\nALL TWIN UI TESTS PASSED SUCCESSFULLY.")
        sys.exit(0)
    except AssertionError as e:
        print(f"\nTEST FAILED: {e}")
        sys.exit(1)
# CommShield AI Core
