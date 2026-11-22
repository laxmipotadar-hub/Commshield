# CommShield Installation, Execution, and Verification Guide

CommShield is cross-platform and verified to run on **Windows 10/11** (PowerShell) and **Ubuntu/Linux** (Bash).

---

## 1. System Requirements & Prerequisites

* **Python**: Version 3.10 through 3.13 (verified on Python 3.13.5).
* **Node.js & npm**: Node.js 18+ (verified on Node.js 22.x) and npm 10+.
* **Git**: With LF line ending support (configured automatically via `.gitattributes`).

---

## 2. Environment Setup

### A. Clone and Configure Line Endings
```bash
git clone <repo-url> commshield
cd commshield
```
`.gitattributes` guarantees LF line endings for all Python, TypeScript, and JSON files on checkout.

### B. Python Virtual Environment Setup

#### Windows (PowerShell)
```powershell
# Create virtual environment inside backend directory
python -m venv backend\.venv

# Activate virtual environment
backend\.venv\Scripts\Activate.ps1

# Upgrade pip and install pinned dependencies
python -m pip install --upgrade pip
pip install -r requirements.lock
```

#### Ubuntu / Debian (Bash)
```bash
# Ensure venv support is installed
sudo apt update && sudo apt install -y python3-venv python3-pip

# Create virtual environment
python3 -m venv backend/.venv

# Activate virtual environment
source backend/.venv/bin/activate

# Upgrade pip and install pinned dependencies
pip install --upgrade pip
pip install -r requirements.lock
```

### C. Environment Configuration
Copy the configuration template:

#### Windows (PowerShell)
```powershell
Copy-Item .env.example .env
```

#### Ubuntu / Linux (Bash)
```bash
cp .env.example .env
```

The default `.env` includes:
* `DATABASE_URL=sqlite:///backend/commshield.db` (cross-platform relative SQLite path)
* `COMMSHIELD_HMAC_KEY=...` (cryptographic salt for subscriber pseudonymisation)
* `COMMSHIELD_ANALYST_TOKEN=commshield-analyst-secret-v1` (governance authorization)
* `COMMSHIELD_SUPPRESSION_K=5` (small-group privacy suppression threshold)

---

## 3. Environment & Runtime Verification

Run the automated verification script to validate your environment across Python, installed libraries, backend initialization, tests, and frontend build:

#### Windows (PowerShell)
```powershell
python tools/check_env.py
```

#### Ubuntu / Linux (Bash)
```bash
python3 tools/check_env.py
```

Expected output:
```text
======================================================================
Summary of Command Verification:
  Libraries Installed : PASS
  Backend App Import  : PASS
  Test Runner (pytest): PASS
  Frontend Build (Vite): PASS
======================================================================
Status: ALL SYSTEMS GO. CommShield is verified operational.
```

To run the static code compatibility audit:
```powershell
python tools/audit_compat.py
```

---

## 4. Running the Backend Service

The backend is built with FastAPI and runs under Uvicorn.

#### Windows (PowerShell)
```powershell
# Ensure virtual environment is active
# Set PYTHONPATH so the root package is resolvable
$env:PYTHONPATH = "."
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
```

#### Ubuntu / Linux (Bash)
```bash
# Ensure virtual environment is active
export PYTHONPATH="."
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
```

Backend endpoints will be available at:
* API: `http://localhost:8000/api/v1`
* Interactive OpenAPI Docs: `http://localhost:8000/docs`
* Health Probe: `http://localhost:8000/health`

---

## 5. Running the Frontend Dashboard

The frontend is built with React 18, TypeScript, TailwindCSS, and Vite.

#### Windows (PowerShell)
```powershell
cd frontend
npm install
npm run dev
```

#### Ubuntu / Linux (Bash)
```bash
cd frontend && npm install && npm run dev
```

Open your browser to `http://localhost:5173`.

### Production Frontend Build
To compile the static production bundle:
#### Windows (PowerShell)
```powershell
cd frontend
npm run build
```

#### Ubuntu / Linux (Bash)
```bash
cd frontend && npm run build
```
Build artifacts will be written to `frontend/dist/`.

---

## 6. Running the Test Suite

CommShield provides automated test suites covering detection, governance, attribution, privacy by design, and end-to-end replay pipelines.

### Running Core and Integration Tests

#### Windows (PowerShell)
```powershell
# Run the 48 core unit, attribution, governance, detection, and privacy tests:
pytest -k "not asyncio" backend/tests/ -v

# Run privacy by design tests:
pytest backend/tests/test_privacy.py -v

# Run governance and audit tests:
pytest backend/tests/test_governance.py backend/tests/test_audit_verification.py -v
```

#### Ubuntu / Linux (Bash)
```bash
# Run full 69-test suite:
pytest backend/tests/ -v
```

> **Windows Note on in-process `AsyncClient(transport=ASGITransport(app=app))`**:  
> On Windows with Python 3.13, Starlette's in-process `ASGITransport` under `pytest-anyio` deadlocks on thread portal cleanup during client fixture initialization for the 21 HTTP route tests. All core algorithmic, detection, governance, attribution, ML engine, and privacy tests (48 tests) execute synchronously or via `anyio.run()` and pass 100%. Live HTTP requests to a running `uvicorn` backend process are unaffected on Windows.

---

## 7. Cross-Platform Audit Findings

Automated audit (`tools/audit_compat.py`) results:
1. **POSIX-Specific Modules**: **None**. Zero occurrences of `fcntl`, `termios`, `pty`, `pwd`, or `grp` in application code.
2. **Subprocess Calls**: All subprocess invocations use cross-platform arrays without `shell=True` (except `tools/check_env.py` resolving `.cmd` wrappers on Windows).
3. **Hard-Coded POSIX Paths**:
   - `backend/tests/test_api.py:201`: Uses mock string `model_artifact_path="/tmp/model.joblib"` as a dummy database record value. It is never opened or accessed as a filesystem path on disk.
   - All runtime model artifact paths utilize `pathlib.Path` with relative references (`data/processed/baselines/`).
4. **Filename Case Collisions**: **Zero**. Verified that no filenames conflict on case-insensitive filesystems (NTFS/FAT32).
<!-- CommShield AI Core -->
