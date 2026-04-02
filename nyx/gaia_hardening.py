"""
NYX :: GAIA HARDENING
Patches for the loose threads found in the expedition.

LOOSE THREADS IDENTIFIED:
  1. _fetch_json/_fetch_text: no retry, one failure = silent loss
  2. DataSource: no circuit breaker, no exponential backoff
  3. _run_source: if thread dies silently, source goes dark forever
  4. SQLite: new connection per county per cycle, no pooling, lock risk
  5. water.noaa.gov: zero security headers, most exposed dependency
  6. archive-api.open-meteo.com: timing out, era5 scripts silently fail
  7. No watchdog: daemon dies, nothing restarts it
  8. No ladder fallback: when primary source fails, no fallback tried

FIX STRATEGY: Each fix is a drop-in wrapper or patch.
Jennifer applies them without rewriting the daemon from scratch.

© 2026 Jennifer Leigh West. All rights reserved.
"""

from __future__ import annotations
import json, logging, os, sqlite3, threading, time, urllib.request, urllib.error
from contextlib import contextmanager
from typing import Any, Callable, Optional
from pathlib import Path

logger = logging.getLogger("gaia.hardened")


# ── FIX 1: Retry-with-backoff fetch ─────────────────────────────────────────
# Drop-in replacement for _fetch_json in data_cache.py
# Tries up to 3 times with exponential backoff before giving up.

def fetch_json_hardened(url: str, timeout: int = 30,
                        retries: int = 3, backoff_base: float = 2.0) -> Optional[dict]:
    """Fetch JSON with retry and exponential backoff. Drop-in for _fetch_json."""
    last_error = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "GAIA/1.0 (severe-weather; theforgottencode.com)"},
            )
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read().decode("utf-8", errors="replace"))
        except urllib.error.HTTPError as e:
            last_error = f"HTTP {e.code}"
            if e.code in (400, 401, 403, 404, 410):
                break  # Don't retry client errors
        except Exception as e:
            last_error = str(e)[:80]
        if attempt < retries - 1:
            wait = backoff_base ** attempt
            logger.debug("Retry %d/%d for %s after %.1fs", attempt + 2, retries, url[:60], wait)
            time.sleep(wait)
    logger.warning("FETCH FAILED after %d tries: %s — %s", retries, url[:60], last_error)
    return None


# ── FIX 2: Circuit Breaker ───────────────────────────────────────────────────
# Wraps a data source fetch function.
# After 3 consecutive failures, opens the circuit for 5 minutes.
# While open, returns None immediately (no wasted network calls).
# Tries to recover every 5 minutes (half-open state).

class CircuitBreaker:
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"

    def __init__(self, name: str, fail_threshold: int = 3,
                 recovery_timeout: float = 300.0):
        self.name = name
        self.fail_threshold = fail_threshold
        self.recovery_timeout = recovery_timeout
        self._state = self.CLOSED
        self._failures = 0
        self._opened_at: Optional[float] = None
        self._lock = threading.Lock()

    @property
    def state(self) -> str:
        with self._lock:
            if self._state == self.OPEN:
                if time.time() - self._opened_at > self.recovery_timeout:
                    self._state = self.HALF_OPEN
                    logger.info("Circuit %s → HALF_OPEN (testing recovery)", self.name)
            return self._state

    def call(self, fn: Callable, *args, **kwargs) -> Any:
        state = self.state
        if state == self.OPEN:
            logger.debug("Circuit %s OPEN — skipping call", self.name)
            return None
        try:
            result = fn(*args, **kwargs)
            with self._lock:
                if self._state == self.HALF_OPEN:
                    logger.info("Circuit %s → CLOSED (recovered)", self.name)
                self._state = self.CLOSED
                self._failures = 0
            return result
        except Exception as e:
            with self._lock:
                self._failures += 1
                if self._failures >= self.fail_threshold:
                    self._state = self.OPEN
                    self._opened_at = time.time()
                    logger.warning(
                        "Circuit %s → OPEN after %d failures. Last: %s",
                        self.name, self._failures, e
                    )
            return None


# ── FIX 3: Thread Watchdog ───────────────────────────────────────────────────
# Monitors daemon threads. If any die, restarts them.
# Run as a separate daemon thread. Check every 60 seconds.

class ThreadWatchdog:
    def __init__(self, check_interval: float = 60.0):
        self.check_interval = check_interval
        self._watched: list[tuple[str, Callable, threading.Thread]] = []
        self._stop = threading.Event()

    def watch(self, name: str, target_fn: Callable) -> threading.Thread:
        t = threading.Thread(target=target_fn, name=name, daemon=True)
        t.start()
        self._watched.append((name, target_fn, t))
        return t

    def start(self):
        watcher = threading.Thread(
            target=self._watchloop, name="ThreadWatchdog", daemon=True
        )
        watcher.start()
        logger.info("ThreadWatchdog started, monitoring %d threads", len(self._watched))

    def _watchloop(self):
        while not self._stop.is_set():
            for i, (name, fn, t) in enumerate(self._watched):
                if not t.is_alive():
                    logger.warning("Thread %s died — restarting", name)
                    new_t = threading.Thread(target=fn, name=name, daemon=True)
                    new_t.start()
                    self._watched[i] = (name, fn, new_t)
            self._stop.wait(self.check_interval)

    def stop(self):
        self._stop.set()


# ── FIX 4: SQLite Connection Pool ────────────────────────────────────────────
# The daemon opens a new SQLite connection for every county every 5 minutes.
# With 10 counties, that's 10 open/close cycles per loop.
# Use a single persistent connection with WAL mode for concurrent safety.

class GAIADatabase:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._conn: Optional[sqlite3.Connection] = None
        self._lock = threading.Lock()
        self._init()

    def _init(self):
        self._conn = sqlite3.connect(
            str(self.db_path),
            check_same_thread=False,
            timeout=10.0,
        )
        self._conn.execute("PRAGMA journal_mode=WAL")  # concurrent reads
        self._conn.execute("PRAGMA synchronous=NORMAL")  # safe but faster
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS decisions (
                id INTEGER PRIMARY KEY,
                timestamp TEXT,
                county TEXT,
                decision TEXT,
                confidence REAL,
                alert_json TEXT,
                created_at TEXT
            )
        """)
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS source_health (
                id INTEGER PRIMARY KEY,
                source TEXT,
                status TEXT,
                latency_ms REAL,
                checked_at TEXT
            )
        """)
        self._conn.commit()

    @contextmanager
    def transaction(self):
        with self._lock:
            try:
                yield self._conn
                self._conn.commit()
            except Exception as e:
                self._conn.rollback()
                logger.error("DB transaction failed: %s", e)
                raise

    def insert_decision(self, timestamp, county, decision, confidence, alert_json, created_at):
        with self.transaction() as conn:
            conn.execute(
                "INSERT INTO decisions (timestamp,county,decision,confidence,alert_json,created_at) VALUES (?,?,?,?,?,?)",
                (timestamp, county, decision, confidence, alert_json, created_at),
            )

    def log_source_health(self, source: str, status: str, latency_ms: float):
        with self.transaction() as conn:
            conn.execute(
                "INSERT INTO source_health (source,status,latency_ms,checked_at) VALUES (?,?,?,datetime('now'))",
                (source, status, latency_ms),
            )


# ── FIX 5: Ladder Fallback Fetch ─────────────────────────────────────────────
# When a primary source fails, try its known ladder.
# Maps primary URL patterns to fallback URL patterns.

FETCH_LADDERS = {
    "water.noaa.gov": "mrms.ncep.noaa.gov",
    "archive-api.open-meteo.com": "api.open-meteo.com",
    "api.weather.gov": "aviationweather.gov",
    "firms.modaps.eosdis.nasa.gov": "earthdata.nasa.gov",
}

def fetch_with_fallback(primary_url: str, fallback_fn: Optional[Callable] = None,
                        timeout: int = 30) -> Optional[dict]:
    """Try primary URL, fall back to alternative if it fails."""
    result = fetch_json_hardened(primary_url, timeout=timeout)
    if result is not None:
        return result
    for primary_domain, fallback_domain in FETCH_LADDERS.items():
        if primary_domain in primary_url:
            fallback_url = primary_url.replace(primary_domain, fallback_domain)
            logger.warning("Primary %s failed — trying ladder: %s",
                          primary_domain, fallback_domain)
            result = fetch_json_hardened(fallback_url, timeout=timeout)
            if result is not None:
                logger.info("Ladder succeeded: %s", fallback_domain)
                return result
    if fallback_fn:
        try:
            return fallback_fn()
        except Exception as e:
            logger.error("Fallback function also failed: %s", e)
    return None


# ── FIX 6: Source Health Monitor ─────────────────────────────────────────────
# Runs every 10 minutes, probes all GAIA critical sources,
# logs their health to the DB, warns if anything is degrading.

GAIA_SOURCES = {
    "api.weather.gov": "NWS alerts backbone",
    "firms.modaps.eosdis.nasa.gov": "NASA fire satellite",
    "water.noaa.gov": "Stage IV rainfall",
    "mrms.ncep.noaa.gov": "MRMS precipitation",
    "api.open-meteo.com": "Open-Meteo weather",
    "web-production-ce417.up.railway.app": "GAIA Railway API",
}

def probe_source_health(host: str, timeout: int = 8) -> tuple[bool, float, str]:
    """Returns (alive, latency_ms, note)."""
    import socket
    try:
        t0 = time.time()
        s = socket.create_connection((host, 443), timeout=timeout)
        s.close()
        latency = (time.time() - t0) * 1000
        return True, round(latency, 1), "ok"
    except Exception as e:
        return False, 0.0, str(e)[:60]

def run_source_health_check(db: Optional[GAIADatabase] = None) -> dict:
    results = {}
    for host, purpose in GAIA_SOURCES.items():
        alive, latency_ms, note = probe_source_health(host)
        results[host] = {"alive": alive, "latency_ms": latency_ms, "note": note}
        status = "ok" if alive else "dead"
        if db:
            try:
                db.log_source_health(host, status, latency_ms)
            except Exception:
                pass
        if not alive:
            logger.warning("SOURCE DEGRADED: %s (%s) — %s", host, purpose, note)
        elif latency_ms > 500:
            logger.warning("SOURCE SLOW: %s %.0fms", host, latency_ms)
    return results


# ── APPLY TO GAIA DAEMON ─────────────────────────────────────────────────────
# How to apply these fixes to the running daemon:
#
# In gaia_daemon.py, replace:
#   conn = sqlite3.connect(db_path) [per county]
#   conn.execute(...) [per county]
#   conn.commit() [per county]
#   conn.close() [per county]
#
# With:
#   db = GAIADatabase(db_path)  # once at startup
#   db.insert_decision(...)  # per county, thread-safe
#
# In data_cache.py, replace _fetch_json with fetch_json_hardened.
# Wrap each DataSource.fetch_fn with a CircuitBreaker.
# Start a ThreadWatchdog over the source threads.
# Run source health check every 10 minutes.

if __name__ == "__main__":
    print("GAIA Hardening — source health check")
    results = run_source_health_check()
    for host, r in results.items():
        icon = "✓" if r["alive"] else "✗"
        print(f"  {icon} {host}: {r['latency_ms']}ms {r['note']}")
