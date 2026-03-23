#!/usr/bin/env python3
"""
FALSE ALARM AUTOPSY — Full fingerprint for every quiet day that reaches WARNING/EMERGENCY.

For each surviving false alarm, prints every channel, every score, every veto status.
The pattern is in the numbers.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts.run_backtest import (
    load_json,
    run_single_event,
)

CELESTIAL_FIXTURE = ROOT / "tests/fixtures/historical_kp.json"


def _get_gps_pw_mm(date_str: str) -> float | None:
    """Look up raw GPS-PW mm from fixture for autopsy display."""
    try:
        fix = json.loads((ROOT / "tests/fixtures/gps_pw.json").read_text())
    except Exception:
        return None
    day = fix.get(str(date_str)[:10])
    if not day:
        return None
    vals = [v for v in day.values() if isinstance(v, (int, float))]
    return round(float(vals[0]), 2) if vals else None


def _first_alarm_entry(timeline: list[dict]) -> dict | None:
    """First timeline entry where decision is WARNING or EMERGENCY."""
    for r in timeline:
        if r.get("decision") in ("WARNING", "EMERGENCY"):
            return r
    return None


def run_autopsy() -> None:
    quiet_files = sorted((ROOT / "tests/fixtures/historical_observations").glob("quiet_*.json"))
    celestial = CELESTIAL_FIXTURE if CELESTIAL_FIXTURE.exists() else None

    false_alarms = []
    for qf in quiet_files:
        dataset = load_json(qf)
        obs_list = dataset.get("observations", [])
        if not obs_list:
            continue
        result = run_single_event(dataset, include_upper_air=True, celestial_fixture_path=celestial)
        if result["max_decision"] not in ("WARNING", "EMERGENCY"):
            continue

        entry = _first_alarm_entry(result["timeline"])
        if not entry:
            continue

        # Enriched obs at first alarm (includes channel_context, sensor vals)
        alarm_snap = result.get("alarm_snapshot") or {}
        obs = alarm_snap.get("alarm_observation") or {}
        date_str = obs.get("timestamp", "")[:10]
        station_id = obs.get("station_id", "?")

        # Channel context from engine_details
        ed = entry.get("engine_details") or {}
        mc = ed.get("moisture", {}).get("channels", {})
        tc = ed.get("thermal", {}).get("channels", {})
        ic = ed.get("instability", {}).get("channels", {})
        ec = ed.get("environmental", {}).get("channels", {})

        gps_pw_score = mc.get("gps_pw")
        gps_pw_mm = _get_gps_pw_mm(date_str)

        # Wind for chorus analysis
        wind_mph = obs.get("wind_speed_mph")
        if wind_mph is None and obs.get("wind_speed_kt") is not None:
            try:
                wind_mph = float(obs["wind_speed_kt"]) * 1.15078
            except (TypeError, ValueError):
                pass

        false_alarms.append({
            "quiet_id": qf.stem,
            "date": date_str,
            "station": station_id,
            "decision": entry.get("decision"),
            "decision_before_veto": entry.get("decision_before_veto"),
            "vetoes": {
                "inst_quality_applied": entry.get("inst_quality_applied", False),
                "chorus_veto_applied": entry.get("chorus_veto_applied", False),
                "siren_decision": entry.get("siren_decision", "CLEAR"),
                "column_dry_count": entry.get("column_dry_count", 0),
                "stillness_count": entry.get("stillness_count", 0),
                "weak_forcing_count": entry.get("weak_forcing_count", 0),
            },
            "engine_scores": entry.get("engine_scores") or {},
            "channels": {
                "gps_pw_score": gps_pw_score,
                "gps_pw_mm": gps_pw_mm,
                "overnight_cooling_rate": tc.get("overnight_cooling_rate"),
                "t_td_convergence": mc.get("t_td_convergence"),
                "daytime_heating_rate": ic.get("daytime_heating_rate"),
                "surface_ozone": ec.get("surface_ozone"),
                "harmonic": entry.get("engine_scores", {}).get("harmonic"),
            },
            "channels_full": {
                "moisture": dict(mc) if mc else {},
                "thermal": dict(tc) if tc else {},
                "instability": dict(ic) if ic else {},
                "environmental": dict(ec) if ec else {},
            },
            "wind_mph": wind_mph,
            "surface_obs": {
                "temp_f": obs.get("temperature_f"),
                "dewpoint_f": obs.get("dewpoint_f"),
                "wind_speed_mph": obs.get("wind_speed_mph"),
                "wind_direction_deg": obs.get("wind_direction_deg"),
                "pressure_mb": obs.get("pressure_mb"),
                "visibility_mi": obs.get("visibility_mi"),
                "sky_condition": obs.get("sky_condition"),
            },
            "convergence_engines": entry.get("convergence_engines", []),
            "convergence_count": entry.get("convergence_count", 0),
        })

    return false_alarms


def _fmt(v, prec=4):
    if v is None:
        return "—"
    if isinstance(v, float):
        return f"{v:.{prec}f}"
    return str(v)


def _why_chorus_didnt_fire(fa: dict) -> str:
    """Explain why chorus didn't fire (or why veto didn't apply)."""
    v = fa.get("vetoes") or {}
    dry = v.get("column_dry_count", 0)
    still = v.get("stillness_count", 0)
    weak = v.get("weak_forcing_count", 0)
    siren = v.get("siren_decision", "CLEAR")
    chorus_applied = v.get("chorus_veto_applied", False)
    wind = fa.get("wind_mph")

    dims_with_2plus = sum([dry >= 2, still >= 2, weak >= 2])
    max_single = max(dry, still, weak)
    fire_threshold = max_single >= 3 or dims_with_2plus >= 2

    lines = []
    if chorus_applied:
        return "Chorus DID fire and downgraded (this is pre-veto snapshot at first alarm)"
    if siren == "FIRE" and not chorus_applied:
        if wind is not None and wind >= 10.0:
            lines.append(f"FIRE threshold MET (dry={dry} still={still} weak={weak}) BUT wind={_fmt(wind, 1)} mph >= 10 blocked veto")
        else:
            lines.append(f"FIRE threshold MET — unexpected: dry={dry} still={still} weak={weak}")
    else:
        lines.append(f"FIRE threshold NOT MET: max_single={max_single} (need 3), dims_with_2+={dims_with_2plus} (need 2)")
        if max_single == 2 and dims_with_2plus == 1:
            need_3 = "dry" if dry == 2 else "still" if still == 2 else "weak"
            lines.append(f"  → One dimension at 2 ({need_3}). Need +1 channel there for max=3, OR +1 on another dim for dims=2")
        elif max_single == 2 and dims_with_2plus == 0:
            lines.append(f"  → Two dimensions at 1 each. Need +1 on each to reach dims=2")
        elif max_single == 1:
            lines.append(f"  → All dims at 0–1. Need +2 on one dim for max=3, OR +1 on two dims for dims=2")
    if wind is not None:
        lines.append(f"  Wind: {_fmt(wind, 1)} mph")
    return " | ".join(lines)


def print_autopsy(fas: list[dict]) -> None:
    print("=" * 100)
    print("FALSE ALARM AUTOPSY — Surviving False Alarms (WARNING/EMERGENCY after all vetoes)")
    print("=" * 100)
    print(f"Total: {len(fas)} false alarms\n")

    for i, fa in enumerate(fas, 1):
        print("-" * 100)
        print(f"## FALSE ALARM {i}: {fa['quiet_id']}")
        print("-" * 100)
        print(f"  Date:              {fa['date']}")
        print(f"  Station:           {fa['station']}")
        print(f"  Final decision:    {fa['decision']} (before vetoes: {fa.get('decision_before_veto', '?')})")
        print()
        print("  SIREN CHORUS (dimension scores):")
        v = fa["vetoes"]
        print(f"    dry={v['column_dry_count']}  still={v['stillness_count']}  weak={v['weak_forcing_count']}  |  siren_decision: {v['siren_decision']}")
        print(f"    chorus_veto_applied: {v['chorus_veto_applied']}  |  wind: {_fmt(fa.get('wind_mph'), 1)} mph")
        print()
        print("  WHY CHORUS DIDN'T FIRE:")
        print(f"    {_why_chorus_didnt_fire(fa)}")
        print()
        print("  ENGINE SCORES (at first alarm):")
        for k, val in sorted((fa["engine_scores"] or {}).items()):
            if val is not None:
                print(f"    {k:<22} {_fmt(val)}")
        print()
        print("  CHANNEL CONTEXT (all values):")
        cf = fa.get("channels_full") or {}
        for engine_name, chans in cf.items():
            if chans:
                print(f"    [{engine_name}]")
                for k, val in sorted(chans.items()):
                    print(f"      {k}: {_fmt(val)}")
        c = fa["channels"]
        print(f"    [chorus-relevant] gps_pw={_fmt(c['gps_pw_score'])} mm={_fmt(c['gps_pw_mm'], 2)} | overnight_cool={_fmt(c['overnight_cooling_rate'])} | t_td_conv={_fmt(c['t_td_convergence'])} | day_heat={_fmt(c['daytime_heating_rate'])} | ozone={_fmt(c['surface_ozone'])} | harmonic={_fmt(c['harmonic'])}")
        print()
        print("  SURFACE OBS:")
        s = fa["surface_obs"]
        print(f"    temp_F: {_fmt(s['temp_f'], 1)}  dewpoint_F: {_fmt(s['dewpoint_f'], 1)}  dd: {_fmt(s['temp_f'] - s['dewpoint_f'] if s.get('temp_f') is not None and s.get('dewpoint_f') is not None else None, 1)}")
        print(f"    wind: {_fmt(s['wind_speed_mph'], 1)} mph @ {_fmt(s['wind_direction_deg'], 0)}°")
        print(f"    pressure_mb: {_fmt(s['pressure_mb'])}  vis_mi: {_fmt(s['visibility_mi'])}  sky: {s.get('sky_condition') or '—'}")
        print()
        print(f"  CONVERGENCE: {fa['convergence_count']} engines  |  Voted: {fa['convergence_engines']}")
        print()

    # Summary table
    print("=" * 100)
    print("SUMMARY TABLE (paste-friendly)")
    print("=" * 100)
    headers = ["quiet_id", "date", "station", "decision", "cc", "gps_pw", "gps_mm", "overnight", "t_td", "day_heat", "ozone", "temp", "dd", "wind", "engines"]
    print("|".join(f"{h:^12}" for h in headers))
    print("-" * (14 * len(headers)))
    for fa in fas:
        c = fa["channels"]
        s = fa["surface_obs"]
        dd = (s.get("temp_f") or 0) - (s.get("dewpoint_f") or 0) if s.get("temp_f") is not None and s.get("dewpoint_f") is not None else None
        row = [
            fa["quiet_id"][:12],
            fa["date"],
            fa["station"][:12],
            fa["decision"][:12],
            str(fa["convergence_count"]),
            _fmt(c["gps_pw_score"], 2),
            _fmt(c["gps_pw_mm"], 2),
            _fmt(c["overnight_cooling_rate"], 2),
            _fmt(c["t_td_convergence"], 2),
            _fmt(c["daytime_heating_rate"], 2),
            _fmt(c["surface_ozone"], 2),
            _fmt(s.get("temp_f"), 1),
            _fmt(dd, 1),
            f"{_fmt(s.get('wind_speed_mph'), 1)}@{_fmt(s.get('wind_direction_deg'), 0)}",
            ",".join(fa["convergence_engines"][:3])[:20],
        ]
        print("|".join(f"{str(x):^12}"[:12] for x in row))

    # Closest to FIRE analysis
    print("=" * 100)
    print("CHORUS GAP ANALYSIS — How close each survivor is to FIRE")
    print("=" * 100)
    print("FIRE needs: max(dry,still,weak)>=3 OR dims_with_2+>=2. Veto also needs wind<10 mph.")
    print()
    for fa in fas:
        v = fa.get("vetoes") or {}
        dry, still, weak = v.get("column_dry_count", 0), v.get("stillness_count", 0), v.get("weak_forcing_count", 0)
        dims = sum([dry >= 2, still >= 2, weak >= 2])
        mx = max(dry, still, weak)
        wind = fa.get("wind_mph")
        wind_blocked = wind is not None and wind >= 10.0
        chorus_fired = v.get("chorus_veto_applied", False)
        gap = []
        if chorus_fired:
            gap.append("chorus fired (EMERGENCY→WARNING); still survives as WARNING")
        elif wind_blocked and (mx >= 3 or dims >= 2):
            gap.append("FIRE met but wind>=10 mph blocked veto")
        elif mx < 3 and dims < 2:
            if mx == 2 and dims == 1:
                gap.append("+1 ch on max dim OR +1 on another dim for FIRE")
            elif mx == 2 and dims == 0:
                gap.append("+1 ch on 2 dims for dims=2")
            elif mx == 1:
                gap.append("+2 on one dim OR +1 on two dims")
            else:
                gap.append("far from FIRE")
        print(f"  {fa['quiet_id']:<25} dry={dry} still={still} weak={weak} dims2+={dims} wind={_fmt(wind,1)}mph | {'; '.join(gap)}")
    print()

    # JSON export
    out_path = ROOT / "runs/false_alarm_autopsy.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(fas, indent=2) + "\n")
    print(f"Full JSON: {out_path}")


def main() -> None:
    fas = run_autopsy()
    print_autopsy(fas)


if __name__ == "__main__":
    main()
