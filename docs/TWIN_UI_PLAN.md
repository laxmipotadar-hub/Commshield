# 3D Digital Twin UI Implementation Plan
1. Architecture: Single service layer (src/services/twinApi.ts) backing an interactive Three.js canvas in dark navy/charcoal styling.
2. Service Layer (TW1): Typed REST client & SSE/polling fallback handling connection status, stale data timeouts, and event deduplication.
3. Unified Layout Shell (TW1): Header with status, scenario selector, attack/demo controls; left telemetry bar; center 3D scene; right security panel; bottom timeline.
4. Three.js Topology (TW2): Render gNodeB, 5G Core (AMF/SMF/UPF), and UEs in slice zones (eMBB, URLLC, mMTC) strictly from backend nodes/links.
5. Resource Lifecycle (TW2): Instanced meshes, capped particles (max 8), requestAnimationFrame throttling, and explicit disposal on unmount.
6. Telemetry Visualization (TW3): Dynamic link particle flows, color-coded health/utilization nodes, hover tooltips, and deep click inspection.
7. Path Inspection (TW3): Focus camera, highlight connected component subgraphs, and provide single-click "Back to Full View" reset.
8. Attack Lifecycle (TW4): Start/Pause/Resume/Stop controls with modal confirmation, real error surfacing, and confirmed state transitions.
9. Blast Radius & Mitigation (TW4): Visual propagation (confirmed/degraded/isolated/mitigated), security alert triage, and 6-stage mitigation tracker.
10. Event Timeline (TW5): Chronological event feed with severity/slice filters and before/during/after metric delta panels.
11. Resilience Metrics (TW5): Time-to-detect, time-to-mitigate, availability, and residual impact cards derived purely from backend results.
12. What-If Lab (TW6): Isolated scenario parameter testing displaying simulated hypothetical metrics without mutating active twin state.
13. Guided Demo & Presentation (TW7): Step-by-step walkthrough across 4 phases with playback controls, plus full-screen clutter-free presentation view.
14. Mock Isolation: Strict dev mock fallback gated behind VITE_USE_MOCK=true with clear "MOCK" tags; real backend gaps logged to docs/API_GAPS.md.
15. Verification: Comprehensive unit tests for service layer resilience, scene disposal, and zero hardcoded metrics, verified via npm build.
<!-- CommShield AI Core -->
