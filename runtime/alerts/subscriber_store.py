"""
Append-only JSON store for alert signups: runs/subscribers.json on Railway.
"""

from __future__ import annotations

import json
import os
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
_lock = threading.Lock()

DEFAULT_PATH = ROOT / "runs" / "subscribers.json"


def subscribers_path() -> Path:
    p = os.environ.get("GAIA_SUBSCRIBERS_PATH")
    return Path(p) if p else DEFAULT_PATH


def _ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def load_subscribers() -> list[dict]:
    path = subscribers_path()
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except Exception:
        return []


def append_subscriber(record: dict) -> int:
    """Append one subscriber; dedupe by email (keep latest). Returns new total count."""
    with _lock:
        path = subscribers_path()
        _ensure_parent(path)
        rows = load_subscribers()
        email = record.get("email", "").lower()
        rows = [r for r in rows if (r.get("email") or "").lower() != email]
        rows.append(record)
        path.write_text(json.dumps(rows, indent=2) + "\n", encoding="utf-8")
        return len(rows)
