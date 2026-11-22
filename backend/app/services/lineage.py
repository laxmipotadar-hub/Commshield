"""CommShield Lineage Provenance Engine and Adapter Interface.

Maintains a tamper-evident, append-only cryptographic audit chain (SHA-256 hash chaining)
for all model lifecycle mutations:
1. Candidate Baseline Creation (features, training windows, parent version hash)
2. Graduated Governance Decisions (Tier 1 Auto-Approve, Tier 2 Flag, Tier 3 Quarantine)
3. Atomic Rollbacks to Anchor or Previous Stable Baselines

Engineering Design:
- Each event block contains: index, timestamp, event_type, payload, prev_hash, and current_hash.
- Block hash is computed as: SHA-256(prev_hash + index + timestamp + event_type + canon_payload).
- Provides audit-grade provenance verification and export for compliance with 5G security standards.
- Fully compatible with Ubuntu and Windows environments.
"""

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import hashlib
import json
import logging
from pathlib import Path
import threading
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("commshield.lineage")

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
PROVENANCE_DIR = PROJECT_ROOT / "data" / "provenance"
LEDGER_FILE = PROVENANCE_DIR / "lineage_ledger.jsonl"

GENESIS_HASH = "0" * 64


@dataclass
class LineageBlock:
    """A single immutable block in the SHA-256 provenance chain."""
    index: int
    timestamp: str
    event_type: str
    slice_id: str
    payload: Dict[str, Any]
    prev_hash: str
    current_hash: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def compute_block_hash(
    index: int,
    timestamp: str,
    event_type: str,
    slice_id: str,
    payload: Dict[str, Any],
    prev_hash: str,
) -> str:
    """Compute deterministic SHA-256 hash for a block."""
    canon_payload = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    raw_str = f"{index}|{timestamp}|{event_type}|{slice_id}|{canon_payload}|{prev_hash}"
    return hashlib.sha256(raw_str.encode("utf-8")).hexdigest()


class LineageProvenanceAdapter:
    """Tamper-evident cryptographic ledger for CommShield adaptive governance events."""

    def __init__(self, ledger_path: Path = LEDGER_FILE):
        self.ledger_path = ledger_path
        self._lock = threading.Lock()
        self._chain: List[LineageBlock] = []
        self._initialize_ledger()

    def _initialize_ledger(self) -> None:
        """Load existing ledger from disk or initialize genesis block."""
        with self._lock:
            self._chain = []
            try:
                self.ledger_path.parent.mkdir(parents=True, exist_ok=True)
                if self.ledger_path.exists():
                    with open(self.ledger_path, "r", encoding="utf-8") as f:
                        for line in f:
                            line = line.strip()
                            if line:
                                data = json.loads(line)
                                block = LineageBlock(
                                    index=data["index"],
                                    timestamp=data["timestamp"],
                                    event_type=data["event_type"],
                                    slice_id=data.get("slice_id", "all"),
                                    payload=data["payload"],
                                    prev_hash=data["prev_hash"],
                                    current_hash=data["current_hash"],
                                )
                                self._chain.append(block)
                if not self._chain:
                    # Append Genesis Block
                    now_iso = datetime.now(timezone.utc).isoformat()
                    genesis_payload = {"message": "CommShield Provenance Genesis Anchor", "version": "1.0.0"}
                    gen_hash = compute_block_hash(
                        index=0,
                        timestamp=now_iso,
                        event_type="GENESIS",
                        slice_id="system",
                        payload=genesis_payload,
                        prev_hash=GENESIS_HASH,
                    )
                    gen_block = LineageBlock(
                        index=0,
                        timestamp=now_iso,
                        event_type="GENESIS",
                        slice_id="system",
                        payload=genesis_payload,
                        prev_hash=GENESIS_HASH,
                        current_hash=gen_hash,
                    )
                    self._chain.append(gen_block)
                    self._append_to_file(gen_block)
            except Exception as e:
                logger.error(f"Failed to initialize lineage ledger: {e}")

    def _append_to_file(self, block: LineageBlock) -> None:
        """Append serialized block to jsonl ledger file."""
        with open(self.ledger_path, "a", encoding="utf-8", newline="\n") as f:
            f.write(json.dumps(block.to_dict(), sort_keys=True) + "\n")

    def append_event(
        self,
        event_type: str,
        slice_id: str,
        payload: Dict[str, Any],
    ) -> LineageBlock:
        """Cryptographically append an event to the lineage chain."""
        with self._lock:
            last_block = self._chain[-1] if self._chain else None
            prev_hash = last_block.current_hash if last_block else GENESIS_HASH
            new_index = len(self._chain)
            timestamp = datetime.now(timezone.utc).isoformat()

            cur_hash = compute_block_hash(
                index=new_index,
                timestamp=timestamp,
                event_type=event_type,
                slice_id=slice_id,
                payload=payload,
                prev_hash=prev_hash,
            )

            block = LineageBlock(
                index=new_index,
                timestamp=timestamp,
                event_type=event_type,
                slice_id=slice_id,
                payload=payload,
                prev_hash=prev_hash,
                current_hash=cur_hash,
            )

            self._chain.append(block)
            self._append_to_file(block)
            logger.info(f"Recorded provenance event '{event_type}' block #{new_index} (hash: {cur_hash[:12]}...)")
            return block

    def record_candidate_created(
        self,
        candidate_id: str,
        candidate_version: str,
        parent_version: str,
        slice_id: str,
        window_count: int,
        feature_hash: Optional[str] = None,
    ) -> LineageBlock:
        """Record candidate baseline creation in the ledger."""
        payload = {
            "candidate_id": candidate_id,
            "candidate_version": candidate_version,
            "parent_version": parent_version,
            "slice_id": slice_id,
            "window_count": window_count,
            "feature_hash": feature_hash or "",
        }
        return self.append_event("CANDIDATE_CREATED", slice_id, payload)

    def record_governance_decision(
        self,
        candidate_id: str,
        candidate_version: Optional[str],
        parent_version: str,
        slice_id: str,
        tier: str,
        action: str,
        explanation: str,
        jsd_score: float,
    ) -> LineageBlock:
        """Record graduated governance decision (Tier 1, Tier 2, or Tier 3)."""
        payload = {
            "candidate_id": candidate_id,
            "candidate_version": candidate_version,
            "parent_version": parent_version,
            "slice_id": slice_id,
            "tier": tier,
            "action": action,
            "explanation": explanation,
            "jsd_score": jsd_score,
        }
        return self.append_event("GOVERNANCE_DECISION", slice_id, payload)

    def record_rollback(
        self,
        slice_id: str,
        from_version: str,
        to_version: str,
        reason: str,
        analyst_id: str,
    ) -> LineageBlock:
        """Record an atomic rollback event."""
        payload = {
            "slice_id": slice_id,
            "from_version": from_version,
            "to_version": to_version,
            "reason": reason,
            "analyst_id": analyst_id,
        }
        return self.append_event("ATOMIC_ROLLBACK", slice_id, payload)

    def verify_integrity(self) -> Tuple[bool, Optional[str]]:
        """Verify full cryptographic SHA-256 integrity of the ledger chain."""
        with self._lock:
            for i, block in enumerate(self._chain):
                if i == 0:
                    expected_prev = GENESIS_HASH
                else:
                    expected_prev = self._chain[i - 1].current_hash

                if block.prev_hash != expected_prev:
                    return False, f"Broken chain at block #{block.index}: prev_hash mismatch"

                recomputed = compute_block_hash(
                    index=block.index,
                    timestamp=block.timestamp,
                    event_type=block.event_type,
                    slice_id=block.slice_id,
                    payload=block.payload,
                    prev_hash=block.prev_hash,
                )
                if block.current_hash != recomputed:
                    return False, f"Tampered block #{block.index}: hash mismatch ({block.current_hash} != {recomputed})"

            return True, None

    def get_blocks(self, slice_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Retrieve verified blocks, optionally filtered by S-NSSAI slice."""
        with self._lock:
            if not slice_id or slice_id.lower() == "all":
                return [b.to_dict() for b in self._chain]
            return [b.to_dict() for b in self._chain if b.slice_id in (slice_id, "system", "all")]


# Global singleton instance
lineage_adapter = LineageProvenanceAdapter()
# CommShield AI Core
