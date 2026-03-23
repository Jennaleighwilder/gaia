#!/usr/bin/env python3
"""
Full 3,667 event backtest.
Uses east_tn_full_events.json + observation fixtures + synthetic radar.
Reports detection rate by event type.
"""

from __future__ import annotations

import os

os.environ["GAIA_OFFLINE"] = "1"
os.environ["GAIA_NO_EVIDENCE"] = "1"

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def load_events() -> list[dict]:
    path = ROOT / "tests/fixtures/east_tn_full_events.json"
    if not path.exists():
        return []
    return json.loads(path.read_text())


def load_event_observations(event_id: str) -> dict | None:
    path = ROOT / f"tests/fixtures/historical_observations/event_{event_id}.json"
    if not path.exists():
        return None
    return json.loads(path.read_text())


def main():
    import sys
    sys.path.insert(0, str(ROOT))
    from scripts.run_backtest import execute_backtest

    events = load_events()
    have_obs = []
    for e in events:
        if load_event_observations(e["event_id"]):
            have_obs.append(e)
    print(f"Full backtest: {len(have_obs)} events with observations (of {len(events)} total)")
    if not have_obs:
        print("Run fetch_asos_full_backtest.py first to build observation fixtures.")
        return 1

    celestial_path = ROOT / "tests/fixtures/historical_kp.json"
    out = execute_backtest(
        events=have_obs,
        quiet_files=[],
        include_upper_air=False,
        celestial_fixture_path=celestial_path,
    )
    print(f"\nOverall: {out['detected']}/{out['events_tested']} ({out['detection_rate']}%)")
    if out.get("lead_times_minutes"):
        print(f"Avg lead time (valid <12hr): {sum(out['lead_times_minutes'])/len(out['lead_times_minutes']):.0f} min")
    if out.get("lead_times_all_minutes"):
        print(f"Avg lead time (all): {sum(out['lead_times_all_minutes'])/len(out['lead_times_all_minutes']):.0f} min")
    if out.get("lead_time_suspect_count"):
        print(f"SUSPECT lead times excluded: {out['lead_time_suspect_count']} (fired >12hr before event)")

    from collections import defaultdict
    by_type = defaultdict(lambda: {"count": 0, "detected": 0, "leads": [], "leads_all": []})
    for r in out.get("severe_results", []):
        ev = r["event"]
        t = ev.get("event_type", "unknown")
        by_type[t]["count"] += 1
        if r["max_decision"] in ("WARNING", "EMERGENCY"):
            by_type[t]["detected"] += 1
        lt = r.get("lead_time_minutes")
        if lt is not None:
            by_type[t]["leads"].append(lt)
            by_type[t]["leads_all"].append(lt)
        elif r.get("lead_time_raw_minutes") is not None:
            by_type[t]["leads_all"].append(r["lead_time_raw_minutes"])

    print("\nEvent Type       | Count | Detected | Rate   | Avg Lead")
    print("-" * 60)
    for t in sorted(by_type.keys(), key=lambda x: -by_type[x]["count"]):
        d = by_type[t]
        rate = (d["detected"] / d["count"] * 100) if d["count"] else 0
        avg_lead = sum(d["leads"]) / len(d["leads"]) if d["leads"] else None
        lead_s = f"{avg_lead:.0f} min" if avg_lead is not None else "-"
        print(f"{t:16s} | {d['count']:5d} | {d['detected']:8d} | {rate:5.1f}% | {lead_s}")
    return 0


if __name__ == "__main__":
    exit(main())
