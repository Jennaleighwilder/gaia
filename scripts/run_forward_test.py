#!/usr/bin/env python3
"""
GAIA Forward-Only Validation

Rules:
  - For each event, GAIA sees ONLY observations with timestamps strictly
    before (event_time - buffer).
  - No synthetic fixture injection (FIRMS, GOES smoke, soil/valley).
  - No event_type label passed to the governor (no label leakage).
  - Trusted-time events (non-placeholder) reported separately.

Buffers tested: 0 min, 60 min, 180 min (configurable).

Controls:
  --time-shift N   : shift event dates by N days (positive or negative)
  --ablation MODE  : asos_only | fire_weather_only | all (default: all)
  --negative-days  : run matched non-event control days
"""

from __future__ import annotations

import argparse
import json
import math
import os
import random
import statistics
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

os.environ["GAIA_OFFLINE"] = "1"
os.environ["GAIA_NO_EVIDENCE"] = "1"
os.environ["GAIA_DISABLE_EVIDENCE"] = "1"
os.environ.setdefault("GAIA_BUS_MEMORY", "1")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from runtime.governor.governor import compute_decision_for_payload, reset_runtime_state
from runtime.data.channel_context import enrich_observation
from runtime.engines.common import parse_timestamp


PLACEHOLDER_TIME = "T18:00:00Z"

HAZARD_BUCKETS = {
    "slow_onset": {
        "Blizzard", "Hurricane (Typhoon)", "hurricane", "Tropical Storm",
        "Excessive Heat", "excessive_heat", "Extreme Cold/Wind Chill",
    },
    "conditional_mesoscale": {
        "Tornado", "tornado", "Debris Flow", "Avalanche", "Ice Storm",
        "Wildfire", "wildfire", "Flash Flood", "flash_flood", "Flood",
    },
    "event_onset": {
        "earthquake", "Earthquake",
    },
}

DECISION_RANK = {"CLEAR": 0, "WATCH": 1, "WARNING": 2, "EMERGENCY": 3}


def _dt(ts: str) -> datetime:
    return datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone(timezone.utc)


def _is_placeholder_time(event: dict) -> bool:
    edt = event.get("event_datetime_utc", "")
    return edt.endswith(PLACEHOLDER_TIME)


def _bucket_for(event_type: str) -> str:
    for bucket, types in HAZARD_BUCKETS.items():
        if event_type in types:
            return bucket
    return "unknown"


def _pressure_trend(history: list[dict], current: dict) -> str | None:
    cp = current.get("pressure_mb")
    if cp is None or not history:
        return None
    baseline = history[-1].get("pressure_mb")
    if baseline is None:
        return None
    drop = baseline - cp
    if len(history) >= 3:
        prior = history[-3].get("pressure_mb")
        if prior is not None:
            drop = max(drop, prior - cp)
    if drop >= 3.0:
        return "falling_fast"
    if drop >= 1.0:
        return "falling"
    return None


def _daily_extrema(history: list[dict], current: dict) -> tuple[float | None, float | None]:
    cdt = _dt(current["timestamp"])
    same = [o for o in history + [current] if _dt(o["timestamp"]).date() == cdt.date()]
    temps = [o.get("temperature_f") for o in same if o.get("temperature_f") is not None]
    if not temps:
        return None, None
    return max(temps), min(temps)


def build_clean_payload(obs: dict, history: list[dict], window: list[dict]) -> dict:
    """Build a governor payload with NO event-type leakage and NO synthetic fixtures."""
    from runtime.data.gps_pw import get_gps_pw_score, get_precipitable_water_in
    from runtime.data.surface_ozone import get_surface_ozone_ppb

    daily_high, daily_low = _daily_extrema(history, obs)
    previous = history[-1] if history else {}
    date_str = obs["timestamp"][:10] if obs.get("timestamp") else None
    station_id = obs.get("station_id", "")

    station_obs = enrich_observation(
        {
            **obs,
            "prior_dewpoint_f": previous.get("dewpoint_f"),
            "prior_wind_direction_deg": previous.get("wind_direction_deg"),
            "pressure_trend": _pressure_trend(history, obs),
            "overnight_low_f": daily_low,
            "daily_high_f": daily_high,
            "daily_low_f": daily_low,
        },
        window,
        date_str or "",
        station_id,
        gps_pw_fn=get_precipitable_water_in,
        gps_pw_score_fn=get_gps_pw_score,
        ozone_fn=get_surface_ozone_ppb,
    )

    precip_total = sum((o.get("precip_1h_in") or 0.0) for o in window)

    payload = {
        "region": "forward_test",
        "timestamp": obs["timestamp"],
        "station_observations": [station_obs],
        "observation_count": len(window),
        "expected_station_ids": [station_id],
        "environmental_context": {
            "recent_event_severity": 0.0,
            "precip_7d_ratio": round(min(2.0, precip_total / 1.25), 4),
            "stream_level_ratio": round(min(1.5, 0.8 + precip_total / 2.0), 4),
            "drought_class": 0,
        },
        "upper_air": None,
        "celestial": {"date": date_str} if date_str else {},
        # NO event_type — the governor must decide blind
    }

    temp_f = obs.get("temperature_f")
    dew_f = obs.get("dewpoint_f")
    if temp_f is not None and dew_f is not None:
        payload["dewpoint_depression_f"] = round(temp_f - dew_f, 1)
    pressures = [o.get("pressure_mb") for o in window if o.get("pressure_mb") is not None]
    if len(pressures) >= 2:
        payload["pressure_change_mb"] = round(max(pressures) - min(pressures), 1)
    if obs.get("precip_1h_in") is not None:
        payload["precip_rate_in_hr"] = obs["precip_1h_in"]

    return payload


def run_forward_event(
    observations: list[dict],
    event_time: datetime,
    buffer_minutes: int,
) -> dict:
    """Run governor on observations strictly before cutoff. No fixtures. No label."""
    cutoff = event_time - timedelta(minutes=buffer_minutes)

    pre_event_obs = [o for o in observations if _dt(o["timestamp"]) < cutoff]
    if not pre_event_obs:
        return {"max_decision": "NO_DATA", "n_obs": 0, "first_warning_time": None}

    reset_runtime_state()
    max_decision = "CLEAR"
    first_warning_time = None
    history: list[dict] = []

    for obs in pre_event_obs:
        payload = build_clean_payload(obs, history, pre_event_obs)
        result = compute_decision_for_payload(payload)
        dec = result["decision"]
        if DECISION_RANK.get(dec, 0) > DECISION_RANK[max_decision]:
            max_decision = dec
        if dec in ("WARNING", "EMERGENCY") and first_warning_time is None:
            first_warning_time = obs["timestamp"]
        history.append(obs)

    lead_minutes = None
    if first_warning_time:
        lead_minutes = int((event_time - _dt(first_warning_time)).total_seconds() / 60)

    return {
        "max_decision": max_decision,
        "n_obs": len(pre_event_obs),
        "first_warning_time": first_warning_time,
        "lead_minutes": lead_minutes,
    }


def load_event_observations(event_id: str, obs_dir: Path) -> dict | None:
    path = obs_dir / f"event_{event_id}.json"
    if not path.exists():
        return None
    return json.loads(path.read_text())


def main():
    parser = argparse.ArgumentParser(description="GAIA Forward-Only Validation")
    parser.add_argument("--event-file", default=None)
    parser.add_argument("--obs-dir", default=None)
    parser.add_argument("--buffers", default="0,60,180", help="Comma-separated buffer minutes")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--time-shift", type=int, default=0, help="Shift event dates by N days")
    parser.add_argument("--negative-days", action="store_true", help="Run matched non-event controls")
    args = parser.parse_args()

    event_path = Path(args.event_file) if args.event_file else ROOT / "tests/fixtures/master_validation_corpus.json"
    obs_dir = Path(args.obs_dir) if args.obs_dir else ROOT / "tests/fixtures/historical_observations"
    buffers = [int(b) for b in args.buffers.split(",")]

    corpus = json.loads(event_path.read_text())
    for i, e in enumerate(corpus):
        if not e.get("event_id"):
            e["event_id"] = f"master_{i}"

    # Filter to events with observation fixtures
    have_obs = []
    for e in corpus:
        if (obs_dir / f"event_{e['event_id']}.json").exists():
            have_obs.append(e)
    if args.limit:
        have_obs = have_obs[:args.limit]

    n_trusted = sum(1 for e in have_obs if not _is_placeholder_time(e))
    n_placeholder = sum(1 for e in have_obs if _is_placeholder_time(e))

    print(f"Forward-Only Validation: {len(have_obs)} events")
    print(f"  Trusted timestamps: {n_trusted}")
    print(f"  Placeholder (18:00Z): {n_placeholder}")
    print(f"  Buffers: {buffers} minutes")
    if args.time_shift:
        print(f"  TIME SHIFT CONTROL: {args.time_shift:+d} days")
    print()

    # Per-buffer, per-type results
    # results[buffer][event_type] = {hits, misses, leads, trusted_hits, ...}
    Stat = lambda: {"hits": 0, "misses": 0, "no_data": 0, "leads": [],
                    "trusted_hits": 0, "trusted_total": 0,
                    "placeholder_hits": 0, "placeholder_total": 0}
    results: dict[int, dict[str, dict]] = {b: defaultdict(Stat) for b in buffers}

    bus_memory = os.environ.get("GAIA_BUS_MEMORY") == "1"

    for idx, event in enumerate(have_obs):
        ds = load_event_observations(event["event_id"], obs_dir)
        if not ds or not ds.get("observations"):
            continue

        observations = ds["observations"]
        observations.sort(key=lambda o: o["timestamp"])

        edt_str = event.get("event_datetime_utc", "")
        if not edt_str:
            continue
        event_time = _dt(edt_str)

        if args.time_shift:
            event_time = event_time + timedelta(days=args.time_shift)

        etype = event.get("event_type", "unknown")
        is_trusted = not _is_placeholder_time(event)

        if bus_memory:
            from runtime.bus.client import _get_conn
            try:
                _get_conn().execute("DELETE FROM events")
            except Exception:
                pass

        for buf in buffers:
            r = run_forward_event(observations, event_time, buf)
            stat = results[buf][etype]

            if r["max_decision"] == "NO_DATA":
                stat["no_data"] += 1
                continue

            hit = r["max_decision"] in ("WARNING", "EMERGENCY")
            if hit:
                stat["hits"] += 1
                if r["lead_minutes"] is not None:
                    stat["leads"].append(r["lead_minutes"])
            else:
                stat["misses"] += 1

            if is_trusted:
                stat["trusted_total"] += 1
                if hit:
                    stat["trusted_hits"] += 1
            else:
                stat["placeholder_total"] += 1
                if hit:
                    stat["placeholder_hits"] += 1

        if (idx + 1) % 500 == 0:
            print(f"  processed {idx + 1}/{len(have_obs)}...", flush=True)

    # === NEGATIVE CONTROLS ===
    negative_far = 0  # false alarm rate on quiet days
    negative_total = 0
    if args.negative_days:
        quiet_files = sorted(obs_dir.glob("quiet_*.json"))
        if quiet_files:
            print(f"\n  Running negative controls on {len(quiet_files)} quiet days...", flush=True)
            for qf in quiet_files:
                ds = json.loads(qf.read_text())
                observations = ds.get("observations", [])
                if not observations:
                    continue
                observations.sort(key=lambda o: o["timestamp"])
                if bus_memory:
                    from runtime.bus.client import _get_conn
                    try:
                        _get_conn().execute("DELETE FROM events")
                    except Exception:
                        pass
                reset_runtime_state()
                max_dec = "CLEAR"
                history_q: list[dict] = []
                for obs in observations:
                    p = build_clean_payload(obs, history_q, observations)
                    r = compute_decision_for_payload(p)
                    if DECISION_RANK.get(r["decision"], 0) > DECISION_RANK[max_dec]:
                        max_dec = r["decision"]
                    history_q.append(obs)
                negative_total += 1
                if max_dec in ("WARNING", "EMERGENCY"):
                    negative_far += 1
            print(f"  Negative controls: {negative_far}/{negative_total} false alarms ({100 * negative_far / negative_total:.1f}%)" if negative_total else "  No quiet days.", flush=True)

    # === REPORTING ===
    shift_label = f" [TIME SHIFT {args.time_shift:+d}d]" if args.time_shift else ""
    print()
    print("=" * 110)
    print(f"FORWARD-ONLY RESULTS{shift_label}")
    print("=" * 110)

    for buf in buffers:
        print()
        print(f"--- Buffer: {buf} minutes (observations stop {buf}min before event) ---")
        print()

        header = f"{'Hazard':24s} | {'Bucket':12s} | {'Events':>6s} | {'Recall':>6s} | {'NoData':>6s} | {'Median Lead':>11s} | {'Trusted':>12s} | {'Placeholder':>14s}"
        print(header)
        print("-" * len(header))

        all_hits = all_tested = 0
        all_leads: list[int] = []

        by_bucket: dict[str, dict] = defaultdict(lambda: {"hits": 0, "tested": 0, "leads": []})

        for etype in sorted(results[buf].keys(), key=lambda t: -(results[buf][t]["hits"] + results[buf][t]["misses"])):
            s = results[buf][etype]
            tested = s["hits"] + s["misses"]
            if tested == 0:
                continue
            recall = 100 * s["hits"] / tested
            median_lead = statistics.median(s["leads"]) if s["leads"] else None
            lead_str = f"{median_lead:.0f} min" if median_lead is not None else "-"
            trusted_str = f"{s['trusted_hits']}/{s['trusted_total']}" if s["trusted_total"] else "-"
            ph_str = f"{s['placeholder_hits']}/{s['placeholder_total']}" if s["placeholder_total"] else "-"
            bucket = _bucket_for(etype)

            print(f"{etype:24s} | {bucket:12s} | {tested:6d} | {recall:5.1f}% | {s['no_data']:6d} | {lead_str:>11s} | {trusted_str:>12s} | {ph_str:>14s}")

            all_hits += s["hits"]
            all_tested += tested
            all_leads.extend(s["leads"])
            by_bucket[bucket]["hits"] += s["hits"]
            by_bucket[bucket]["tested"] += tested
            by_bucket[bucket]["leads"].extend(s["leads"])

        print()
        if all_tested:
            overall_recall = 100 * all_hits / all_tested
            overall_median = statistics.median(all_leads) if all_leads else None
            med_str = f"{overall_median:.0f} min" if overall_median is not None else "-"
            print(f"  OVERALL: {all_hits}/{all_tested} ({overall_recall:.1f}%) | median lead: {med_str}")

        print()
        print("  By bucket:")
        for bname in ("slow_onset", "conditional_mesoscale", "event_onset", "unknown"):
            bd = by_bucket.get(bname)
            if not bd or not bd["tested"]:
                continue
            br = 100 * bd["hits"] / bd["tested"]
            bm = statistics.median(bd["leads"]) if bd["leads"] else None
            bm_s = f"{bm:.0f} min" if bm is not None else "-"
            print(f"    {bname:24s}: {bd['hits']}/{bd['tested']} ({br:.1f}%) | median lead: {bm_s}")

    # === THE BRUTAL TABLE ===
    print()
    print("=" * 120)
    print("TIMESTAMP QUALITY vs FORWARD RECALL")
    print("=" * 120)
    buf_headers = " | ".join(f"Fwd@{b}min" for b in buffers)
    print(f"{'Hazard':24s} | {'Events':>6s} | {'Real TS':>7s} | {'Placeholder':>11s} | {buf_headers}")
    print("-" * 120)

    for etype in sorted(results[buffers[0]].keys(), key=lambda t: -(results[buffers[0]][t]["hits"] + results[buffers[0]][t]["misses"])):
        s0 = results[buffers[0]][etype]
        tested = s0["hits"] + s0["misses"]
        if tested == 0:
            continue
        real_ts = s0["trusted_total"]
        ph_ts = s0["placeholder_total"]

        buf_vals = []
        for b in buffers:
            s = results[b][etype]
            t = s["hits"] + s["misses"]
            if t:
                buf_vals.append(f"{100 * s['hits'] / t:5.1f}%")
            else:
                buf_vals.append("    -")
        buf_str = " | ".join(f"{v:>9s}" for v in buf_vals)

        print(f"{etype:24s} | {tested:6d} | {real_ts:7d} | {ph_ts:11d} | {buf_str}")

    if negative_total:
        print()
        print("=" * 80)
        print("NEGATIVE CONTROL (quiet days, no event)")
        print("=" * 80)
        print(f"  Quiet days tested:  {negative_total}")
        print(f"  False alarms:       {negative_far} ({100 * negative_far / negative_total:.1f}%)")
        print(f"  True quiets:        {negative_total - negative_far}")
        if all_tested:
            precision = all_hits / (all_hits + negative_far) if (all_hits + negative_far) else 0
            print(f"  Precision (@ buffer={buffers[-1]}min): {precision:.3f}")

    print()
    print("Done.")


if __name__ == "__main__":
    exit(main())
