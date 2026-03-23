#!/usr/bin/env python3
"""
Diagnose 28 missed hail events:
- Hail size missed
- Engine scores at event time
- VIL score
- Radar reflectivity
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def main():
    from scripts.run_backtest import run_single_event, load_event_observations
    from scripts.run_full_backtest import load_events, load_event_observations as load_obs

    events = load_events()
    hail = [e for e in events if e.get("event_type") == "hail"]
    have_obs = [e for e in hail if load_obs(e["event_id"])]

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

    # Hail size distribution: magnitude in inches (NWS: penny 0.75, quarter 1.0, golf 1.75, baseball 2.75)
    penny, golf_ball, baseball, other = [], [], [], []
    for ev, _, _ in misses:
        mag = str(ev.get("magnitude", "") or "").strip()
        inch = 0.0
        for part in mag.replace(" mph", "").split():
            try:
                inch = float(part)
                break
            except ValueError:
                pass
        if inch >= 2.5:
            baseball.append(ev)
        elif inch >= 1.5:
            golf_ball.append(ev)
        elif inch >= 0.75:
            penny.append(ev)
        else:
            other.append(ev)
    print(f"Missed hail events: {len(misses)}")
    print("Hail size distribution of misses:")
    print(f"  Baseball (>=2.5\"): {len(baseball)}")
    print(f"  Golf ball (1.5-2.5\"): {len(golf_ball)}")
    print(f"  Penny (0.75-1.5\"): {len(penny)}")
    print(f"  Other/small: {len(other)}")
    print("=" * 80)
    for ev, result, dataset in misses[:28]:
        mag = ev.get("magnitude", "")
        timeline = result.get("timeline", [])
        last = timeline[-1] if timeline else {}
        eng = last.get("engine_scores", {})
        details = last.get("engine_details", {})
        radar = details.get("radar") or dataset.get("radar_fixture") or {}
        vil = radar.get("vil") or radar.get("VIL") or 0
        echo_top = radar.get("echo_top_km") or 0
        comp = eng.get("composite") or eng.get("radar") or 0
        inst = eng.get("instability") or 0
        print(f"\n{ev['date']} {ev['county']} id={ev['event_id']} mag={mag}")
        print(f"  VIL: {vil} echo_top_km: {echo_top}")
        print(f"  radar: {eng.get('radar')} composite: {comp} instability: {inst}")
        print(f"  max_decision: {result['max_decision']}")
    return 0


if __name__ == "__main__":
    exit(main())
