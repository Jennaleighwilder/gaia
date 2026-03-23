#!/usr/bin/env python3
"""
Flash flood backtest only.
Reports detection rate and diagnoses misses.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def main():
    from scripts.run_backtest import execute_backtest, load_event_observations
    events_all = json.loads((ROOT / "tests/fixtures/east_tn_full_events.json").read_text())
    ff_events = [e for e in events_all if e["event_type"] == "flash_flood" and load_event_observations(e["event_id"])]
    if not ff_events:
        print("No flash flood events with observation fixtures.")
        return 1
    print(f"Flash flood backtest: {len(ff_events)} events")
    out = execute_backtest(
        events=ff_events,
        quiet_files=[],
        include_upper_air=False,
        celestial_fixture_path=ROOT / "tests/fixtures/historical_kp.json",
    )
    detected = out["detected"]
    total = out["events_tested"]
    rate = (detected / total * 100) if total else 0
    print(f"\nDetection: {detected}/{total} ({rate:.1f}%)")
    for r in out.get("severe_results", []):
        ev = r["event"]
        hit = r["max_decision"] in ("WARNING", "EMERGENCY")
        status = "HIT" if hit else "MISS"
        tl = r.get("timeline", [])
        last = tl[-1] if tl else {}
        eng = last.get("engine_scores", {})
        hydro = last.get("engine_details", {}).get("hydrological", {})
        soil = eng.get("soil", 0)
        terrain = eng.get("terrain", 0)
        print(f"  [{status}] {ev['date']} {ev['county']} (id={ev['event_id']}) -> {r['max_decision']}")
        if not hit:
            print(f"       engine scores: hydro={eng.get('hydrological')}, soil={soil}, terrain={terrain}, moisture={eng.get('moisture')}")
    return 0


if __name__ == "__main__":
    exit(main())
