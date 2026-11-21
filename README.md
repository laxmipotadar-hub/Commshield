# CommShield: 5G Core Anomaly Detection & Baseline Governance

CommShield is a telecom-focused anomaly detection and baseline governance platform for 5G core telemetry. It evaluates whether traffic shifts are explainable as proportional growth, abstains when evidence is inconclusive, and enforces canary-checked, drift-budgeted, analyst-approved baseline promotions with atomic rollback.

## Core Capabilities

- **Ensemble Anomaly Detection**: Isolation Forest and PyTorch Autoencoder scoring canonical 60-second telemetry windows with percentile score fusion and CUSUM change detection.
- **Explainability & Attribution**: Jensen-Shannon Divergence (JSD) test for proportional growth attribution and split conformal p-value abstention.
- **4-Stage Governance Pipeline**:
  1. *Normal-holdout FPR backtest* ($\le 2.0\%$)
  2. *Proportional growth verification* (JSD $\le 0.035$, per-UE rate deviation $\le 0.15$)
  3. *Canary attack retention test* ($\Delta_{\text{recall}} \le 3.0\%$)
  4. *Cumulative drift budget* ($b_{\text{step}} \le 1.5, B_{\text{rms}} \le 2.5, D_{\max} \le 3.5$)
- **Human-in-the-Loop Operator Gate**: Baseline promotion requires analyst bearer token (`COMMSHIELD_ANALYST_TOKEN`) verification with immutable anchor rollback.
- **Privacy Hardening**: HMAC-SHA256 device ID masking and small-group entropy suppression.
- **Honest Data Provenance**: Replays real 5G testbed traffic (5G-NIDD) with assigned slice topology (BS1 $\rightarrow$ eMBB, BS2 $\rightarrow$ URLLC) and transparent labelling (`"Real 5G testbed traffic (5G-NIDD), replayed"`, `"slices assigned"`, `"semi-synthetic"`, `"Controlled simulation"`).

---

## Tech Stack

| Layer | Technologies |
| :--- | :--- |
| **Frontend** | React 18, TypeScript, Tailwind CSS, Recharts, Vite |
| **Backend** | FastAPI, SQLite (via SQLAlchemy, PostgreSQL-portable), Pydantic v2 |
| **ML Engine** | Python 3.11+, scikit-learn, PyTorch, NumPy, SciPy |
| **Telemetry Sources** | 5G-NIDD real testbed captures, parametric synthetic twin generator, Open5GS lab adapter |

---

## Directory Structure

```
commshield/
├── frontend/               # React + TS + Tailwind SPA (h-screen layout, full-height sidebar)
├── backend/app/            # FastAPI backend service (endpoints, database models, replay)
├── ml_engine/              # Python ML engine
│   ├── preprocessing/      # Canonical window aggregation & scale-invariant ratio features
│   ├── baseline/           # Per-slice atomic baseline packaging & scaling parameters
│   ├── detection/          # Isolation Forest, Autoencoder, percentile fusion, CUSUM
│   ├── attribution/        # JSD growth test, conformal abstention, device-class IF
│   ├── governance/         # 4-stage pipeline: holdout, growth, canary, drift budget
│   └── evaluation/         # Three-arm replay runner (A/B/C), ablations, real benchmarks
├── data/                   # Data tiers: raw captures, processed windows, twin provisioning
├── experiments/            # Experiment runners and saved evaluation JSONs
├── lab/                    # Open5GS adapter and offline sample logs
├── tools/                  # Verification scripts (demo_check.py)
└── docs/                   # Specifications, architecture, handoff, and limitations
```

---

## Quick Start Guide

### Windows (PowerShell)

```powershell
# 1. Start Backend
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --host 127.0.0.1 --port 8000

# 2. Run Test Suite & Verification Harness (in a second terminal)
cd backend
.\venv\Scripts\Activate.ps1
pytest tests ..\experiments\test_governance_fix.py ..\experiments\test_ablations.py
python ..\tools\demo_check.py

# 3. Start Frontend (in a third terminal)
cd frontend
npm install
npm run build
npm run dev
```

### Ubuntu / Linux (Bash)

```bash
# 1. Start Backend
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 127.0.0.1 --port 8000

# 2. Run Test Suite & Verification Harness (in a second terminal)
cd backend
source venv/bin/activate
pytest tests ../experiments/test_governance_fix.py ../experiments/test_ablations.py
python3 ../tools/demo_check.py

# 3. Start Frontend (in a third terminal)
cd frontend
npm install
npm run build
npm run dev
```

---

## Documentation Links

- `docs/HANDOFF.md`: Comprehensive handoff summary, commands, and verified deliverables
- `docs/LIMITATIONS.md`: Known system and dataset limitations
- `docs/GOVERNANCE_FIX.md`: Mathematical derivation and verification of ratio-only drift budgets
- `docs/PRIVACY.md`: Telemetry privacy threat model, HMAC hashing, and analyst gating
- `docs/CONTRACTS.md`: Canonical schemas, API endpoints, and database models
- `docs/DEMO_SCRIPT.md`: Step-by-step presentation script for the 4-scene demo
