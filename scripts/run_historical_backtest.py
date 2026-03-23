#!/usr/bin/env python3
"""
Historical backtest across event corpus.
--event-type tornado|flash_flood|thunderstorm_wind|all
--start-year, --end-year, --county
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TORNADO_EVENTS = ROOT / "tests" / "fixtures" / "east_tn_tornado_events.json"


def load_tornado_events() -> list[dict]:
    if not TORNADO_EVENTS.exists():
        return []
    return json.loads(TORNADO_EVENTS.read_text())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--event-type", default="tornado", choices=["tornado", "all"])
    ap.add_argument("--start-year", type=int, default=1996)
    ap.add_argument("--end-year", type=int, default=2025)
    ap.add_argument("--county", default=None)
    args = ap.parse_args()

    import sys
    sys.path.insert(0, str(ROOT))
    from scripts.run_backtest import (
        execute_backtest,
        load_event_observations,
    )

    events = load_tornado_events()
    if args.start_year or args.end_year:
        events = [e for e in events if args.start_year <= int(e["date"][:4]) <= args.end_year]
    if args.county:
        events = [e for e in events if e.get("county") == args.county.lower()]

    # Filter to events that have observation fixtures
    have_obs = []
    for e in events:
        if load_event_observations(e["event_id"]):
            have_obs.append(e)
    print(f"Tornado backtest: {len(have_obs)} events (of {len(events)} total)")

    out = execute_backtest(
        events=have_obs,
        quiet_files=[],
        include_upper_air=False,
        celestial_fixture_path=ROOT / "tests/fixtures/historical_kp.json",
    )
    print(f"\nDetection rate: {out['detected']}/{out['events_tested']} ({out['detection_rate']}%)")
    if out.get("lead_times_minutes"):
        print(f"Avg lead time: {sum(out['lead_times_minutes'])/len(out['lead_times_minutes']):.0f} min")
    for r in out.get("severe_results", []):
        ev = r["event"]
        status = "HIT" if r["max_decision"] in ("WARNING", "EMERGENCY") else "MISS"
        lead = f" ({r['lead_time_minutes']} min)" if r.get("lead_time_minutes") is not None else ""
        print(f"  [{status}] {ev['date']} {ev['county']} {ev.get('magnitude','')} -> {r['max_decision']}{lead}")
    return out


if __name__ == "__main__":
    main()
