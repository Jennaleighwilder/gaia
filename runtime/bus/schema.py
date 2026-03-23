"""
GAIA Bus — Event envelope schema.
All components publish GaiaEvents; the governor consumes normalized metrics.
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional
import hashlib
import json
import uuid


@dataclass
class GaiaEvent:
    """
    Unified event envelope for GAIA.
    source keeps native identity; metrics provides normalized cross-cutting scores.
    """
    event_id: str
    timestamp: datetime
    source: str
    source_version: str
    event_type: str
    payload: dict
    context: dict
    metrics: dict
    previous_hash: str
    event_hash: str

    def to_dict(self) -> dict:
        return {
            "event_id": self.event_id,
            "timestamp": self.timestamp.isoformat(),
            "source": self.source,
            "source_version": self.source_version,
            "event_type": self.event_type,
            "payload": self.payload,
            "context": self.context,
            "metrics": self.metrics,
            "previous_hash": self.previous_hash,
            "event_hash": self.event_hash,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "GaiaEvent":
        ts = d.get("timestamp")
        if isinstance(ts, str):
            ts = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        return cls(
            event_id=d["event_id"],
            timestamp=ts,
            source=d["source"],
            source_version=d.get("source_version", "1.0"),
            event_type=d["event_type"],
            payload=d.get("payload", {}),
            context=d.get("context", {}),
            metrics=d.get("metrics", {}),
            previous_hash=d.get("previous_hash", ""),
            event_hash=d["event_hash"],
        )


def ulid_like() -> str:
    """Simple ULID-like id: timestamp hex + random hex."""
    t = int(datetime.now(timezone.utc).timestamp() * 1000)
    r = uuid.uuid4().hex[:12]
    return f"{t:012x}{r}"


def compute_event_hash(ev: dict) -> str:
    """SHA256 of canonical JSON (excluding event_hash for computation)."""
    copy = {k: v for k, v in ev.items() if k != "event_hash"}
    canonical = json.dumps(copy, sort_keys=True)
    return hashlib.sha256(canonical.encode()).hexdigest()


def create_event(
    source: str,
    event_type: str,
    payload: dict,
    previous_hash: str,
    context: Optional[dict] = None,
    metrics: Optional[dict] = None,
    source_version: str = "1.0",
) -> GaiaEvent:
    """
    Build a GaiaEvent with correct hashing.
    """
    ev = {
        "event_id": ulid_like(),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "source": source,
        "source_version": source_version,
        "event_type": event_type,
        "payload": payload,
        "context": context or {},
        "metrics": metrics or {},
        "previous_hash": previous_hash,
        "event_hash": "",
    }
    ev["event_hash"] = compute_event_hash(ev)
    return GaiaEvent.from_dict(ev)
