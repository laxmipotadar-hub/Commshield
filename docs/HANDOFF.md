# CommShield: System Handoff & Operator Guide

This document summarizes what exists in the repository, how to execute test suites and demo services on Windows and Ubuntu, and the verified status of all deliverables.

---

## 1. What Exists

1. **Frontend (`frontend/`)**:
   - Single Page Application built with React 18, Vite, TypeScript, Tailwind CSS, Lucide icons, and Recharts.
   - Core Views: Overview, Live Monitoring, Detection, Attribution & Explainability, Governance & Audit, Investigation & Forensics, Experiments & Benchmarks, and Digital Twin.
   - Transparent Data Provenance Strip (`DataProvenanceStrip`) rendering active dataset, window counts, and honest badges:
     - Real testbed traffic: `"Real 5G testbed traffic (5G-NIDD), replayed"` plus `"slices assigned"`
     - Scaled scenarios: `"semi-synthetic"`
     - Controlled simulation: `"Controlled simulation (ground truth known)"`
   - Presentation Demo Control Bar with deterministic 4-scene progression: (1) baseline, (2) approved onboarding, (3) unprovisioned device, (4) hidden ramp.

2. **Backend Service (`backend/`)**:
   - FastAPI REST API with SQLite database (portable to PostgreSQL via SQLAlchemy).
   - Replay service streaming canonical 60-second windows with request-time dynamic scoring and attribution.
   - Governance endpoints enforcing analyst token authentication (`COMMSHIELD_ANALYST_TOKEN`) for state mutations (`approve`, `reject`, `rollback`).
   - Digital Twin and Demo endpoints (`/api/demo/scenarios`, `/api/digital-twin`) reading strictly from saved result JSONs.

3. **ML Engine (`ml_engine/`)**:
   - Canonical 60-second window aggregation and scale-invariant ratio feature extraction (`FEATURE_NAMES`, `RATIO_FEATURE_NAMES`).
   - Per-slice Isolation Forest & Autoencoder anomaly detectors with percentile score fusion.
   - ADWIN distribution drift detector, JSD proportional growth test, and split conformal p-value abstention.
   - 4-stage Governance Pipeline:
     1. Normal-holdout FPR backtest ($\le 2.0\%$)
     2. Proportional growth test (JSD $\le 0.035$, per-UE rate deviation $\le 0.15$)
     3. Canary attack recall retention test ($\Delta_{\text{recall}} \le 3.0\%$)
     4. Cumulative drift budget ($b_{\text{step}} \le 1.5, B_{\text{rms}} \le 2.5, D_{\max} \le 3.5$)
   - Privacy-hardened provisioning loader with HMAC-SHA256 device hashing and small-group entropy suppression.

4. **Lab Adapter & Tests (`lab/`, `tests/`, `tools/`)**:
   - Offline Open5GS adapter operating on canonical sample logs.
   - `tools/demo_check.py`: Verification harness asserting all displayed numbers match saved result JSONs.
   - Full automated test suite (114 pytest unit and integration tests).

---

## 2. Cross-Platform Execution Instructions

### A. Windows (PowerShell)

```powershell
# 1. Setup Backend Environment
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt

# 2. Run Test Suite
pytest tests ..\experiments\test_governance_fix.py ..\experiments\test_ablations.py

# 3. Verify Demo & Results
python ..\tools\demo_check.py

# 4. Start Backend Server
uvicorn app.main:app --host 127.0.0.1 --port 8000

# 5. Build and Run Frontend (in separate terminal)
cd ..\frontend
npm install
npm run build
npm run dev
```

### B. Ubuntu / Linux (Bash)

```bash
# 1. Setup Backend Environment
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 2. Run Test Suite
pytest tests ../experiments/test_governance_fix.py ../experiments/test_ablations.py

# 3. Verify Demo & Results
python3 ../tools/demo_check.py

# 4. Start Backend Server
uvicorn app.main:app --host 127.0.0.1 --port 8000

# 5. Build and Run Frontend (in separate terminal)
cd ../frontend
npm install
npm run build
npm run dev
```

---

## 3. Verified Deliverables (From `docs/FINISH_PROGRESS.md`)

| Stage | Deliverable | Status | Weakest Finding |
|:---|:---|:---|:---|
| **F0** | Reality check & stabilization | **DONE** | Creeping step factor needed scaling to trigger cumulative budget $B_{\text{rms}}$. |
| **F1** (S3) | Demo mode fix & verification | **DONE** | Missing proxy route resolved in Vite configuration. |
| **F2** (S5) | Governance ratio-only fix | **DONE** | Non-proportional growth rejected by drift budget; operator review required. |
| **F3** (S8) | Real data default & honest badges | **DONE** | 5G-NIDD slice assignments are base station proxies rather than 3GPP S-NSSAI headers. |
| **F4** (S6) | Minimum privacy & analyst token | **DONE** | Small-group suppression suppresses entropy with `-1.0` when active UEs $< 5$. |
| **F5** (S7) | Boiling-frog creeping poisoning test | **DONE** | Step-only check accepts 10/10 attack steps; cumulative budget caps drift at step 5. |
| **F6** (S9) | Documentation & honest claims | **DONE** | Documentation aligned strictly with implemented code and saved results. |
