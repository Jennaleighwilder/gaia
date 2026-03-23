#!/usr/bin/env python3
"""
Diagnose the 23 missed tornadoes: peak_decision, convergence_count, chorus_fired, top_engine_scores.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main():
    import sys
    sys.path.insert(0, str(ROOT))

    tornado_events = json.loads((ROOT / "tests/fixtures/east_tn_tornado_events.json").read_text())
    from scripts.run_backtest import execute_backtest, load_event_observations

    have_obs = [e for e in tornado_events if load_event_observations(e["event_id"])]
    out = execute_backtest(
        events=have_obs,
        quiet_files=[],
        include_upper_air=False,
        celestial_fixture_path=ROOT / "tests/fixtures/historical_kp.json",
    )

    misses = [r for r in out["severe_results"] if r["max_decision"] not in ("WARNING", "EMERGENCY")]
    print(f"=== TORNADO MISS DIAGNOSIS ({len(misses)} misses) ===\n")
    print(f"Detection: {out['detected']}/{out['events_tested']} ({out['detection_rate']}%)\n")

    rows = []
    for r in misses:
        ev = r["event"]
        timeline = r.get("timeline", [])
        max_cc = 0
        peak_engines = {}
        chorus_fired = r.get("chorus_veto_caught", False)
        max_decision_before = r.get("max_decision_before_veto", r["max_decision"])

        for t in timeline:
            cc = t.get("convergence_count", 0)
            if cc > max_cc:
                max_cc = cc
            eng = t.get("engine_scores") or {}
            for k, v in eng.items():
                if isinstance(v, (int, float)) and v and v >= 0.4:
                    peak_engines[k] = max(peak_engines.get(k, 0), v)

        top_scores = ", ".join(f"{k}={v:.2f}" for k, v in sorted(peak_engines.items(), key=lambda x: -x[1])[:6])
        rows.append({
            "date": ev["date"],
            "county": ev["county"],
            "ef": ev.get("magnitude", ""),
            "peak": r["max_decision"],
            "cc": max_cc,
            "chorus": "YES" if chorus_fired else "no",
            "before_veto": max_decision_before,
            "top_engines": top_scores,
        })

    # Table
    print(f"{'date':<12} {'county':<10} {'EF':<6} {'peak':<8} {'cc':<4} {'chorus':<6} {'before_veto':<10} {'top_engine_scores'}")
    print("-" * 120)
    for row in rows:
        print(f"{row['date']:<12} {row['county']:<10} {row['ef']:<6} {row['peak']:<8} {row['cc']:<4} {row['chorus']:<6} {row['before_veto']:<10} {row['top_engines'][:60]}")

    # EF2+ check
    ef2_plus = [r for r in misses if any(x in str(r["event"].get("magnitude", "")).upper() for x in ("EF2", "EF3", "EF4", "EF5", "F2", "F3", "F4", "F5"))]
    print(f"\n=== EF2+ MISSED ({len(ef2_plus)}) ===")
    for r in ef2_plus:
        ev = r["event"]
        print(f"  {ev['date']} {ev['county']} {ev.get('magnitude')} -> {r['max_decision']} (chorus={r.get('chorus_veto_caught')})")

    return rows


if __name__ == "__main__":
    main()
