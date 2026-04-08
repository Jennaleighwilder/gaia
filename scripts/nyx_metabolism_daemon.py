#!/usr/bin/env python3
"""
Nyx metabolism only — continuous web gather → Void → birth loop.

Run this to let the substrate run without the full GAIA county evaluation loop.
Uses GAIADataCache by default so the membrane pulls live ASOS/FIRMS/USGS-style data.

  .venv/bin/python scripts/nyx_metabolism_daemon.py
  GAIA_NO_PROXY=1 .venv/bin/python scripts/nyx_metabolism_daemon.py

  .venv/bin/python scripts/nyx_metabolism_daemon.py --no-cache
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Nyx MetabolicDaemon in the foreground.")
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Do not start GAIADataCache; use standalone API transporters only.",
    )
    args = parser.parse_args()

    root = Path(__file__).resolve().parent.parent
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    os.chdir(root)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(message)s",
    )
    log = logging.getLogger("nyx_metabolism_daemon")

    cache = None
    if not args.no_cache:
        from runtime.cache.data_cache import GAIADataCache

        cache = GAIADataCache()
        cache.start()
        log.info("GAIADataCache started — membrane has live nutrient threads")

    from runtime.nyx_metabolism_boot import start_metabolic_daemon

    daemon = start_metabolic_daemon(root, cache=cache, background=False)
    if daemon is None:
        log.error("MetabolicDaemon failed to start — check Nyx install and logs above")
        return 1

    log.info(
        "Nyx metabolism running in foreground (Ctrl+C to stop). "
        "Liminal store: %s",
        root / "runs" / "nyx_liminal",
    )
    try:
        daemon.run_forever()
    except KeyboardInterrupt:
        log.info("Stopping metabolic daemon")
        daemon.stop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
