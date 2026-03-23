#!/usr/bin/env python3
"""Quick thunderstorm_wind backtest only."""

from __future__ import annotations

import os

os.environ["GAIA_OFFLINE"] = "1"
os.environ["GAIA_NO_EVIDENCE"] = "1"

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def _dt(ts: str):
    from datetime import datetime, timezone
    return datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone(timezone.utc)


def _wind_kt(event: dict, dataset: dict) -> float:
    mag = str(event.get("magnitude", "") or "")
    wkt = 0.0
    for part in mag.replace(" mph", "").replace(" kt", "").split():
        try:
            v = float(part)
            wkt = v / 1.15078 if "mph" in mag.lower() else v
            break
        except ValueError:
            pass
    if wkt == 0 and dataset.get("observations"):
        event_utc = event.get("event_datetime_utc", "")
        obs_at_event = None
        for o in dataset["observations"]:
            if o.get("timestamp", "")[:16] >= event_utc[:16]:
                obs_at_event = o
                break
        if obs_at_event is None:
            obs_at_event = dataset["observations"][-1]
        ws = obs_at_event.get("wind_speed_mph")
        if ws is not None:
            wkt = ws / 1.15078
    return round(wkt, 1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0, help="Limit events (0=all)")
    ap.add_argument("--show-misses", action="store_true", help="Show detailed diagnosis for missed events")
    args = ap.parse_args()
    from scripts.run_backtest import execute_backtest, load_event_observations
    events = json.loads((ROOT / "tests/fixtures/east_tn_full_events.json").read_text())
    tw = [e for e in events if e.get("event_type") == "thunderstorm_wind" and load_event_observations(e["event_id"])]
    if args.limit:
        tw = tw[: args.limit]
    print(f"Thunderstorm wind backtest: {len(tw)} events")
    out = execute_backtest(tw, [], False, ROOT / "tests/fixtures/historical_kp.json")
    det = out["detected"]
    tot = out["events_tested"]
    rate = 100 * det / tot if tot else 0
    print(f"Detection: {det}/{tot} ({rate:.1f}%)")
    leads = out.get("lead_times_minutes", [])
    if leads:
        print(f"Avg lead time (valid): {sum(leads)/len(leads):.0f} min")

    if args.show_misses and out.get("misses"):
        misses = [r for r in out.get("severe_results", []) if r["max_decision"] not in ("WARNING", "EMERGENCY")]
        print(f"\n=== MISS DIAGNOSIS ({len(misses)} events) ===\n")
        for i, item in enumerate(misses, 1):
            ev, ds = item["event"], item["dataset"]
            event_utc = ev.get("event_datetime_utc", "")
            dt = _dt(event_utc) if event_utc else None
            local_hr = (dt.hour - 5) % 24 if dt else 12
            time_of_day = "night" if (0 <= local_hr < 6 or local_hr >= 22) else "day"
            wind_kt = _wind_kt(ev, ds)
            timeline = item.get("timeline", [])
            peak = max(timeline, key=lambda t: {"CLEAR": 0, "WATCH": 1, "WARNING": 2, "EMERGENCY": 3}.get(t["decision"], 0)) if timeline else {}
            eng = peak.get("engine_scores", {})
            details = peak.get("engine_details", {})
            conv = peak.get("convergence_count", 0)
            shear = float(eng.get("shear") or 0)
            engines_above_04 = [k for k, v in eng.items() if isinstance(v, (int, float)) and v >= 0.4]
            pressure_detail = details.get("pressure", {})
            drop = float(pressure_detail.get("pressure_drop_rate_mbph") or 0)
            fast_mover = drop >= 0.8 and conv >= 2
            shear_detail = details.get("shear", {}) or {}
            llj = float(shear_detail.get("channels", {}).get("low_level_jet", 0) or 0)
            llj_fired = llj >= 0.5
            print(f"--- MISS {i}: {ev.get('date')} {ev.get('county')} ---")
            print(f"  Wind speed: {wind_kt} kt")
            print(f"  Peak decision: {item['max_decision']}")
            print(f"  convergence_count at peak: {conv}")
            print(f"  Engines >= 0.4: {', '.join(engines_above_04) or 'none'}")
            print(f"  Shear score: {shear:.2f} (>=0.6: {shear >= 0.6})")
            print(f"  Fast-mover (drop>=0.8): {fast_mover} (drop={drop:.2f} mb/hr)")
            print(f"  LLJ fired: {llj_fired} (llj={llj:.2f})")
            print(f"  Time of day: {time_of_day} (local hr {local_hr:02d})")
            print()
    return 0


if __name__ == "__main__":
    exit(main())
