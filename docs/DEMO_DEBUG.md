# Demo Mode Diagnosis (S2)

This document details the architectural inspection and diagnostic audit of CommShield's presentation demo mode across the backend API, frontend routing, and UI presentation components.

---

## 1. GET /api/demo/scenarios Inspection

- **Endpoint Existence**: **YES**, defined in [backend/app/api/demo.py](file:///home/laxmi/Desktop/NETWORK/NETWORK_5G/backend/app/api/demo.py#L98) and registered under `/api/demo` router in [backend/app/main.py](file:///home/laxmi/Desktop/NETWORK/NETWORK_5G/backend/app/main.py#L65).
- **HTTP Status Code**: **200 OK**.
- **Response Structure & Body**:
  Returns a `DemoScenariosResponse` JSON object containing:
  - `source_attribution`: `"CommShield 5G Digital Twin & Lab Telemetry"`
  - `fixed_seed`: `42`
  - `scenarios`: Exactly 4 pre-packaged presentation scenes ordered strictly 1 to 4:
    1. **`baseline`**: "1. Baseline Steady-State Telemetry" (`source`: `"simulated_twin"`, `source_badge`: `"Simulated twin"`, windows 0–9).
    2. **`approved_onboarding`**: "2. Approved Onboarding (Batch OB-01 & OB-02)" (`source`: `"simulated_twin"`, `source_badge`: `"Simulated twin"`, windows 0–19).
    3. **`unprovisioned_device`**: "3. Unprovisioned Device Burst Flagged" (`source`: `"lab"`, `source_badge`: `"Live lab"` when validated against canonical schema, otherwise `"simulated_twin"` / `"Simulated twin"`, windows 0–19).
    4. **`hidden_ramp`**: "4. Hidden Ramp (Naive Poisoned vs CommShield Quarantines Excess)" (`source`: `"simulated_twin"`, `source_badge`: `"Simulated twin"`, windows 0–29).

All 4 scenarios include deterministic key event timelines with single-line presenter captions, window ranges, and three-arm benchmark summaries.

---

## 2. Frontend URL and Backend Proxy Alignment

- **Frontend Invocation**:
  - Implemented in [frontend/src/services/api.ts](file:///home/laxmi/Desktop/NETWORK/NETWORK_5G/frontend/src/services/api.ts#L712):
    ```typescript
    getDemoScenarios: () => request<DemoScenariosResponse>('/api/demo/scenarios')
    ```
  - `API_BASE_URL` is defined at [frontend/src/services/api.ts#L6](file:///home/laxmi/Desktop/NETWORK/NETWORK_5G/frontend/src/services/api.ts#L6):
    ```typescript
    const API_BASE_URL = (import.meta.env.VITE_API_URL || 'http://localhost:8000').replace(/\/$/, '');
    ```
  - When `getDemoScenarios()` is called by `DemoContext.tsx`, it executes a `fetch()` to `http://localhost:8000/api/demo/scenarios`.
- **Proxy Status in Vite**:
  - In [frontend/vite.config.ts](file:///home/laxmi/Desktop/NETWORK/NETWORK_5G/frontend/vite.config.ts#L13-L16), the dev server config is:
    ```typescript
    server: {
      port: 5173,
      host: true,
    }
    ```
  - **Issue**: Vite does not configure a `proxy` for `/api`. If the application is accessed in an environment where direct browser cross-origin requests to port 8000 are restricted or where `VITE_API_URL` is omitted, requests relying on local origin `/api/*` will not route to the backend.

---

## 3. Demo Toggle Component & Rendering Status

- **Component & File**:
  - Component: `<DemoControlBar />` defined in [frontend/src/components/DemoControlBar.tsx](file:///home/laxmi/Desktop/NETWORK/NETWORK_5G/frontend/src/components/DemoControlBar.tsx#L5-L87).
  - Exported via [frontend/src/components/index.ts](file:///home/laxmi/Desktop/NETWORK/NETWORK_5G/frontend/src/components/index.ts#L4).
  - Rendered in [frontend/src/App.tsx](file:///home/laxmi/Desktop/NETWORK/NETWORK_5G/frontend/src/App.tsx#L200) inside the top header toolbar (`<header className="h-16 ...">`).
  - Wrapped by `<DemoProvider>` in [frontend/src/App.tsx#L377](file:///home/laxmi/Desktop/NETWORK/NETWORK_5G/frontend/src/App.tsx#L377).
- **Condition Analysis**:
  - The toggle button (`<button onClick={() => setIsDemoMode(!isDemoMode)}>Demo Mode [ON/OFF]</button>`) is **unconditionally rendered** inside `<header>`. It is NOT behind a false condition and IS imported.
  - Sub-controls (Source Tag Badge, Scene selector dropdown `1` through `4`, and `Next scene` button) are conditionally rendered behind `{isDemoMode && (...)}`.
  - The event banner `<DemoEventBanner />` in [frontend/src/App.tsx#L286](file:///home/laxmi/Desktop/NETWORK/NETWORK_5G/frontend/src/App.tsx#L286) is conditionally rendered on line 20 of `DemoEventBanner.tsx` (`if (!isDemoMode) return null;`).

---

## 4. Test Suite and Build Execution

- **Backend Pytest**:
  ```bash
  backend/venv/bin/pytest backend/tests/
  ```
  Result: **108 passed in 12.63s** (0 failures).
- **Demo Check Verification Tool**:
  ```bash
  backend/venv/bin/python tools/demo_check.py
  ```
  Result: **10 PASSED, 0 FAILED** (Backend health, scenarios 200, exactly 4 scenes, order compliant, captions present, twin endpoints responsive, 570 result numbers verified, badge rule enforced).
- **Frontend Build**:
  ```bash
  npm --prefix frontend run build
  ```
  Result: **Clean production build** (`tsc && vite build`), 0 compilation errors.

---

## 5. Root Causes and Minimal Fixes

1. **Vite Proxy Omission**:
   - *Cause*: `frontend/vite.config.ts` lacks a `/api` reverse proxy to `http://localhost:8000`.
   - *Smallest Fix*: In S3, add `proxy: { '/api': { target: 'http://localhost:8000', changeOrigin: true } }` inside `server` in [frontend/vite.config.ts](file:///home/laxmi/Desktop/NETWORK/NETWORK_5G/frontend/vite.config.ts).
2. **Missing Unit Tests for Demo Toggle and Scenarios Contract**:
   - *Cause*: While `tools/demo_check.py` verifies runtime API endpoints, unit tests in `backend/tests/` did not explicitly assert the four-scenario contract and toggle rendering behavior.
   - *Smallest Fix*: In S3, add explicit unit test assertions in [backend/tests/test_demo.py](file:///home/laxmi/Desktop/NETWORK/NETWORK_5G/backend/tests/test_demo.py) confirming that GET `/api/demo/scenarios` returns 4 scenarios with exact metadata and that the frontend components include the Demo toggle.
<!-- CommShield AI Core -->
