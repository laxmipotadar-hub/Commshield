#!/usr/bin/env python3
"""CommShield Environment and Build Health Checker.

Verifies the runtime environment across Windows (PowerShell/CMD) and Ubuntu/Linux.
Checks:
1. Python version and platform details.
2. Key scientific, ML, and web library versions.
3. Backend service import and initialization.
4. Test suite execution via pytest.
5. Frontend production build via npm.

Usage:
  python tools/check_env.py
"""

import importlib
import importlib.metadata
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

KEY_LIBRARIES = [
    ("fastapi", "FastAPI"),
    ("uvicorn", "Uvicorn"),
    ("sqlalchemy", "SQLAlchemy"),
    ("pydantic", "Pydantic"),
    ("sklearn", "scikit-learn"),
    ("numpy", "NumPy"),
    ("scipy", "SciPy"),
    ("torch", "PyTorch"),
    ("shap", "SHAP"),
    ("pytest", "Pytest"),
    ("httpx", "HTTPX"),
    ("anyio", "AnyIO"),
]


def check_python_environment():
    print("=" * 70)
    print("CommShield Environment Verification")
    print("=" * 70)
    print(f"Operating System : {platform.system()} ({platform.release()}, {platform.machine()})")
    print(f"Platform Tag     : {sys.platform} (os.name='{os.name}')")
    print(f"Python Executable: {sys.executable}")
    py_ver = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    print(f"Python Version   : {py_ver}")
    print("-" * 70)

    # Version check: Recommended 3.10+
    if sys.version_info < (3, 10):
        print("  [WARN] Python 3.10+ recommended.")
    else:
        print("  [OK] Python version meets requirements (>= 3.10).")


def check_library_versions():
    print("\nKey Library Versions:")
    print("-" * 70)
    print(f"{'Library':20} | {'Status':10} | {'Installed Version':25}")
    print("-" * 70)
    all_installed = True
    for mod_name, display_name in KEY_LIBRARIES:
        try:
            ver = None
            try:
                ver = importlib.metadata.version(display_name.lower())
            except Exception:
                try:
                    ver = importlib.metadata.version(mod_name)
                except Exception:
                    pass

            if ver is None:
                mod = importlib.import_module(mod_name)
                ver = getattr(mod, "__version__", "installed (no __version__)")

            print(f"{display_name:20} | {'FOUND':10} | {ver:25}")
        except ImportError:
            all_installed = False
            print(f"{display_name:20} | {'MISSING':10} | Not installed")

    return all_installed


def check_backend_import():
    print("\n1. Testing Backend App Initialization:")
    cmd = [sys.executable, "-c", "import sys; sys.path.insert(0, '.'); from backend.app.main import app; print('FastAPI app initialized')"]
    try:
        proc = subprocess.run(
            cmd,
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=25,
        )
        if proc.returncode == 0:
            print("  ✓ Backend app imported and initialized successfully.")
            return True
        else:
            print("  ✗ Backend app failed to initialize:")
            print(proc.stderr.strip() or proc.stdout.strip())
            return False
    except Exception as e:
        print(f"  ✗ Error testing backend import: {e}")
        return False


def check_tests():
    print("\n2. Testing Test Suite Execution (pytest):")
    # Run a targeted test to verify runner integrity
    test_path = ROOT / "backend" / "tests" / "test_privacy.py"
    if not test_path.is_file():
        # Fallback to any test file in backend/tests
        test_files = list((ROOT / "backend" / "tests").glob("test_*.py"))
        test_path = test_files[0] if test_files else None

    if not test_path:
        print("  ✗ No test files found in backend/tests.")
        return False

    cmd = [sys.executable, "-m", "pytest", str(test_path), "-q"]
    try:
        proc = subprocess.run(
            cmd,
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=120,
        )
        if proc.returncode == 0:
            first_line = proc.stdout.strip().split("\n")[-1] if proc.stdout else "Passed"
            print(f"  ✓ Pytest runs successfully ({first_line}).")
            return True
        else:
            print("  ✗ Pytest encountered errors:")
            print(proc.stdout.strip() or proc.stderr.strip())
            return False
    except Exception as e:
        print(f"  ✗ Error running pytest: {e}")
        return False


def check_frontend_build():
    print("\n3. Testing Frontend Build (npm run build):")
    frontend_dir = ROOT / "frontend"
    if not frontend_dir.is_dir():
        print("  ✗ frontend directory not found.")
        return False

    # Cross-platform npm resolution (npm.cmd on Windows, npm on Unix)
    npm_bin = shutil.which("npm") or shutil.which("npm.cmd")
    if not npm_bin:
        print("  [WARN] 'npm' executable not found in PATH. Skipping frontend build.")
        return False

    cmd = [npm_bin, "run", "build"]
    try:
        proc = subprocess.run(
            cmd,
            cwd=frontend_dir,
            capture_output=True,
            text=True,
            timeout=90,
            shell=(sys.platform == "win32"),  # Shell required on Windows for .cmd batch files
        )
        if proc.returncode == 0:
            print("  ✓ Frontend production build succeeded.")
            return True
        else:
            print("  ✗ Frontend build failed:")
            print(proc.stderr.strip() or proc.stdout.strip())
            return False
    except Exception as e:
        print(f"  ✗ Error executing frontend build: {e}")
        return False


def main():
    check_python_environment()
    libs_ok = check_library_versions()
    backend_ok = check_backend_import()
    tests_ok = check_tests()
    frontend_ok = check_frontend_build()

    print("\n" + "=" * 70)
    print("Summary of Command Verification:")
    print(f"  Libraries Installed : {'PASS' if libs_ok else 'FAIL'}")
    print(f"  Backend App Import  : {'PASS' if backend_ok else 'FAIL'}")
    print(f"  Test Runner (pytest): {'PASS' if tests_ok else 'FAIL'}")
    print(f"  Frontend Build (Vite): {'PASS' if frontend_ok else 'FAIL'}")
    print("=" * 70)

    if all([libs_ok, backend_ok, tests_ok, frontend_ok]):
        print("Status: ALL SYSTEMS GO. CommShield is verified operational.")
        return 0
    else:
        print("Status: SOME CHECKS FAILED. See details above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
