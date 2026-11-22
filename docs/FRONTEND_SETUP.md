# CommShield Frontend Setup & Execution Guide

## Requirements
- **Node.js**: `v18.0.0` or higher (tested with `v20.x` and `v22.x`)
- **Package Manager**: `npm` (v9+) or `pnpm`
- **Supported Operating Systems**: Windows 10/11 (PowerShell), Ubuntu 20.04/22.04 LTS (bash)

## Environment Configuration
Create a `.env` file inside `frontend/` (or copy from `.env.example`):
```env
VITE_API_URL=http://localhost:8000
VITE_USE_MOCK=false
```

- `VITE_API_URL`: Root URL of the FastAPI backend.
- `VITE_USE_MOCK`: Set to `true` strictly for offline dev simulation when backend is unreachable. Defaults to `false`.

## Installation & Commands

### 1. Install Dependencies
**Windows (PowerShell)**:
```powershell
npm install --prefix frontend
```
**Ubuntu (bash)**:
```bash
npm install --prefix frontend
```

### 2. Start Development Server
**Windows (PowerShell)**:
```powershell
npm run dev --prefix frontend
```
**Ubuntu (bash)**:
```bash
npm run dev --prefix frontend
```
The server will bind locally at `http://localhost:5173`.

### 3. Production Build
**Windows (PowerShell)**:
```powershell
npm run build --prefix frontend
```
**Ubuntu (bash)**:
```bash
npm run build --prefix frontend
```

### 4. Run Test Suite
**Windows (PowerShell)**:
```powershell
backend\.venv\Scripts\python.exe tools/verify_frontend_numbers.py
```
**Ubuntu (bash)**:
```bash
python3 tools/verify_frontend_numbers.py
```
<!-- CommShield AI Core -->
