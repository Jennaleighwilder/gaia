"""
GAIA Bus client — publish and replay from a local SQLite WAL event log.

Phase 1 keeps the West-OS append-only structure but writes directly to the
GAIA bus DB so the scaffold can run without a separate scribe process.
"""
import json
import os
import sqlite3
import threading
from datetime import datetime
from typing import Callable, Generator, Optional

from .schema import GaiaEvent, create_event

BUS_DIR = os.environ.get("GAIA_BUS_DIR", os.path.expanduser("~/gaia/runtime/bus"))
DB_PATH = os.environ.get("GAIA_DB_PATH", os.environ.get("GAIA_DB", os.path.join(BUS_DIR, "bus.db")))
_LOCK = threading.Lock()
_CONN: Optional[sqlite3.Connection] = None


def _get_conn() -> sqlite3.Connection:
    global _CONN
    if _CONN is None:
        init_bus()
    return _CONN


def init_bus() -> sqlite3.Connection:
    """Create bus directory and SQLite DB. Read-only connection for replay."""
    global _CONN
    db_path = os.path.abspath(os.path.expanduser(DB_PATH))
    db_dir = os.path.dirname(db_path)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)
    os.makedirs(os.path.abspath(os.path.expanduser(BUS_DIR)), exist_ok=True)
    conn = sqlite3.connect(db_path, check_same_thread=False, timeout=30)
    conn.execute("PRAGMA busy_timeout = 30000")
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS events (
            seq INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            source TEXT NOT NULL,
            source_version TEXT,
            event_type TEXT NOT NULL,
            payload_json TEXT,
            context_json TEXT,
            metrics_json TEXT,
            previous_hash TEXT,
            event_hash TEXT NOT NULL,
            created_at TEXT DEFAULT (datetime('now'))
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_events_source ON events(source)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_events_type ON events(event_type)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_events_timestamp ON events(timestamp)")
    conn.commit()
    _CONN = conn
    return conn


def publish(ev: GaiaEvent) -> int:
    """Append an event directly to the GAIA bus."""
    with _LOCK:
        conn = _get_conn()
        cur = conn.execute(
            """
            INSERT INTO events (
                event_id, timestamp, source, source_version, event_type,
                payload_json, context_json, metrics_json, previous_hash, event_hash
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                ev.event_id,
                ev.timestamp.isoformat(),
                ev.source,
                ev.source_version,
                ev.event_type,
                json.dumps(ev.payload or {}),
                json.dumps(ev.context or {}),
                json.dumps(ev.metrics or {}),
                ev.previous_hash,
                ev.event_hash,
            ),
        )
        conn.commit()
        return int(cur.lastrowid)


def get_last_hash() -> str:
    """Last event_hash in bus. Used for chaining next event."""
    with _LOCK:
        conn = _get_conn()
        row = conn.execute(
            "SELECT event_hash FROM events ORDER BY seq DESC LIMIT 1"
        ).fetchone()
        return row[0] if row else "GENESIS"


def count_events() -> int:
    """Total number of events in the append-only bus."""
    with _LOCK:
        conn = _get_conn()
        row = conn.execute("SELECT COALESCE(MAX(seq), 0) FROM events").fetchone()
        return int(row[0]) if row else 0


def replay(from_seq: int = 0, limit: Optional[int] = None) -> Generator[GaiaEvent, None, None]:
    """
    Replay events from offset. Yields GaiaEvent.
    from_seq=0 means from first event.
    """
    for _seq, ev in replay_with_seq(from_seq=from_seq, limit=limit):
        yield ev


def get_recent_events_for_claim(claim_id: str, limit: int = 20) -> list:
    """
    Return the most recent `limit` events for claim_id (chronological order, newest last).
    Used by governor for sequence-pattern matching (e.g. "X → Y" rules).
    """
    if not claim_id or claim_id == "unknown":
        return []
    conn = _get_conn()
    try:
        sql = """
            SELECT * FROM events
            WHERE json_extract(context_json, '$.claim_id') = ? OR json_extract(context_json, '$.client_id') = ?
               OR json_extract(payload_json, '$.claim_id') = ?
            ORDER BY seq DESC
            LIMIT ?
        """
        rows = list(conn.execute(sql, [claim_id, claim_id, claim_id, limit]))
        rows = list(reversed(rows))  # chronological: oldest first
        return [_row_to_event(r) for r in rows if _row_to_event(r)]
    except sqlite3.OperationalError:
        # Fallback: Python filter
        total = count_events()
        from_seq = max(0, total - 500)
        out = []
        for _seq, ev in replay_with_seq(from_seq=from_seq, limit=500, claim_id=claim_id):
            out.append(ev)
        return out[-limit:] if len(out) > limit else out


def get_recent_event(event_type: str, claim_id: Optional[str] = None, limit: int = 500) -> Optional[GaiaEvent]:
    """
    Get the most recent event of type event_type, optionally filtered by claim_id.
    Used by governor to read mirror_coherence, etc.
    """
    total = count_events()
    from_seq = max(0, total - limit)
    last_match = None
    for _seq, ev in replay_with_seq(from_seq=from_seq, limit=limit):
        if ev.event_type != event_type:
            continue
        if claim_id:
            ctx = ev.context or {}
            payload = ev.payload or {}
            cid = payload.get("claim_id") or ctx.get("claim_id") or ctx.get("client_id")
            if cid != claim_id:
                continue
        last_match = ev
    return last_match


def replay_with_seq(from_seq: int = 0, limit: Optional[int] = None, claim_id: Optional[str] = None) -> Generator[tuple, None, None]:
    """
    Replay events from offset. Yields (seq, GaiaEvent).
    Use seq for resuming: pass last_seq + 1 as from_seq on next poll.
    If claim_id provided, filter to events with matching claim_id or client_id in context.
    """
    conn = _get_conn()
    if claim_id:
        try:
            sql = """
                SELECT * FROM events WHERE seq > ?
                AND (json_extract(context_json, '$.claim_id') = ? OR json_extract(context_json, '$.client_id') = ?)
                ORDER BY seq
            """
            args: list = [from_seq, claim_id, claim_id]
            if limit is not None:
                sql += " LIMIT ?"
                args.append(limit)
            for row in conn.execute(sql, args):
                seq = row[0]
                ev = _row_to_event(row)
                if ev:
                    yield (seq, ev)
            return
        except sqlite3.OperationalError:
            pass  # json_extract not available, fall through to Python filter
        # Fallback: filter in Python
        sql = "SELECT * FROM events WHERE seq > ? ORDER BY seq"
        args = [from_seq]
        if limit is not None:
            sql += " LIMIT ?"
            args.append(limit)
        for row in conn.execute(sql, args):
            seq = row[0]
            ev = _row_to_event(row)
            if ev:
                ctx = ev.context or {}
                if ctx.get("claim_id") == claim_id or ctx.get("client_id") == claim_id:
                    yield (seq, ev)
        return

    sql = "SELECT * FROM events WHERE seq > ? ORDER BY seq"
    args = [from_seq]
    if limit is not None:
        sql += " LIMIT ?"
        args.append(limit)
    for row in conn.execute(sql, args):
        seq = row[0]
        ev = _row_to_event(row)
        if ev:
            yield (seq, ev)


def _safe_json(s, default=None):
    """Parse JSON, return default on empty/invalid."""
    if default is None:
        default = {}
    raw = (s or "").strip()
    if not raw:
        return default
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return default


def _row_to_event(row) -> Optional[GaiaEvent]:
    try:
        return GaiaEvent(
            event_id=row[1],
            timestamp=datetime.fromisoformat(row[2].replace("Z", "+00:00")),
            source=row[3],
            source_version=row[4] or "1.0",
            event_type=row[5],
            payload=_safe_json(row[6]),
            context=_safe_json(row[7]),
            metrics=_safe_json(row[8]),
            previous_hash=row[9] or "",
            event_hash=row[10],
        )
    except Exception:
        return None


def subscribe(
    callback: Callable[[GaiaEvent], None],
    from_seq: int = 0,
    poll_interval: float = 2.0,
) -> None:
    """
    Poll bus and invoke callback for each new event. Blocks.
    Use from_seq to resume; pass last processed seq + 1.
    """
    import time
    seq = from_seq
    while True:
        for ev in replay(from_seq=seq, limit=100):
            callback(ev)
            seq = _seq_for_event(ev)
        time.sleep(poll_interval)


def _seq_for_event(ev: GaiaEvent) -> int:
    """Get seq for event (from DB)."""
    conn = _get_conn()
    row = conn.execute(
        "SELECT seq FROM events WHERE event_id = ?",
        (ev.event_id,),
    ).fetchone()
    return row[0] if row else 0


def publish_simple(
    source: str,
    event_type: str,
    payload: dict,
    context: Optional[dict] = None,
    metrics: Optional[dict] = None,
) -> int:
    """Convenience helper that chains and persists a new event."""
    ev = create_event(
        source=source,
        event_type=event_type,
        payload=payload,
        previous_hash=get_last_hash(),
        context=context or {},
        metrics=metrics or {},
    )
    return publish(ev)
