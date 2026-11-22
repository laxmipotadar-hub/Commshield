# CommShield Presentation Demo Runbook

This runbook specifies the exact commands, click sequence, timing, keyboard shortcuts, and fallback procedures for evaluating CommShield's four-scene presentation demo on Windows (PowerShell) and Ubuntu (bash).

---

## 1. Quickstart & Server Launch Commands

### Ubuntu / Linux (bash)
```bash
# Terminal 1: Backend Server (FastAPI)
cd /path/to/NETWORK_5G
source backend/venv/bin/activate
uvicorn backend.app.main:app --host 127.0.0.1 --port 8000

# Terminal 2: Frontend Dashboard (Vite + React)
cd frontend
npm run dev -- --host 127.0.0.1 --port 5173
```

### Windows (PowerShell)
```powershell
# Terminal 1: Backend Server (FastAPI)
cd C:\path\to\NETWORK_5G
.\backend\venv\Scripts\Activate.ps1
uvicorn backend.app.main:app --host 127.0.0.1 --port 8000

# Terminal 2: Frontend Dashboard (Vite + React)
cd frontend
npm run dev -- --host 127.0.0.1 --port 5173
```

### Verification Check
Before presenting, run the automated verification tool to confirm all 10 consistency checks pass:
```bash
python tools/demo_check.py
```

---

## 2. Presentation Click Sequence & Timing

Open the browser to `http://127.0.0.1:5173`.

### Initial Setup
1. In the top navigation bar, click the **Demo Mode** button to toggle it **ON**.
2. Notice the control bar expands with:
   - Source tag (`Source: Simulated twin`)
   - Scene step indicator (`Scene 1 of 4`)
   - Scenario selector
   - Accessibility toggle (`Low-Motion: ON/OFF`)
   - Action button (`Next scene (N)`)

### Scene 1: Baseline Steady-State Telemetry
* **Action**: Automatically loads on Demo Mode start.
* **Timing**: Replay begins at $t=0$; auto-pauses at Window #5 (`periodic_audit`).
* **Observation**: Point at 200 catalog-provisioned SIMs, 0 alerts, and nominal packet rates (41.25 pps cameras, 80.0 pps AGVs, 10.0 pps sensors).
* **Advance**: Press **'N'** or click **Next scene (N)**.

### Scene 2: Approved Onboarding (Batch OB-01 & OB-02)
* **Action**: Replay starts for scheduled onboarding expansion.
* **Timing**: New devices join at Window #10; auto-pauses at Window #14 (`governance_approval`).
* **Observation**: Point at 30 onboarded sensors matching change event `BATCH-OB-20261115-01`, volume scale $k=1.48$, JSD divergence $0.018 \le 0.045$, and 0.0% contamination.
* **Advance**: Press **'N'** or click **Next scene (N)**.

### Scene 3: Unprovisioned Device Burst Flagged
* **Action**: Rogue SIM traffic ingress on the core.
* **Timing**: Rogue devices appear at Window #10; auto-pauses at Window #11 (`quarantine_isolation`).
* **Observation**: Point at catalog provisioned share plummeting to 57.1% (<95.0% threshold), zero-trust Rule 1 quarantine enforcement, and 0.0% contamination vs Naive Retraining's 50.0% poisoning.
* **Lab Fallback**: Scene 3 automatically uses the Open5GS live lab capture clip if `data/lab/windows.jsonl` exists and validates; otherwise it smoothly runs the simulated twin clip without errors.
* **Advance**: Press **'N'** or click **Next scene (N)**.

### Scene 4: Hidden Ramp (Naive Poisoned vs CommShield Quarantines Excess)
* **Action**: Stealth slow attack ramp hidden inside approved onboarding.
* **Timing**: Rate creep begins at Window #10; auto-pauses at Window #15 (`conformal_gray_band`) and Window #16 (`governance_divergence`).
* **Observation**: Point at Naive Retraining suffering 33.3% contamination, while CommShield's split-conformal gray band ($p \in [0.01, 0.05]$) quarantines excess devices, holding contamination to 1.7% [95% CI: 0.0%, 5.0%].

---

## 3. Keyboard Shortcuts & Accessibility

| Key | Action | Context |
| :--- | :--- | :--- |
| **`N`** or **`n`** | Advance to next scene (Scene $X \rightarrow X+1$) | Active whenever Demo Mode is ON |
| **`ArrowRight`** | Advance to next scene | Active whenever Demo Mode is ON |
| **Space** | Pause / Resume replay playback | Active during replay |
| **Low-Motion Button** | Toggles packet particles & pulsing animations | Synchronized with OS `prefers-reduced-motion` |

---

## 4. Fallback Procedures & Offline Snapshot Operation

If backend database connectivity is lost or running entirely offline:
1. **Frontend Snapshot Fallback**: When the backend API is unreachable, `DemoContext` automatically activates the hardcoded canonical presets (`FALLBACK_PRESETS`) and renders a visible `Snapshot Fallback` badge in the header.
2. **Backend Snapshot Fallback**: When the database is uninitialized, `/api/demo/scenarios` reads fallback benchmark data from `experiments/snapshot/twin/three_arm_twin_summary.json`.
3. **Data Panel Fallback**: The Data Catalog panel falls back to cached snapshots in `experiments/snapshot/` and provides deterministic client/in-memory generation.
<!-- CommShield AI Core -->
