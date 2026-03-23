#!/usr/bin/env python3
"""
Channel Separation Diagnostic — score new channels alongside backtest,
report severe vs false-alarm separation for each.

Finds the channel that finally splits the 52.9%.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts.run_backtest import (
    load_events,
    load_json,
    load_event_observations,
    _payload_for_observation,
    run_single_event,
)
from runtime.governor import governor
from runtime.governor.governor import compute_decision_for_payload, reset_runtime_state

CELESTIAL_FIXTURE = ROOT / "tests/fixtures/historical_kp.json"


def run_diagnostic() -> dict:
    reset_runtime_state()
    if CELESTIAL_FIXTURE.exists():
        governor.CELESTIAL_ENGINE.load_fixture(str(CELESTIAL_FIXTURE))

    # Use full events for more severe-event coverage (match run_full_backtest)
    full_path = ROOT / "tests/fixtures/east_tn_full_events.json"
    events = load_events(full_path) if full_path.exists() else load_events()
    events = [e for e in events if load_event_observations(e["event_id"])]
    quiet_files = sorted((ROOT / "tests/fixtures/historical_observations").glob("quiet_*.json"))

    new_channel_keys = (
        "pressure_acceleration", "t_td_crossover_velocity", "wind_dir_variance",
        "pressure_temperature_divergence_index", "vis_collapse_rate", "sky_cover_trend",
        "gust_factor_trend", "cross_station_gradient",
    )
    channel_keys = (
        "gps_pw", "harmonic", "overnight_cooling_rate", "t_td_convergence",
        "daytime_heating_rate", "surface_ozone", "thermal", "moisture", "instability",
        *new_channel_keys,
    )

    def _collect_from_obs(alarm_obs: dict | None, channel_dict: dict, new_keys: tuple) -> None:
        if not alarm_obs:
            return
        for k in new_keys:
            v = alarm_obs.get(k)
            if v is not None:
                channel_dict[k].append(float(v))

    def _collect_with_details():
        reset_runtime_state()
        if CELESTIAL_FIXTURE.exists():
            governor.CELESTIAL_ENGINE.load_fixture(str(CELESTIAL_FIXTURE))
        sev_ch = {k: [] for k in channel_keys}
        fa_ch = {k: [] for k in channel_keys}
        for event in events:
            dataset = load_event_observations(event["event_id"])
            if not dataset or not dataset.get("observations"):
                continue
            result = run_single_event(dataset, event, include_upper_air=True, celestial_fixture_path=CELESTIAL_FIXTURE)
            if result["max_decision"] not in ("WARNING", "EMERGENCY"):
                continue
            alarm_obs = (result.get("alarm_snapshot") or {}).get("alarm_observation")
            for i, r in enumerate(result["timeline"]):
                if r["decision"] in ("WARNING", "EMERGENCY"):
                    eng = r.get("engine_details") or {}
                    td = eng.get("thermal") or {}
                    md = eng.get("moisture") or {}
                    id_ = eng.get("instability") or {}
                    ed = eng.get("environmental") or {}
                    tc = td.get("channels") or {}
                    mc = md.get("channels") or {}
                    ic = id_.get("channels") or {}
                    ec = ed.get("channels") or {}
                    for k, src in [
                        ("overnight_cooling_rate", tc),
                        ("daytime_heating_rate", ic),
                        ("t_td_convergence", mc),
                        ("gps_pw", mc),
                        ("surface_ozone", ec),
                    ]:
                        v = src.get(k)
                        if v is not None:
                            sev_ch[k].append(v)
                    for k in ("thermal", "moisture", "instability", "harmonic"):
                        v = r.get("engine_scores", {}).get(k)
                        if v is not None:
                            sev_ch[k].append(v)
                    _collect_from_obs(alarm_obs, sev_ch, new_channel_keys)
                    break
        fa_quiet_ids = []
        for qf in quiet_files:
            dataset = load_json(qf)
            if not dataset.get("observations"):
                continue
            result = run_single_event(dataset, include_upper_air=True, celestial_fixture_path=CELESTIAL_FIXTURE)
            if result["max_decision"] not in ("WARNING", "EMERGENCY"):
                continue
            fa_quiet_ids.append(qf.stem)
            alarm_obs = (result.get("alarm_snapshot") or {}).get("alarm_observation")
            for i, r in enumerate(result["timeline"]):
                if r["decision"] in ("WARNING", "EMERGENCY"):
                    eng = r.get("engine_details") or {}
                    td = eng.get("thermal") or {}
                    md = eng.get("moisture") or {}
                    id_ = eng.get("instability") or {}
                    ed = eng.get("environmental") or {}
                    tc = td.get("channels") or {}
                    mc = md.get("channels") or {}
                    ic = id_.get("channels") or {}
                    ec = ed.get("channels") or {}
                    for k, src in [
                        ("overnight_cooling_rate", tc),
                        ("daytime_heating_rate", ic),
                        ("t_td_convergence", mc),
                        ("gps_pw", mc),
                        ("surface_ozone", ec),
                    ]:
                        v = src.get(k)
                        if v is not None:
                            fa_ch[k].append(v)
                    for k in ("thermal", "moisture", "instability", "harmonic"):
                        v = r.get("engine_scores", {}).get(k)
                        if v is not None:
                            fa_ch[k].append(v)
                    _collect_from_obs(alarm_obs, fa_ch, new_channel_keys)
                    break
        return sev_ch, fa_ch, fa_quiet_ids

    severe_channel_values, quiet_channel_values, fa_ids = _collect_with_details()

    return {
        "severe": severe_channel_values,
        "false_alarm": quiet_channel_values,
        "fa_quiet_ids": fa_ids,
        "severe_count": max(len(severe_channel_values.get("thermal", [])), 1),
        "fa_count": max(len(quiet_channel_values.get("thermal", [])), 1),
    }


def main():
    print("Channel Separation Diagnostic — GAIA Phase 7c")
    print("=" * 70)
    data = run_diagnostic()
    sev = data["severe"]
    fa = data["false_alarm"]

    print(f"\nSevere events (first alarm): {sum(len(sev[k]) for k in sev)} values across channels")
    print(f"False alarm days: {sum(len(fa[k]) for k in fa)} values across channels")

    def _avg(arr):
        return sum(arr) / len(arr) if arr else None

    def _sep(sev_arr, fa_arr):
        a = _avg(sev_arr)
        b = _avg(fa_arr)
        if a is None or b is None:
            return None
        return abs(a - b)

    print("\n" + "=" * 70)
    print("CHANNEL SEPARATION (severe avg vs false alarm avg)")
    print("=" * 70)
    print(f"{'Channel':<35} | {'Severe avg':>10} | {'FA avg':>10} | {'Separation':>10} | N_sev N_fa")
    print("-" * 80)

    all_channels = (
        "gps_pw", "overnight_cooling_rate", "t_td_convergence", "daytime_heating_rate",
        "surface_ozone", "harmonic", "thermal", "moisture", "instability",
        "pressure_acceleration", "t_td_crossover_velocity", "wind_dir_variance",
        "pressure_temperature_divergence_index", "vis_collapse_rate", "sky_cover_trend",
        "gust_factor_trend", "cross_station_gradient",
    )
    for ch in all_channels:
        sev_arr = sev.get(ch, [])
        fa_arr = fa.get(ch, [])
        a = _avg(sev_arr)
        b = _avg(fa_arr)
        sep = _sep(sev_arr, fa_arr)
        a_s = f"{a:.4f}" if a is not None else "—"
        b_s = f"{b:.4f}" if b is not None else "—"
        sep_s = f"{sep:.4f}" if sep is not None else "—"
        print(f"{ch:<35} | {a_s:>10} | {b_s:>10} | {sep_s:>10} | {len(sev_arr)} {len(fa_arr)}")

    print("\nHigher separation = better discriminator.")
    print("New channels: pressure_acceleration (2nd deriv), wind_dir_variance, vis_collapse_rate, etc.")

    fa_ids = data.get("fa_quiet_ids", [])
    fa_gps_pw = fa.get("gps_pw", [])
    high_pw_fa = [(fa_ids[i], v) for i, v in enumerate(fa_gps_pw) if v is not None and v > 0.5]
    if high_pw_fa:
        print("\n" + "=" * 70)
        print("FALSE ALARMS WITH HIGH gps_pw (>0.5) — real PW makes these look moist")
        print("=" * 70)
        for qid, val in sorted(high_pw_fa, key=lambda x: -x[1]):
            print(f"  {qid}: gps_pw={val:.3f}")

    top3_survivors = sorted(
        [(fa_ids[i], fa_gps_pw[i] or 0) for i in range(min(len(fa_ids), len(fa_gps_pw)))],
        key=lambda x: -x[1]
    )[:3]
    print("\nTop 3 false alarm survivors (by gps_pw):")
    for qid, val in top3_survivors:
        print(f"  {qid}: gps_pw={val:.3f}")

    out_path = ROOT / "runs/channel_separation.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps({
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "severe": {k: {"mean": _avg(v), "n": len(v), "values": v[:20]} for k, v in sev.items()},
        "false_alarm": {k: {"mean": _avg(v), "n": len(v), "values": v[:20]} for k, v in fa.items()},
        "fa_quiet_ids": data.get("fa_quiet_ids", []),
        "gps_pw_separation_gap": _sep(sev.get("gps_pw", []), fa.get("gps_pw", [])),
    }, indent=2) + "\n")
    print(f"\nResults saved: {out_path}")


if __name__ == "__main__":
    main()
