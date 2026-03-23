#!/usr/bin/env python3
"""
Diagnose thunderstorm_wind misses.
Shows: wind speed, time of day, season, engine scores, shear>0.4, instability>0.4.
"""

from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def _dt(ts: str):
    from datetime import datetime, timezone
    return datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone(timezone.utc)


def mph_to_kt(mph: float) -> float:
    return mph / 1.15078 if mph else 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--event-type", default="thunderstorm_wind")
    ap.add_argument("--missed-only", action="store_true", help="Only missed events (default: True)")
    ap.add_argument("--limit", type=int, default=0, help="Limit events to diagnose (0=all)")
    args = ap.parse_args()

    from scripts.run_backtest import run_single_event, load_event_observations
    from scripts.run_full_backtest import load_events, load_event_observations as load_obs

    events = load_events()
    target = [e for e in events if e.get("event_type") == args.event_type]
    have_obs = [e for e in target if load_obs(e["event_id"])]

    misses = []
    for ev in have_obs:
        dataset = load_event_observations(ev["event_id"])
        if not dataset or not dataset.get("observations"):
            continue
        result = run_single_event(
            dataset, ev,
            include_upper_air=False,
            celestial_fixture_path=ROOT / "tests/fixtures/historical_kp.json",
        )
        if result["max_decision"] not in ("WARNING", "EMERGENCY"):
            misses.append((ev, result, dataset))
        if args.limit and len(misses) >= args.limit:
            break

    print(f"Thunderstorm wind misses: {len(misses)} (of {len(have_obs)} with fixtures)")
    if not misses:
        return 0

    # Wind speed from magnitude (e.g. "50 kt", "75 mph") or obs at event time
    wind_kts = []
    day_count, night_count = 0, 0
    months = defaultdict(int)
    shear_above_04 = 0
    inst_above_04 = 0
    weak_events = []  # wind 50-55 kt
    night_events = []
    fast_mover_candidates = []

    for ev, result, dataset in misses:
        event_utc = ev.get("event_datetime_utc", "")
        dt = _dt(event_utc) if event_utc else None
        local_hour = (dt.hour - 5) % 24 if dt else 12
        if 0 <= local_hour < 6 or 22 <= local_hour:
            night_count += 1
            night_events.append(ev)
        else:
            day_count += 1

        month = event_utc[5:7] if event_utc else ""
        months[month] += 1

        mag = str(ev.get("magnitude", "") or "")
        wkt = 0.0
        for part in mag.replace(" mph", "").replace(" kt", "").split():
            try:
                v = float(part)
                if "mph" in mag.lower():
                    wkt = v / 1.15078
                else:
                    wkt = v
                break
            except ValueError:
                pass
        if wkt == 0 and dataset.get("observations"):
            obs_at_event = None
            event_utc = ev.get("event_datetime_utc", "")
            for o in dataset["observations"]:
                if o.get("timestamp", "")[:16] >= event_utc[:16]:
                    obs_at_event = o
                    break
            if obs_at_event is None:
                obs_at_event = dataset["observations"][-1]
            ws = obs_at_event.get("wind_speed_mph")
            if ws is not None:
                wkt = ws / 1.15078
        wind_kts.append(wkt)
        if 50 <= wkt <= 55:
            weak_events.append((ev, wkt))

        timeline = result.get("timeline", [])
        event_obs_idx = None
        for i, obs in enumerate(dataset.get("observations", [])):
            if obs.get("timestamp", "").replace("Z", "+00:00")[:16] >= event_utc[:16]:
                event_obs_idx = i
                break
        if event_obs_idx is None and timeline:
            event_obs_idx = len(timeline) - 1

        if event_obs_idx is not None and event_obs_idx < len(timeline):
            t = timeline[event_obs_idx]
            eng = t.get("engine_scores", {})
            shear = float(eng.get("shear") or 0)
            inst = float(eng.get("instability") or 0)
            if shear >= 0.4:
                shear_above_04 += 1
            if inst >= 0.4:
                inst_above_04 += 1
            pressure_detail = t.get("engine_details", {}).get("pressure", {})
            drop = pressure_detail.get("pressure_drop_rate_mbph") or 0
            if drop and abs(float(drop)) > 0.8:
                fast_mover_candidates.append((ev, drop))

    print("\n=== MISS PATTERN TABLE ===")
    print(f"\nWind speed (kt): n={len(wind_kts)}, avg={sum(wind_kts)/len(wind_kts):.1f}" if wind_kts else "")
    if wind_kts:
        print(f"  range: {min(wind_kts):.0f}-{max(wind_kts):.0f} kt")
        weak = sum(1 for w in wind_kts if 50 <= w <= 55)
        marginal = sum(1 for w in wind_kts if 55 < w <= 60)
        print(f"  weak (50-55 kt): {weak}")
        print(f"  marginal (55-60 kt): {marginal}")

    print(f"\nTime of day: day={day_count} night={night_count}")
    print(f"  Night events (0000-0600 or 2200-2400 local): {night_count}")

    print("\nSeason (month):")
    for m in sorted(months.keys()):
        print(f"  {m}: {months[m]}")

    print(f"\nEngine scores at event time:")
    print(f"  Shear >= 0.4: {shear_above_04}/{len(misses)}")
    print(f"  Instability >= 0.4: {inst_above_04}/{len(misses)}")

    print(f"\nFast mover candidates (pressure drop > 0.8 hPa/hr): {len(fast_mover_candidates)}")

    print("\n=== SAMPLE MISSES (first 15) ===")
    for ev, result, dataset in misses[:15]:
        mag = ev.get("magnitude", "?")
        event_utc = ev.get("event_datetime_utc", "")
        dt = _dt(event_utc) if event_utc else None
        local_hr = (dt.hour - 5) % 24 if dt else 0
        timeline = result.get("timeline", [])
        last = timeline[-1] if timeline else {}
        eng = last.get("engine_scores", {})
        shear = eng.get("shear", 0)
        inst = eng.get("instability", 0)
        radar = eng.get("radar", 0)
        print(f"  {ev['date']} {ev['county']} mag={mag} local_hr={local_hr:02d} shear={shear} inst={inst} radar={radar}")

    return 0


if __name__ == "__main__":
    exit(main())
