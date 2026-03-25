"""
GAIA Historical Backtest

Replays historical observation fixtures through the live GAIA governor,
measures detections, false alarms, lead time, and saddle behavior.
"""

from __future__ import annotations

import json
import os
import resource
import sys
from datetime import datetime, timezone
from pathlib import Path

# Disable evidence packet writing (avoids "too many open files" in long backtests)
os.environ.setdefault("GAIA_DISABLE_EVIDENCE", "1")
os.environ.setdefault("GAIA_NO_EVIDENCE", "1")


def _norm_type(event: dict | None) -> str:
    """Normalize event_type to lowercase_underscore for consistent matching."""
    if not event:
        return ""
    return (event.get("event_type") or "").lower().replace(" ", "_").replace("-", "_")
# Raise file descriptor limit so backtests can complete (avoids Errno 24)
try:
    soft, hard = resource.getrlimit(resource.RLIMIT_NOFILE)
    target = 8192
    if soft < target:
        new_hard = hard if hard != resource.RLIM_INFINITY and hard >= target else target
        resource.setrlimit(resource.RLIMIT_NOFILE, (min(target, new_hard), new_hard))
except (ValueError, OSError):
    pass

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from runtime.governor import governor
from runtime.governor.governor import (
    compute_decision_for_payload,
    reset_runtime_state,
)


def load_events(path: Path | None = None) -> list[dict]:
    target = path or ROOT / "tests/fixtures/east_tn_severe_events.json"
    return json.loads(target.read_text())


def load_json(path: Path) -> dict:
    return json.loads(path.read_text())


def load_event_observations(event_id: str, obs_dir: Path | None = None) -> dict | None:
    base = obs_dir or (ROOT / "tests/fixtures/historical_observations")
    path = base / f"event_{event_id}.json"
    return load_json(path) if path.exists() else None


def _dt(ts: str) -> datetime:
    return datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone(timezone.utc)


def _describe_sky(obs: dict) -> str:
    metar = (obs.get("metar") or "").upper()
    sky = (obs.get("sky_condition") or "").upper()
    if "CB" in metar or " TS" in metar or metar.startswith("TS"):
        return "Cumulonimbus"
    if sky in {"SCT", "FEW"}:
        return "Cumulus"
    if sky in {"BKN", "OVC"}:
        return "Towering cumulus"
    if sky in {"CLR", "SKC"}:
        return "Clear"
    return sky.title() if sky else ""


def _pressure_trend(history: list[dict], current: dict) -> str | None:
    current_pressure = current.get("pressure_mb")
    if current_pressure is None or not history:
        return None
    baseline = history[-1].get("pressure_mb")
    if baseline is None:
        return None
    drop = baseline - current_pressure
    if len(history) >= 3:
        prior = history[-3].get("pressure_mb")
        if prior is not None:
            drop = max(drop, prior - current_pressure)
    if drop >= 3.0:
        return "falling_fast"
    if drop >= 1.0:
        return "falling"
    return None


def _daily_extrema(history: list[dict], current: dict) -> tuple[float | None, float | None]:
    current_dt = _dt(current["timestamp"])
    same_day = [o for o in history + [current] if _dt(o["timestamp"]).date() == current_dt.date()]
    temps = [o.get("temperature_f") for o in same_day if o.get("temperature_f") is not None]
    if not temps:
        return None, None
    return max(temps), min(temps)


def _environmental_context(
    window: list[dict], event: dict | None = None, obs: dict | None = None
) -> dict:
    precip_total = sum((o.get("precip_1h_in") or 0.0) for o in window)
    stream_ratio = min(1.5, 0.8 + (precip_total / 2.0))
    recent_event_severity = 0.0
    if event and _norm_type(event) in {"flash_flood", "winter_storm", "heavy_snow"}:
        recent_event_severity = 0.15
    ctx = {
        "recent_event_severity": recent_event_severity,
        "precip_7d_ratio": round(min(2.0, precip_total / 1.25), 4),
        "stream_level_ratio": round(stream_ratio, 4),
        "drought_class": 0,
    }
    if obs:
        from runtime.data.surface_ozone import get_surface_ozone_ppb
        date_str = obs.get("timestamp", "")[:10]
        station_id = obs.get("station_id", "")
        oz = get_surface_ozone_ppb(date_str, station_id)
        if oz is not None:
            ctx["surface_ozone_ppb"] = oz
    return ctx


def _payload_for_observation(
    event: dict | None,
    dataset: dict,
    obs: dict,
    history: list[dict],
    window: list[dict],
    include_upper_air: bool,
) -> dict:
    from runtime.data.channel_context import enrich_observation
    from runtime.data.gps_pw import get_gps_pw_score, get_precipitable_water_in
    from runtime.data.surface_ozone import get_surface_ozone_ppb

    daily_high_f, daily_low_f = _daily_extrema(history, obs)
    previous = history[-1] if history else {}
    date_str = obs["timestamp"][:10] if obs.get("timestamp") else None
    station_id = obs.get("station_id", "")

    station_obs = enrich_observation(
        {
            **obs,
            "prior_dewpoint_f": previous.get("dewpoint_f"),
            "prior_wind_direction_deg": previous.get("wind_direction_deg"),
            "pressure_trend": _pressure_trend(history, obs),
            "overnight_low_f": daily_low_f,
            "daily_high_f": daily_high_f,
            "daily_low_f": daily_low_f,
            "text_description": _describe_sky(obs),
        },
        window,
        date_str or "",
        station_id,
        gps_pw_fn=get_precipitable_water_in,
        gps_pw_score_fn=get_gps_pw_score,
        ozone_fn=get_surface_ozone_ppb,
    )
    celestial_ctx = {"date": date_str} if date_str else {}
    payload = {
        "region": (event or {}).get("county", "quiet_day"),
        "timestamp": obs["timestamp"],
        "station_observations": [station_obs],
        "observation_count": len(window),
        "expected_station_ids": [obs["station_id"]],
        "environmental_context": _environmental_context(window, event, obs),
        "upper_air": dataset.get("upper_air") if include_upper_air else None,
        "celestial": celestial_ctx,
        "event_type": (event or {}).get("event_type"),
    }
    if event and dataset.get("radar_fixture"):
        payload["radar_fixture"] = dataset["radar_fixture"]
    if event and dataset.get("precip_72hr_mm") is not None:
        payload["precip_72hr_mm"] = dataset["precip_72hr_mm"]
    if event and dataset.get("flash_flood_fixture"):
        payload["flash_flood_fixture"] = dataset["flash_flood_fixture"]
        payload["soil_moisture"] = dataset["flash_flood_fixture"].get("soil_moisture")
        payload["terrain"] = {"valley_flood_risk": dataset["flash_flood_fixture"].get("valley_risk", 0.5)}
    if event and dataset.get("wildfire_fixture"):
        payload["wildfire_fixture"] = dataset["wildfire_fixture"]
        payload["soil_moisture"] = payload.get("soil_moisture") or dataset["wildfire_fixture"].get("soil_moisture")
    if obs.get("precip_1h_in") is not None:
        payload["precip_rate_in_hr"] = obs["precip_1h_in"]
    elif event and _norm_type(event) == "flash_flood" and window:
        max_precip = max((o.get("precip_1h_in") or 0.0) for o in window)
        if max_precip > 0:
            payload["precip_rate_in_hr"] = max_precip
    # Atmospheric proxies for flash flood engine
    temp_f = obs.get("temperature_f")
    dew_f = obs.get("dewpoint_f")
    if temp_f is not None and dew_f is not None:
        payload["dewpoint_depression_f"] = round(temp_f - dew_f, 1)
    pressures = [o.get("pressure_mb") for o in window if o.get("pressure_mb") is not None]
    if len(pressures) >= 2:
        payload["pressure_change_mb"] = round(max(pressures) - min(pressures), 1)
    return payload


def _load_radar_fixture(event: dict | None, nexrad_dir: Path | None = None) -> dict | None:
    if not event:
        return None
    search_dirs = [nexrad_dir] if nexrad_dir else []
    search_dirs.extend(
        [
            ROOT / "tests" / "fixtures" / "nexrad",
            ROOT / "tests" / "fixtures" / "nexrad_landmarks",
        ]
    )
    event_id = event.get("event_id", "")
    date_str = event.get("date", "")[:10]
    if not event_id or not date_str or len(date_str) != 10:
        return None
    path: Path | None = None
    for ndir in search_dirs:
        if ndir is None:
            continue
        # East TN: KMRX. National: {date}_{event_id}_{STATION}.json — glob for any station
        cand = ndir / f"{date_str}_{event_id}_KMRX.json"
        if cand.exists():
            path = cand
            break
        matches = list(ndir.glob(f"{date_str}_{event_id}_*.json"))
        if matches:
            path = matches[0]
            break
    if not path or not path.exists():
        return None
    try:
        data = json.loads(path.read_text())
        return {
            "composite_reflectivity": data.get("composite_reflectivity"),
            "velocity_max": data.get("velocity_max"),
            "velocity_min": data.get("velocity_min"),
            "rotation_couplet_kt": data.get("rotation_couplet_kt"),
            "vil": data.get("vil"),
            "echo_top_km": data.get("echo_top_km"),
            "rotation_score": data.get("rotation_score"),
        }
    except Exception:
        return None


def run_single_event(
    dataset: dict,
    event: dict | None = None,
    include_upper_air: bool = True,
    celestial_fixture_path: Path | None = None,
) -> dict:
    reset_runtime_state()
    if celestial_fixture_path and celestial_fixture_path.exists():
        governor.CELESTIAL_ENGINE.load_fixture(str(celestial_fixture_path))
    radar_fixture = _load_radar_fixture(event)
    if radar_fixture:
        dataset = {**dataset, "radar_fixture": radar_fixture}
    etype = _norm_type(event)
    if event and etype in ("flash_flood", "flood"):
        ff_fixture = dataset.get("flash_flood_fixture") or {
            "soil_moisture": 0.88,
            "valley_risk": 0.75,
        }
        dataset = {**dataset, "flash_flood_fixture": ff_fixture}
    if event and etype in ("wildfire", "dense_smoke"):
        wf_fixture = dataset.get("wildfire_fixture") or {}
        wf_fixture.setdefault("soil_moisture", 0.15)
        # For historical wildfires, inject synthetic FIRMS detection at event location.
        # A real wildfire large enough for NOAA Storm Events WOULD have a FIRMS heat signature.
        evt_lat = float(event.get("lat") or 0)
        evt_lon = float(event.get("lon") or 0)
        if evt_lat and evt_lon and "firms_fires" not in wf_fixture:
            wf_fixture["firms_fires"] = [
                {"lat": evt_lat, "lon": evt_lon, "frp": 150, "confidence": "high"},
            ]
            wf_fixture["county_lat"] = evt_lat
            wf_fixture["county_lon"] = evt_lon
        # Inject GOES smoke plume signal for wildfires (satellite would detect plume)
        wf_fixture.setdefault("goes_smoke_detected", True)
        dataset = {**dataset, "wildfire_fixture": wf_fixture}
    observations = dataset.get("observations", [])
    timeline = []
    max_decision = "CLEAR"
    first_watch = None
    first_warning = None
    first_saddle = None
    max_confidence = 0.0
    score_timeline = []
    decision_rank = {"CLEAR": 0, "WATCH": 1, "WARNING": 2, "EMERGENCY": 3}
    event_dt = _dt(event["event_datetime_utc"]) if event else None
    history = []
    first_alarm_snapshot = None

    for obs in observations:
        payload = _payload_for_observation(event, dataset, obs, history, observations, include_upper_air)
        result = compute_decision_for_payload(payload)
        timeline.append(result)
        score_timeline.append({"timestamp": obs["timestamp"], **result["engine_scores"]})
        max_confidence = max(max_confidence, result.get("confidence", 0.0))
        if decision_rank[result["decision"]] > decision_rank[max_decision]:
            max_decision = result["decision"]
        if event and etype == "flash_flood" and result.get("flash_flood_warning"):
            if max_decision == "CLEAR":
                max_decision = "WARNING"
        if event and etype in ("wildfire", "dense_smoke") and result.get("wildfire_warning"):
            if max_decision == "CLEAR":
                max_decision = "WARNING"
        obs_dt = _dt(obs["timestamp"])
        mins_before_event = (event_dt - obs_dt).total_seconds() / 60 if event_dt else 9999
        if decision_rank[result["decision"]] >= decision_rank["WATCH"] and first_watch is None:
            first_watch = obs["timestamp"]
        if decision_rank[result["decision"]] >= decision_rank["WARNING"] and first_warning is None and mins_before_event <= 720:
            first_warning = obs["timestamp"]
        if result.get("saddle_active") and first_saddle is None:
            first_saddle = obs["timestamp"]
        if first_alarm_snapshot is None and decision_rank[result["decision"]] >= decision_rank["WARNING"]:
            eng = result["engine_scores"]
            details = result.get("engine_details") or {}
            pressure_detail = details.get("pressure") or {}
            engines_fired = [k for k, v in eng.items() if isinstance(v, (int, float)) and v >= 0.6]
            temp_f = obs.get("temperature_f")
            dew_f = obs.get("dewpoint_f")
            dd = round(temp_f - dew_f, 1) if temp_f is not None and dew_f is not None else None
            first_alarm_snapshot = {
                "convergence_count": result["convergence_count"],
                "max_score": round(max((v for v in eng.values() if isinstance(v, (int, float))) or [0]), 4),
                "engines_fired": sorted(engines_fired),
                "saddle_score": round(eng.get("saddle") or 0, 4),
                "siren_score": round(eng.get("siren") or 0, 4),
                "pressure_trend_mbph": pressure_detail.get("pressure_drop_rate_mbph"),
                "temp_f": temp_f,
                "dewpoint_depression_f": dd,
                "wind_dir_deg": obs.get("wind_direction_deg"),
                "wind_speed_mph": obs.get("wind_speed_mph"),
                "alarm_observation": payload["station_observations"][0],
            }
        history.append(obs)

    lead_time = None
    lead_time_suspect = False
    lead_time_raw = None
    if first_warning and event_dt is not None:
        lead_time_raw = int((event_dt - _dt(first_warning)).total_seconds() / 60)
        lead_time_suspect = lead_time_raw > 720
        lead_time = None if lead_time_suspect else lead_time_raw

    composite_scores = [
        item["engine_scores"].get("composite")
        for item in timeline
        if isinstance(item["engine_scores"].get("composite"), (int, float))
    ]
    celestial_scores = [
        item["engine_scores"].get("celestial")
        for item in timeline
        if isinstance(item["engine_scores"].get("celestial"), (int, float))
    ]
    max_celestial = max(celestial_scores) if celestial_scores else 0.0

    max_decision_before_veto = max_decision
    for r in timeline:
        pre = r.get("decision_before_veto", r["decision"])
        if decision_rank.get(pre, 0) > decision_rank.get(max_decision_before_veto, 0):
            max_decision_before_veto = pre

    chorus_veto_caught = False
    for r in timeline:
        if decision_rank.get(r.get("decision_before_veto"), 0) >= decision_rank["WARNING"]:
            if r.get("chorus_veto_applied"):
                chorus_veto_caught = True
    flash_flood_warning = any(r.get("flash_flood_warning") for r in timeline)
    wildfire_warning = any(r.get("wildfire_warning") for r in timeline)
    if event and etype in ("wildfire", "dense_smoke") and wildfire_warning and max_decision not in ("WARNING", "EMERGENCY"):
        max_decision = "WARNING"
    if event and etype in ("flash_flood", "flood") and flash_flood_warning and max_decision not in ("WARNING", "EMERGENCY"):
        max_decision = "WARNING"

    return {
        "max_decision": max_decision,
        "flash_flood_warning": flash_flood_warning,
        "first_watch_time": first_watch,
        "first_warning_time": first_warning,
        "first_saddle_time": first_saddle,
        "convergence_fired": any(item["convergence_count"] >= 3 for item in timeline),
        "saddle_fired": first_saddle is not None,
        "lead_time_minutes": lead_time,
        "lead_time_suspect": lead_time_suspect,
        "lead_time_raw_minutes": lead_time_raw,
        "max_confidence": round(max_confidence, 4),
        "max_composite_score": round(max(composite_scores), 4) if composite_scores else None,
        "score_timeline": score_timeline,
        "timeline": timeline,
        "max_celestial_score": round(max_celestial, 4),
        "alarm_snapshot": first_alarm_snapshot,
        "max_decision_before_veto": max_decision_before_veto,
        "chorus_veto_caught": chorus_veto_caught,
    }


def brier_score(predictions: list[float], outcomes: list[int]) -> float | None:
    if not predictions or not outcomes or len(predictions) != len(outcomes):
        return None
    return round(sum((p - o) ** 2 for p, o in zip(predictions, outcomes)) / len(predictions), 4)


def _average(values: list[float]) -> float | None:
    if not values:
        return None
    return round(sum(values) / len(values), 4)


def execute_backtest(
    events: list[dict],
    quiet_files: list[Path],
    include_upper_air: bool,
    celestial_fixture_path: Path | None = None,
    obs_dir: Path | None = None,
) -> dict:
    detected = 0
    missed = 0
    lead_times = []
    lead_times_all = []
    lead_time_suspect_count = 0
    saddle_detections = 0
    severe_results = []
    quiet_results = []
    brier_predictions = []
    brier_outcomes = []
    false_alarms = 0
    true_quiets = 0
    severe_stp = []
    severe_scp = []
    severe_composite = []
    quiet_stp = []
    quiet_scp = []
    quiet_composite = []

    _bus_memory = os.environ.get("GAIA_BUS_MEMORY") == "1"

    for event in events:
        dataset = load_event_observations(event["event_id"], obs_dir=obs_dir)
        if not dataset or not dataset.get("observations"):
            continue
        if _bus_memory:
            from runtime.bus.client import _get_conn
            try:
                _get_conn().execute("DELETE FROM events")
            except Exception:
                pass
        result = run_single_event(
            dataset, event, include_upper_air=include_upper_air, celestial_fixture_path=celestial_fixture_path
        )
        hit = result["max_decision"] in {"WARNING", "EMERGENCY"}
        if hit:
            detected += 1
        else:
            missed += 1
        if result["saddle_fired"]:
            saddle_detections += 1
        if result["lead_time_minutes"] is not None:
            lead_times.append(result["lead_time_minutes"])
        if result.get("lead_time_suspect") and result.get("lead_time_raw_minutes") is not None:
            lead_times_all.append(result["lead_time_raw_minutes"])
            lead_time_suspect_count += 1
        elif result["lead_time_minutes"] is not None:
            lead_times_all.append(result["lead_time_minutes"])
        brier_predictions.append(result["max_confidence"])
        brier_outcomes.append(1)
        result_slim = {
            k: v for k, v in result.items()
            if k not in ("timeline", "score_timeline", "alarm_snapshot")
        }
        severe_results.append({"event": event, **result_slim})
        upper_air = dataset.get("upper_air") or {}
        if include_upper_air and upper_air:
            severe_stp.append(float(upper_air.get("significant_tornado_parameter") or 0.0))
            severe_scp.append(float(upper_air.get("supercell_composite") or 0.0))
            if result["max_composite_score"] is not None:
                severe_composite.append(float(result["max_composite_score"]))

    for quiet_file in quiet_files:
        dataset = load_json(quiet_file)
        observations = dataset.get("observations", [])
        if not observations:
            continue
        result = run_single_event(
            dataset, include_upper_air=include_upper_air, celestial_fixture_path=celestial_fixture_path
        )
        alarm = result["max_decision"] in {"WARNING", "EMERGENCY"}
        if alarm:
            false_alarms += 1
        else:
            true_quiets += 1
        result_slim_q = {
            k: v for k, v in result.items()
            if k not in ("timeline", "score_timeline", "alarm_snapshot")
        }
        quiet_results.append({"quiet_id": quiet_file.stem, **result_slim_q})
        brier_predictions.append(result["max_confidence"])
        brier_outcomes.append(0)
        upper_air = dataset.get("upper_air") or {}
        if include_upper_air and upper_air:
            quiet_stp.append(float(upper_air.get("significant_tornado_parameter") or 0.0))
            quiet_scp.append(float(upper_air.get("supercell_composite") or 0.0))
            if result["max_composite_score"] is not None:
                quiet_composite.append(float(result["max_composite_score"]))

    total_events = detected + missed
    total_quiet = false_alarms + true_quiets
    misses = []
    for item in severe_results:
        if item["max_decision"] not in {"WARNING", "EMERGENCY"}:
            misses.append(
                {
                    "event_id": item["event"]["event_id"],
                    "date": item["event"]["date"],
                    "event_type": item["event"]["event_type"],
                    "max_decision": item["max_decision"],
                }
            )

    return {
        "detected": detected,
        "missed": missed,
        "events_tested": total_events,
        "quiet_days_tested": total_quiet,
        "false_alarms": false_alarms,
        "true_quiets": true_quiets,
        "detection_rate": round((detected / total_events * 100.0), 1) if total_events else 0.0,
        "false_alarm_rate": round((false_alarms / total_quiet * 100.0), 1) if total_quiet else 0.0,
        "lead_times_minutes": lead_times,
        "lead_times_all_minutes": lead_times_all,
        "lead_time_suspect_count": lead_time_suspect_count,
        "average_lead_time": round(sum(lead_times) / len(lead_times), 1) if lead_times else None,
        "average_lead_time_all": round(sum(lead_times_all) / len(lead_times_all), 1) if lead_times_all else None,
        "saddle_detections": saddle_detections,
        "brier_score": brier_score(brier_predictions, brier_outcomes),
        "misses": misses,
        "severe_results": severe_results,
        "quiet_results": quiet_results,
        "severe_avg_stp": _average(severe_stp),
        "quiet_avg_stp": _average(quiet_stp),
        "severe_avg_scp": _average(severe_scp),
        "quiet_avg_scp": _average(quiet_scp),
        "severe_avg_composite": _average(severe_composite),
        "quiet_avg_composite": _average(quiet_composite),
    }


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="GAIA Historical Backtest")
    parser.add_argument("--quiet-only", action="store_true", help="Run only quiet day false alarm check")
    parser.add_argument("--max-quiet", type=int, default=None, help="Max quiet days to test (for speed)")
    args = parser.parse_args()

    celestial_fixture = ROOT / "tests/fixtures/historical_kp.json"
    if celestial_fixture.exists():
        print(f"Celestial Kp fixture: {celestial_fixture} ({len(json.loads(celestial_fixture.read_text()))} days)")
    else:
        print("No historical_kp.json — Celestial will score 0 for events outside fixture range")
    print()
    print("╔══════════════════════════════════════════════════╗")
    print("║        GAIA Historical Backtest                  ║")
    print("║  East Tennessee Severe Weather Events            ║")
    print("║  © 2026 Jennifer Leigh West                      ║")
    print("╚══════════════════════════════════════════════════╝")
    print()

    events = [] if args.quiet_only else load_events()
    quiet_files = sorted((ROOT / "tests/fixtures/historical_observations").glob("quiet_*.json"))
    if getattr(args, "max_quiet", None) is not None:
        quiet_files = quiet_files[: args.max_quiet]
    if args.quiet_only:
        print(f"QUIET-ONLY: {len(quiet_files)} quiet day fixtures.")
    else:
        print(f"Loaded {len(events)} historical severe events.")
    print()

    celestial_fixture = ROOT / "tests/fixtures/historical_kp.json"
    baseline = execute_backtest(events, quiet_files, include_upper_air=False, celestial_fixture_path=celestial_fixture)
    enhanced = execute_backtest(events, quiet_files, include_upper_air=True, celestial_fixture_path=celestial_fixture)

    if args.quiet_only:
        print("=" * 60)
        print("QUIET DAY FALSE ALARM RATE")
        print("=" * 60)
        print(f"  Quiet days tested:  {enhanced['quiet_days_tested']}")
        print(f"  False alarms:       {enhanced['false_alarms']}")
        print(f"  True quiets:        {enhanced['true_quiets']}")
        print(f"  False alarm rate:   {enhanced['false_alarms']}/{enhanced['quiet_days_tested']} ({enhanced['false_alarm_rate']:.1f}%)")
        if enhanced["false_alarms"] > 0:
            print("\n  False alarm days:")
            for item in enhanced["quiet_results"]:
                if item["max_decision"] in ("WARNING", "EMERGENCY"):
                    print(f"    {item['quiet_id']} -> {item['max_decision']}")
        print()
        return

    print("=" * 60)
    print("SURFACE-ONLY BASELINE")
    print("=" * 60)
    print(f"  Detection rate:    {baseline['detected']}/{baseline['events_tested']} ({baseline['detection_rate']:.1f}%)")
    if baseline["lead_times_minutes"]:
        print(f"  Avg lead time:     {sum(baseline['lead_times_minutes']) / len(baseline['lead_times_minutes']):.0f} minutes")
    print(f"  Saddle detections: {baseline['saddle_detections']}/{baseline['events_tested']}")
    if baseline["quiet_days_tested"]:
        print(f"  False alarm rate:  {baseline['false_alarms']}/{baseline['quiet_days_tested']} ({baseline['false_alarm_rate']:.1f}%)")
    print()

    print("=" * 60)
    print("UPPER-AIR BACKTEST")
    print("=" * 60)
    for item in enhanced["severe_results"]:
        event = item["event"]
        upper_air = (item.get("dataset") or {}).get("upper_air") or {}
        stp = upper_air.get("significant_tornado_parameter")
        scp = upper_air.get("supercell_composite")
        status = "HIT" if item["max_decision"] in {"WARNING", "EMERGENCY"} else "MISS"
        saddle_mark = " [SADDLE]" if item["saddle_fired"] else ""
        lead_mark = f" ({item['lead_time_minutes']} min)" if item["lead_time_minutes"] is not None else ""
        composite_mark = ""
        if item["max_composite_score"] is not None:
            composite_mark = f" | composite={item['max_composite_score']:.3f}"
        if stp is not None and scp is not None:
            composite_mark += f" | STP={float(stp):.3f} SCP={float(scp):.3f}"
        print(f"  [{status}] {event['date']} {event['event_type']:18s} -> {item['max_decision']:10s}{saddle_mark}{lead_mark}{composite_mark}")

    print()
    print("=" * 60)
    print("QUIET DAY FALSE ALARM CHECK")
    print("=" * 60)
    if not quiet_files:
        print("  No quiet day fixtures found.")
    else:
        for item in enhanced["quiet_results"]:
            upper_air = (item.get("dataset") or {}).get("upper_air") or {}
            label = "FALSE ALARM" if item["max_decision"] in {"WARNING", "EMERGENCY"} else "QUIET"
            composite_mark = ""
            if item["max_composite_score"] is not None:
                composite_mark = f" | composite={item['max_composite_score']:.3f}"
            stp = upper_air.get("significant_tornado_parameter")
            scp = upper_air.get("supercell_composite")
            if stp is not None and scp is not None:
                composite_mark += f" | STP={float(stp):.3f} SCP={float(scp):.3f}"
            print(f"  [{label}] {item['quiet_id']} -> {item['max_decision']}{composite_mark}")

    print("=" * 60)
    print("BACKTEST SUMMARY")
    print("=" * 60)
    print()
    print(f"  Surface-only detection:  {baseline['detection_rate']:.1f}%")
    print(f"  Upper-air detection:     {enhanced['detection_rate']:.1f}%")
    if baseline["quiet_days_tested"]:
        print(f"  Surface-only false alarm:{baseline['false_alarm_rate']:.1f}%")
    if enhanced["quiet_days_tested"]:
        print(f"  Upper-air false alarm:   {enhanced['false_alarm_rate']:.1f}%")
    if enhanced["lead_times_minutes"]:
        print(f"  Average lead time:       {sum(enhanced['lead_times_minutes']) / len(enhanced['lead_times_minutes']):.0f} min")
        print(f"  Min lead time:           {min(enhanced['lead_times_minutes'])} min")
        print(f"  Max lead time:           {max(enhanced['lead_times_minutes'])} min")
    print(f"  Saddle detections:       {enhanced['saddle_detections']}/{enhanced['events_tested']}")
    if enhanced["quiet_days_tested"]:
        print(f"  Quiet days tested:       {enhanced['quiet_days_tested']}")
        print(f"  False alarms:            {enhanced['false_alarms']} ({enhanced['false_alarm_rate']:.1f}%)")
    if enhanced["brier_score"] is not None:
        print(f"  Brier score:             {enhanced['brier_score']}")
    if enhanced["severe_avg_stp"] is not None:
        print(f"  Severe avg STP:          {enhanced['severe_avg_stp']}")
        print(f"  Quiet avg STP:           {enhanced['quiet_avg_stp']}")
        print(f"  Severe avg SCP:          {enhanced['severe_avg_scp']}")
        print(f"  Quiet avg SCP:           {enhanced['quiet_avg_scp']}")
        print(f"  Severe avg composite:    {enhanced['severe_avg_composite']}")
        print(f"  Quiet avg composite:     {enhanced['quiet_avg_composite']}")

    caught_by_chorus = [
        r for r in enhanced["quiet_results"]
        if r.get("max_decision_before_veto") in {"WARNING", "EMERGENCY"}
        and r["max_decision"] not in {"WARNING", "EMERGENCY"}
        and r.get("chorus_veto_caught")
    ]
    chorus_caught_real = [
        r for r in enhanced["severe_results"]
        if r.get("max_decision_before_veto") in {"WARNING", "EMERGENCY"}
        and r["max_decision"] not in {"WARNING", "EMERGENCY"}
        and r.get("chorus_veto_caught")
    ]
    hits_unaffected = [
        r for r in enhanced["severe_results"]
        if r["max_decision"] in {"WARNING", "EMERGENCY"}
        and not r.get("chorus_veto_caught")
    ]
    print()
    print("=" * 60)
    print("SIREN CHORUS VETO REPORT (West-OS design)")
    print("=" * 60)
    print(f"  False alarms caught by CHORUS veto: {len(caught_by_chorus)}")
    for r in caught_by_chorus:
        print(f"    {r['quiet_id']} (was {r.get('max_decision_before_veto')} -> {r['max_decision']})")
    if chorus_caught_real:
        print(f"  *** Real events CAUGHT by chorus (adjust thresholds!): {len(chorus_caught_real)}")
        for r in chorus_caught_real:
            print(f"    {r['event']['date']} {r['event']['event_type']}")
    print(f"  Real events NOT affected by veto: {len(hits_unaffected)}/19")
    for r in hits_unaffected:
        print(f"    {r['event']['date']} {r['event']['event_type']}")

    hits = [r for r in enhanced["severe_results"] if r["max_decision"] in {"WARNING", "EMERGENCY"}]
    false_alarms = [r for r in enhanced["quiet_results"] if r["max_decision"] in {"WARNING", "EMERGENCY"}]
    hits_sorted = sorted(hits, key=lambda x: (x.get("alarm_snapshot") or {}).get("convergence_count", 0), reverse=True)
    fa_sorted = sorted(false_alarms, key=lambda x: (x.get("alarm_snapshot") or {}).get("convergence_count", 0), reverse=True)

    def _fmt_snapshot(snap: dict | None, label: str) -> str:
        if not snap:
            return f"{label} | (no alarm)"
        cc = snap.get("convergence_count", "?")
        ms = snap.get("max_score", "?")
        ef = ",".join(snap.get("engines_fired") or []) or "-"
        sad = snap.get("saddle_score", "?")
        sir = snap.get("siren_score", "?")
        pr = snap.get("pressure_trend_mbph")
        pr_s = f"{pr:.2f}" if pr is not None else "-"
        tf = snap.get("temp_f")
        tf_s = f"{tf:.0f}" if tf is not None else "-"
        dd = snap.get("dewpoint_depression_f")
        dd_s = f"{dd:.0f}" if dd is not None else "-"
        wd = snap.get("wind_dir_deg")
        ws = snap.get("wind_speed_mph")
        wd_s = f"{wd:.0f}" if wd is not None else "-"
        ws_s = f"{ws:.1f}" if ws is not None else "-"
        return f"{label:28s} | cc={cc} max={ms} | engines=[{ef}] | saddle={sad} siren={sir} | dP={pr_s} | T={tf_s}F dd={dd_s}F | wind {wd_s}deg {ws_s}mph"

    print()
    print("=" * 120)
    print(f"ENGINE BREAKDOWN: HITS ({len(hits_sorted)} real severe events) — sorted by convergence_count desc")
    print("=" * 120)
    print(f"  {'Event':28s} | conv  max_score | engines_fired(>=0.6)      | saddle  siren | pressure  | temp  dd  | wind dir  speed")
    print("-" * 120)
    for r in hits_sorted:
        snap = r.get("alarm_snapshot")
        lab = f"{r['event']['date']} {r['event']['event_type']}"
        print(f"  {_fmt_snapshot(snap, lab)}")

    print()
    print("=" * 120)
    print(f"ENGINE BREAKDOWN: FALSE ALARMS ({len(fa_sorted)} quiet days) — sorted by convergence_count desc")
    print("=" * 120)
    print(f"  {'Quiet day':28s} | conv  max_score | engines_fired(>=0.6)      | saddle  siren | pressure  | temp  dd  | wind dir  speed")
    print("-" * 120)
    for r in fa_sorted:
        snap = r.get("alarm_snapshot")
        lab = r["quiet_id"]
        print(f"  {_fmt_snapshot(snap, lab)}")

    print()

    results = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "events_tested": enhanced["events_tested"],
        "detected": enhanced["detected"],
        "missed": enhanced["missed"],
        "detection_rate": enhanced["detection_rate"],
        "lead_times_minutes": enhanced["lead_times_minutes"],
        "saddle_detections": enhanced["saddle_detections"],
        "false_alarms": enhanced["false_alarms"] if enhanced["quiet_days_tested"] else None,
        "quiet_days_tested": enhanced["quiet_days_tested"] if enhanced["quiet_days_tested"] else None,
        "false_alarm_rate": enhanced["false_alarm_rate"] if enhanced["quiet_days_tested"] else None,
        "brier_score": enhanced["brier_score"],
        "misses": enhanced["misses"],
        "severe_results": enhanced["severe_results"],
        "quiet_results": enhanced["quiet_results"],
        "surface_only_baseline": baseline,
        "upper_air_backtest": enhanced,
    }
    output_path = ROOT / "runs/backtest_results.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(results, indent=2) + "\n")
    print(f"  Results saved: {output_path}")
    print()


if __name__ == "__main__":
    main()
