#!/usr/bin/env python3
"""
Fetch upper-air soundings for all GAIA stations and report.

Usage:
  python scripts/fetch_soundings.py               # latest available (00Z or 12Z)
  python scripts/fetch_soundings.py 2011-04-27T12  # historical
  python scripts/fetch_soundings.py --cron         # silent unless risk >= MODERATE

Output written to runs/live_soundings.json for dashboard consumption.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from datetime import datetime, timezone
from runtime.data.sounding_client import fetch_all_soundings, format_table


def main():
    cron_mode = "--cron" in sys.argv
    dt = None
    for arg in sys.argv[1:]:
        if arg.startswith("--"):
            continue
        dt = datetime.fromisoformat(arg).replace(tzinfo=timezone.utc)

    data = fetch_all_soundings(dt)

    if cron_mode:
        risk = data.get("sounding_risk", "LOW")
        if risk in ("MODERATE", "SIGNIFICANT", "EXTREME"):
            print(format_table(data))
            print(f"\n*** SOUNDING RISK: {risk} ***")
        return

    print(format_table(data))
    print(f"\nCached to: runs/live_soundings.json")


if __name__ == "__main__":
    main()
