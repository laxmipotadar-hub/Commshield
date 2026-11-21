# Stitch UI Port Documentation

## 1. Overview
The CommShield 5G SOC dashboard has been re-skinned to match the Stitch design export (`design/stitch_commshield_5g_soc_dashboard/`). This update is strictly visual and layout-oriented: no backend logic, API contracts, detector thresholds, or governance gate formulas were altered.

## 2. Theme Decision
The design export follows a **Dual-Shell architecture**:
- **Fixed Command Shell**: `#0a1628` deep navy sidebar and navigation frame.
- **Analytical Canvas**: `#f8f9ff` light surface background with full dark-mode support via Tailwind `.dark` classes (`#0b1329` / `#0f172a`).
- **Theme Toggle**: Default follows system `prefers-color-scheme`, persisted to `localStorage` (`commshield_theme`), with an explicit toggle in the top navigation bar.
- **Motion Toggle**: Low-motion accessibility mode following `prefers-reduced-motion` with an interactive manual toggle.

## 3. Screen Status Summary

| Item | Screen Name | Target Component(s) | Status | Commit |
| :--- | :--- | :--- | :--- | :--- |
| **UI1** | Design tokens and layout shell | `tailwind.config.js`, `index.css`, `App.tsx` | **DONE** | `aa836fc` |
| **UI2** | `security_command_center` | `OverviewPage.tsx`, `OverviewView.tsx` | **DONE** | `b6ffb6b` |
| **UI3** | `scientific_experiment_comparison` | `ExperimentsView.tsx` | **DONE** | `c05f57d` |
| **UI4** | `baseline_governance_trust_center` | `GovernanceView.tsx` | **DONE** | `5937807` |
| **UI5** | `anomaly_detection_detector_agreement` | `DetectionPage.tsx`, `InvestigationView.tsx` | **DONE** | `1905a91` |
| **UI6** | `digital_twin_spatial_rf_topology` | `DigitalTwinView.tsx` | **DONE** | `669009c` |

## 4. Omitted Widgets & Architectural Integrity
To maintain strict mathematical honesty and project integrity:
- **RF Spectrum Analyzer**: Omitted uncomputed RF spectrum heatmaps that lack underlying physical sensor probes or backend endpoints.
- **Arbitrary eNodeB Tooltips**: Omitted simulated antenna gain tooltips that do not correspond to the digital twin catalog.
- **External CDN Scripts & Fonts**: Bundled local system font fallbacks (`Inter`, `JetBrains Mono`, system sans-serif) and eliminated all external Google Fonts or CDN scripts so the application operates 100% offline.

## 5. Removed Mockup Placeholders & Live Data Sourcing
All static mockup values in the Stitch HTML templates were replaced with real, verified data streams:
- `48.2 Gbps`, `148.6 TB` &rarr; Replaced with dynamic throughput from `api.getWindows()` and `api.getRealOverview()`.
- `4,829,140 Flow Vectors` &rarr; Replaced with verified empirical benchmark window counts ($N = 11,870$ windows across 5 seeds).
- `1 - β = 0.992` &rarr; Replaced with empirical empirical power / TPR metrics from `summary_5seeds.json`.
- `UPF-EDGE-09`, `ENCLAVE 04`, `Sarah Jenkins` &rarr; Sourced dynamically from authenticated analyst profile (`analyst_sec_01`) and active core node state (`5G-CORE-UPF`).
- Verified zero static mockup leaks using `tools/verify_frontend_numbers.py`.
