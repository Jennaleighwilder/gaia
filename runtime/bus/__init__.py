"""
GAIA Bus — Append-only event log for atmospheric observations and decisions.
SQLite WAL mode with replayable, hash-chained events.
"""
from .schema import GaiaEvent, create_event, compute_event_hash, ulid_like
from .client import publish, publish_simple, subscribe, replay, replay_with_seq, get_last_hash, init_bus, count_events, get_recent_event, get_recent_events_for_claim
from .normalize import normalize_instability, register_normalizer, list_normalizers

__all__ = [
    "GaiaEvent",
    "create_event",
    "compute_event_hash",
    "ulid_like",
    "publish",
    "publish_simple",
    "subscribe",
    "replay",
    "replay_with_seq",
    "get_recent_event",
    "get_recent_events_for_claim",
    "get_last_hash",
    "init_bus",
    "count_events",
    "normalize_instability",
    "register_normalizer",
    "list_normalizers",
]
