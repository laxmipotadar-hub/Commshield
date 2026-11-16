"""Standalone CLI script to reset runtime database tables while preserving calibrated anchor baselines."""

import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.database import SessionLocal
from backend.app.services.system import reset_runtime_database


def main():
    db = SessionLocal()
    try:
        print("[reset_db] Clearing runtime tables and resetting replay engine...")
        res = reset_runtime_database(db=db)
        print(f"[reset_db] Success: {res['message']}")
        for table, count in res["cleared_records"].items():
            if count > 0:
                print(f"  - {table}: {count} rows deleted")
    finally:
        db.close()


if __name__ == "__main__":
    main()
