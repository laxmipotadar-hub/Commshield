# CommShield: 5G Core Anomaly Detection & Baseline Governance

CommShield is a telecom-native anomaly detection and baseline governance platform for 5G core networks. It evaluates whether traffic shifts are explainable as proportional growth, abstains when evidence is inconclusive, and enforces canary-checked, drift-budgeted, analyst-approved baseline promotions with atomic rollback.

## Tech Stack

| Layer | Technologies |
| :--- | :--- |
| **Frontend** | React 18, TypeScript, Tailwind CSS, Recharts, Vite |
| **Backend** | FastAPI, SQLite (via SQLAlchemy, Postgres-portable), Pydantic v2 |
| **ML Engine** | Python 3.11+, scikit-learn (Isolation Forest), PyTorch (Autoencoder), NumPy, Pandas, SciPy |
| **Data & Replay**| 5G-NIDD captures, Open5GS/UERANSIM testbed logs, real-growth backbones (MAWI) |

## Directory Structure

```
commshield/
├── frontend/               # React + TS + Tailwind SPA (h-screen layout, full-height sidebar)
├── backend/app/            # FastAPI backend service
│   ├── api/                # API route controllers
│   ├── database/           # SQLite / SQLAlchemy connection & base
│   ├── models/             # SQLAlchemy ORM models
│   ├── schemas/            # Pydantic contract schemas
│   └── services/           # Replay, scoring, governance services
├── ml_engine/              # Python ML engine
│   ├── preprocessing/      # Canonical window aggregation & ratio feature extraction
│   ├── baseline/           # Per-slice atomic baseline learning & packaging
│   ├── detection/          # Isolation Forest, Autoencoder, percentile fusion, CUSUM
│   ├── attribution/        # ADWIN drift detection, proportional growth test (JSD), abstention
│   ├── governance/         # Quarantine, shadow candidate, canary retention, drift budgets
│   └── evaluation/         # Three-arm replay runner (A/B/C), ablations, evasion tests
├── data/                   # Data tiers: raw captures, processed windows, synthetic generators
├── experiments/            # Reproducible experiment configurations and outputs
└── docs/                   # Specifications, architecture, contracts, agent rules, and tests
```

## Quick Start (Preview)

1. **Backend**:
   ```bash
   cd backend
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   uvicorn app.main:app --reload --port 8000
   ```

2. **Frontend**:
   ```bash
   cd frontend
   npm install
   npm run dev
   ```

3. **Source of Truth & Governance Docs**:
   - `docs/COMMSHIELD_SPEC_v9.md`: Comprehensive system specification
   - `docs/AGENT_RULES.md`: Development rules and constraints
   - `docs/ARCHITECTURE.md`: Module boundaries, data flow, pluggable interfaces, and milestones
   - `docs/CONTRACTS.md`: DB schemas, API endpoints, and canonical JSON contracts
   - `docs/TESTING.md`: Module verification matrices and test suites

## Reproducible Pipeline Execution

To run the complete pipeline end-to-end with one command (synthetic data generation, baseline training, scenario replay through detection, attribution, and governance):

```bash
# Reset database and replay scenario end-to-end
python backend/scripts/run_demo.py --reset-db --scenario legitimate_growth --windows 60
```

To reset runtime telemetry and drift events while preserving immutable anchor baselines:
```bash
python backend/scripts/reset_db.py
# Or via API:
# curl -X POST http://localhost:8000/api/reset
```

## Where to Change What

| Configuration Area | File / Path | Description & Notes |
| :--- | :--- | :--- |
| **Detection Thresholds** | `ml_engine/detection/config.py` | Percentiles (95th/98th/99th), CUSUM parameter $k$, alarm threshold $h$, fusion weights |
| **Attribution Thresholds** | `ml_engine/attribution/config.py` | ADWIN $\delta$ sensitivity, JSD growth threshold ($\tau_{\text{JSD}}$), sample limits, ratio bounds |
| **Governance Limits** | `ml_engine/governance/config.py` | Holdout FPR cap, canary retention limit, drift budget thresholds ($d_{\text{update}}, d_{\text{anchor}}, \Delta_{\max}$) |
| **Scenarios & Datasets** | `data/synthetic/` & `backend/scripts/generate_synthetic_scenarios.py` | Scenario JSON files (`stable_benign`, `legitimate_growth`, `attack_in_growth`, `stealth_poisoning`) |
| **Design System Colours** | `frontend/tailwind.config.js` | Palette definition: `safe` (emerald/teal), `attack` (red), `suspicious` (amber), `quarantined` (purple), `navy`, `blue` |
| **UI Labels & Navigation** | `frontend/src/components/layout/Sidebar.tsx` & `frontend/src/pages/` | Navigation titles, page headings, status badge text, table column labels |
| **API URLs & Client Endpoints** | `frontend/src/services/api.ts` & `frontend/vite.config.ts` | Backend REST endpoints, `/api` proxy target (`http://localhost:8000`), SSE stream URLs |

