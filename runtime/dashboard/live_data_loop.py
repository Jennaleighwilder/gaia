"""
Background refresh on the web worker: TESS, surface METAR, soundings, and fire layer JSON.

Render/Railway single-process gunicorn does not run gaia_daemon by default; without this,
AO/Gulf and surface panels stay empty or frozen from whatever was committed in runs/.

The fire dashboard (FIRMS count, double-threat hollows, KAVL wx) reads data/fire/*.json.
Those files were only updated when someone ran scripts/fire/fire_ingest.py — so counts
stayed frozen at repo snapshot. We periodically re-run ingest + fire_risk_layer here.

Enable by default; set GAIA_LIVE_REFRESH=0 to disable.
"""

from __future__ import annotations

import logging
import os
import subprocess
import sys
import threading
import time
from pathlib import Path

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[2]


def _run_tess_cron() -> None:
    argv_bak = sys.argv[:]
    try:
        sys.argv = ["live_tess_score.py", "--cron"]
        from scripts import live_tess_score

        live_tess_score.main()
    finally:
        sys.argv = argv_bak


def _run_surface_cron() -> None:
    argv_bak = sys.argv[:]
    try:
        sys.argv = ["fetch_live_surface.py", "--cron"]
        from scripts import fetch_live_surface

        fetch_live_surface.main()
    finally:
        sys.argv = argv_bak


def _run_soundings() -> None:
    from runtime.data.sounding_client import fetch_all_soundings

    fetch_all_soundings()


def _run_fire_pipeline() -> None:
    """Refresh NASA FIRMS + SPC + NWS + overlay JSON under data/fire/."""
    steps = (
        ROOT / "scripts" / "fire" / "fire_ingest.py",
        ROOT / "scripts" / "fire" / "fire_risk_layer.py",
    )
    for script in steps:
        r = subprocess.run(
            [sys.executable, str(script)],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            timeout=int(os.environ.get("GAIA_FIRE_PIPELINE_TIMEOUT_SEC", "480")),
            env=os.environ.copy(),
        )
        if r.returncode != 0:
            tail = (r.stderr or r.stdout or "").strip()[-600:]
            raise RuntimeError(f"{script.name} exit {r.returncode}: {tail}")


def start_live_data_refresh_thread() -> None:
    raw = os.environ.get("GAIA_LIVE_REFRESH", "1").strip().lower()
    if raw in ("0", "false", "no", "off"):
        logger.info("GAIA live refresh disabled (GAIA_LIVE_REFRESH=%s)", raw)
        return

    tess_sec = int(os.environ.get("GAIA_LIVE_TESS_INTERVAL_SEC", "900"))
    surface_sec = int(os.environ.get("GAIA_LIVE_SURFACE_INTERVAL_SEC", "600"))
    sound_sec = int(os.environ.get("GAIA_LIVE_SOUNDINGS_INTERVAL_SEC", "1800"))
    fire_sec = int(os.environ.get("GAIA_LIVE_FIRE_INTERVAL_SEC", "900"))

    def loop() -> None:
        if str(ROOT) not in sys.path:
            sys.path.insert(0, str(ROOT))
        boot = time.monotonic()
        next_tess = next_surface = next_sound = boot
        next_fire = boot + fire_sec
        logger.info(
            "GAIA live refresh started (TESS %ss, surface %ss, soundings %ss, fire %ss); FIRMS_MAP_KEY=%s",
            tess_sec,
            surface_sec,
            sound_sec,
            fire_sec,
            "set" if os.environ.get("FIRMS_MAP_KEY", "").strip() else "MISSING",
        )
        try:
            _run_fire_pipeline()
            logger.info("Refreshed data/fire (FIRMS + fire_risk_overlay) [boot]")
        except Exception as e:
            logger.warning("fire pipeline failed (boot): %s", e)
        while True:
            now = time.monotonic()
            if now >= next_tess:
                try:
                    _run_tess_cron()
                    logger.info("Refreshed runs/live_tess.json")
                except Exception as e:
                    logger.warning("live_tess refresh failed: %s", e)
                next_tess = now + tess_sec
            if now >= next_surface:
                try:
                    _run_surface_cron()
                    logger.info("Refreshed runs/live_surface.json")
                except Exception as e:
                    logger.warning("live_surface refresh failed: %s", e)
                next_surface = now + surface_sec
            if now >= next_sound:
                try:
                    _run_soundings()
                    logger.info("Refreshed runs/live_soundings.json")
                except Exception as e:
                    logger.warning("soundings refresh failed: %s", e)
                next_sound = now + sound_sec
            if now >= next_fire:
                try:
                    _run_fire_pipeline()
                    logger.info("Refreshed data/fire (FIRMS + fire_risk_overlay)")
                except Exception as e:
                    logger.warning("fire pipeline failed: %s", e)
                next_fire = now + fire_sec
            time.sleep(30)

    t = threading.Thread(target=loop, name="gaia-live-data", daemon=True)
    t.start()
