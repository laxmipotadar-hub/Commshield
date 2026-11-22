"""Read-only Digital Twin Provisioning and Change Events Loader.

Enforces cryptographic pseudonymisation of subscriber identities via HMAC-SHA256,
preventing raw SIM/UE identifiers from ever being exposed to models, logs, or APIs.
"""

from datetime import datetime, timezone
import hashlib
import hmac
import json
import os
from pathlib import Path
from types import MappingProxyType
from typing import Any, Dict, List, Optional, Set, Union

from .schema import parse_iso_timestamp

DEFAULT_TWIN_HMAC_SALT = b"commshield-twin-pseudonymization-default-salt-v1"


def get_twin_hmac_secret() -> bytes:
    """Retrieve HMAC secret key from environment or fallback safely."""
    # Check .env first via manual read if python-dotenv is not installed
    env_file = Path(__file__).resolve().parent.parent.parent / ".env"
    if env_file.is_file():
        try:
            with open(env_file, "r", encoding="utf-8", newline="\n") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        k, v = k.strip(), v.strip()
                        if k not in os.environ:
                            os.environ[k] = v
        except Exception:
            pass

    secret = os.getenv("COMMSHIELD_TWIN_HMAC_KEY") or os.getenv("COMMSHIELD_HMAC_KEY")
    if secret:
        return secret.encode("utf-8")
    return DEFAULT_TWIN_HMAC_SALT


def hash_sim_id(identifier: str, key: Optional[Union[bytes, str]] = None) -> str:
    """Hash a SIM identifier using HMAC-SHA256, returning a 64-character lowercase hex string."""
    if not identifier:
        return ""
    if key is None:
        hmac_key = get_twin_hmac_secret()
    elif isinstance(key, str):
        hmac_key = key.encode("utf-8")
    else:
        hmac_key = key
    return hmac.new(hmac_key, identifier.encode("utf-8"), hashlib.sha256).hexdigest()


class ProvisioningLoader:
    """Read-only loader for digital twin provisioning and change events."""

    def __init__(
        self,
        data_dir: Optional[Union[str, Path]] = None,
        key: Optional[Union[bytes, str]] = None,
    ):
        if data_dir is None:
            self._data_dir = Path(__file__).resolve().parent.parent.parent / "data" / "twin"
        else:
            self._data_dir = Path(data_dir)

        if key is None:
            self._key = get_twin_hmac_secret()
        elif isinstance(key, str):
            self._key = key.encode("utf-8")
        else:
            self._key = key

        self._sim_by_hash: Dict[str, Dict[str, Any]] = {}
        self._raw_to_hash: Dict[str, str] = {}
        self._events: List[Dict[str, Any]] = []

        self._load_data()

        # Freeze lookup maps for read-only safety
        self._sim_by_hash_view = MappingProxyType(self._sim_by_hash)
        self._events_view = tuple(self._events)

    def _load_data(self) -> None:
        """Load provisioning and event records."""
        prov_file = self._data_dir / "provisioning.json"
        events_file = self._data_dir / "change_events.json"

        if not prov_file.is_file():
            raise FileNotFoundError(f"Provisioning file not found: {prov_file}")
        if not events_file.is_file():
            raise FileNotFoundError(f"Change events file not found: {events_file}")

        with open(prov_file, "r", encoding="utf-8", newline="\n") as f:
            prov_data = json.load(f)

        for sim in prov_data.get("sims", []):
            raw_id = sim["sim_id"]
            h_id = hash_sim_id(raw_id, self._key)
            self._raw_to_hash[raw_id] = h_id
            self._sim_by_hash[h_id] = {
                "device_class": sim["device_class"],
                "slice": sim["slice"],
                "status": sim.get("status", "provisioned"),
                "provisioned_at": sim.get("provisioned_at"),
            }

        with open(events_file, "r", encoding="utf-8", newline="\n") as f:
            events_data = json.load(f)

        for batch in events_data.get("batches", []):
            start_dt = parse_iso_timestamp(batch["start"])
            end_dt = parse_iso_timestamp(batch["end"])
            hashed_ids = set()
            for raw_sim in batch.get("sim_ids", []):
                h_id = self._raw_to_hash.get(raw_sim) or hash_sim_id(raw_sim, self._key)
                hashed_ids.add(h_id)

            self._events.append({
                "batch_id": batch["batch_id"],
                "start": start_dt,
                "end": end_dt,
                "count": batch["count"],
                "slice": batch["slice"],
                "device_class": batch.get("device_class"),
                "hashed_sim_ids": frozenset(hashed_ids),
            })

    @property
    def total_provisioned(self) -> int:
        """Total number of provisioned SIMs."""
        return len(self._sim_by_hash)

    @property
    def total_batches(self) -> int:
        """Total number of onboarding batches."""
        return len(self._events)

    def get_hashed_ids_for_class(self, device_class: str) -> List[str]:
        """Return all hashed SIM IDs for a specific device class."""
        return sorted([
            h_id for h_id, info in self._sim_by_hash.items()
            if info["device_class"] == device_class
        ])

    def get_all_hashed_ids(self) -> List[str]:
        """Return all provisioned hashed SIM IDs."""
        return sorted(list(self._sim_by_hash.keys()))

    def lookup(
        self,
        id: str,
        time: Union[datetime, str],
    ) -> Dict[str, Any]:
        """Lookup a SIM identity at a specific timestamp.
        
        Accepts either a raw SIM string ID or an already-hashed HMAC-SHA256 hex digest.
        
        Returns:
            Dict containing:
                "provisioned": bool
                "device_class": Optional[str]
                "slice": Optional[str]
                "event_id": Optional[str] (batch_id if active event covers id at time, else None)
        """
        if not id or not isinstance(id, str):
            return {
                "provisioned": False,
                "device_class": None,
                "slice": None,
                "event_id": None,
            }

        # Resolve to hashed ID
        if id in self._sim_by_hash:
            h_id = id
        elif id in self._raw_to_hash:
            h_id = self._raw_to_hash[id]
        else:
            cand_hash = hash_sim_id(id, self._key)
            if cand_hash in self._sim_by_hash:
                h_id = cand_hash
            else:
                return {
                    "provisioned": False,
                    "device_class": None,
                    "slice": None,
                    "event_id": None,
                }

        info = self._sim_by_hash[h_id]
        dt = parse_iso_timestamp(time)

        # Check active change events covering dt
        active_event_id: Optional[str] = None
        for event in self._events:
            if event["start"] <= dt <= event["end"]:
                if h_id in event["hashed_sim_ids"]:
                    active_event_id = event["batch_id"]
                    break

        return {
            "provisioned": True,
            "device_class": info["device_class"],
            "slice": info["slice"],
            "event_id": active_event_id,
        }
# CommShield AI Core
