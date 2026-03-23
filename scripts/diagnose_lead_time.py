#!/usr/bin/env python3
"""
Diagnose thunderstorm_wind events with suspect lead time (>500 min).
Prints: event date, begin_time, first WARNING timestamp, engines fired, ASOS at that time.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def _dt(ts: str):
    from datetime import datetime, timezone
    return datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone(timezone.utc)


def main():
    from scripts.run_backtest import run_single_event, load_event_observations
    from scripts.run_full_backtest import load_events, load_event_observations as load_obs

    events = load_events()
    tw = [e for e in events if e.get("event_type") == "thunderstorm_wind"]
    have_obs = [e for e in tw if load_obs(e["event_id"])]

    suspect = []
    for ev in have_obs:
        dataset = load_event_observations(ev["event_id"])
        if not dataset or not dataset.get("observations"):
            continue
        result = run_single_event(
            dataset, ev,
            include_upper_air=False,
            celestial_fixture_path=ROOT / "tests/fixtures/historical_kp.json",
        )
        lt = result.get("lead_time_minutes") or result.get("lead_time_raw_minutes")
        if lt is not None and lt > 500:
            suspect.append((ev, result, dataset))

    suspect.sort(key=lambda x: -(x[1].get("lead_time_minutes") or x[1].get("lead_time_raw_minutes") or 0))
    top10 = suspect[:10]

    print(f"Thunderstorm wind events with lead time > 500 min: {len(suspect)}")
    print("=" * 80)
    for ev, result, dataset in top10:
        lt = result.get("lead_time_minutes") or result.get("lead_time_raw_minutes") or 0
        fw = result.get("first_warning_time") or result.get("first_warning_time_raw")
        event_dt = ev.get("event_datetime_utc", "")
        obs = dataset.get("observations", [])
        first_warn_obs = None
        if fw and obs:
            for o in obs:
                if o.get("timestamp") == fw:
                    first_warn_obs = o
                    break
        snap = result.get("alarm_snapshot", {})
        engines = snap.get("engines_fired", [])
        timeline = result.get("timeline", [])
        warn_idx = None
        for i, t in enumerate(timeline):
            if t.get("decision") in ("WARNING", "EMERGENCY"):
                warn_idx = i
                break
        warn_engines = timeline[warn_idx]["engine_scores"] if warn_idx is not None else {}

        print(f"\nEvent: {ev['date']} {ev['county']} id={ev['event_id']}")
        print(f"  event_datetime_utc: {event_dt}")
        print(f"  first WARNING timestamp: {fw}")
        print(f"  lead_time_minutes: {lt} ({lt/60:.1f} hours)")
        print(f"  observation window: {obs[0]['timestamp'] if obs else '?'} to {obs[-1]['timestamp'] if obs else '?'}")
        print(f"  engines fired at first WARNING: {engines}")
        print(f"  engine scores at first WARNING: {[(k,v) for k,v in (warn_engines or {}).items() if isinstance(v,(int,float)) and v>=0.3]}")
        if first_warn_obs:
            print(f"  ASOS at first WARNING: temp={first_warn_obs.get('temperature_f')} dew={first_warn_obs.get('dewpoint_f')} "
                  f"wind={first_warn_obs.get('wind_speed_mph')} kt sky={first_warn_obs.get('sky_condition')}")
    return 0


if __name__ == "__main__":
    exit(main())
