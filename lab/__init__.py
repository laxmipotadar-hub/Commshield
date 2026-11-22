"""CommShield Lab Integration Package.

Provides Open5GS and UERANSIM telemetry ingestion, HMAC identity pseudonymisation,
offline sample log replay, and canonical schema validation for 5G testbed environments.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .adapter import LabAdapter
    from .validate import validate_lab_windows_file

__all__ = ["LabAdapter", "validate_lab_windows_file"]


def __getattr__(name: str):
    if name == "LabAdapter":
        from .adapter import LabAdapter
        return LabAdapter
    elif name == "validate_lab_windows_file":
        from .validate import validate_lab_windows_file
        return validate_lab_windows_file
    raise AttributeError(f"module 'lab' has no attribute '{name}'")
# CommShield AI Core
