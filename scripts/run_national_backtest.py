"""
Run GAIA against the sampled national backtest fixtures.
"""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from runtime.governor.governor import compute_decision_for_payload, reset_runtime_state
from runtime.memory.event_memory import EventMemory


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
    same_day = [item for item in history + [current] if _dt(item["timestamp"]).date() == current_dt.date()]
    temps = [item.get("temperature_f") for item in same_day if item.get("temperature_f") is not None]
    if not temps:
        return None, None
    return max(temps), min(temps)


def _environmental_context(window: list[dict], event_type: str | None = None) -> dict:
    precip_total = sum((obs.get("precip_1h_in") or 0.0) for obs in window)
    recent_event_severity = 0.15 if event_type in {"Flash Flood", "Flood", "Winter Storm", "Heavy Snow"} else 0.0
    return {
        "recent_event_severity": recent_event_severity,
        "precip_7d_ratio": round(min(2.0, precip_total / 1.25), 4),
        "stream_level_ratio": round(min(1.5, 0.8 + (precip_total / 2.0)), 4),
        "drought_class": 0,
    }


def _payload_for_observation(dataset: dict, obs: dict, history: list[dict], window: list[dict]) -> dict:
    daily_high_f, daily_low_f = _daily_extrema(history, obs)
    previous = history[-1] if history else {}
    station_obs = {
        **obs,
        "prior_dewpoint_f": previous.get("dewpoint_f"),
        "prior_wind_direction_deg": previous.get("wind_direction_deg"),
        "pressure_trend": _pressure_trend(history, obs),
        "overnight_low_f": daily_low_f,
        "daily_high_f": daily_high_f,
        "daily_low_f": daily_low_f,
        "text_description": _describe_sky(obs),
    }
    return {
        "region": dataset.get("state", "unknown_state"),
        "timestamp": obs["timestamp"],
        "station_observations": [station_obs],
        "expected_station_ids": [obs["station_id"]],
        "environmental_context": _environmental_context(window, dataset.get("event_type")),
        "upper_air": dataset.get("upper_air"),
        "daily_summaries": dataset.get("daily_summaries", []),
    }


def run_dataset(dataset: dict) -> dict:
    reset_runtime_state()
    observations = dataset.get("observations", [])
    history = []
    max_decision = "CLEAR"
    first_warning = None
    first_saddle = None
    max_confidence = 0.0
    max_composite = None
    timeline = []
    decision_rank = {"CLEAR": 0, "WATCH": 1, "WARNING": 2, "EMERGENCY": 3}

    for obs in observations:
        payload = _payload_for_observation(dataset, obs, history, observations)
        result = compute_decision_for_payload(payload)
        timeline.append(result)
        if decision_rank[result["decision"]] > decision_rank[max_decision]:
            max_decision = result["decision"]
        if decision_rank[result["decision"]] >= decision_rank["WARNING"] and first_warning is None:
            first_warning = obs["timestamp"]
        if result.get("saddle_active") and first_saddle is None:
            first_saddle = obs["timestamp"]
        max_confidence = max(max_confidence, result.get("confidence", 0.0))
        composite = result["engine_scores"].get("composite")
        if isinstance(composite, (int, float)):
            max_composite = composite if max_composite is None else max(max_composite, composite)
        history.append(obs)

    return {
        "max_decision": max_decision,
        "first_warning_time": first_warning,
        "saddle_fired": first_saddle is not None,
        "max_confidence": round(max_confidence, 4),
        "max_composite_score": round(max_composite, 4) if max_composite is not None else None,
        "timeline": timeline,
    }


def main() -> None:
    fixtures_dir = ROOT / "data/national_history"
    severe_files = sorted(fixtures_dir.glob("event_*.json"))
    quiet_files = sorted(fixtures_dir.glob("quiet_*.json"))[:100]
    if not severe_files:
        print("No national severe fixtures found.")
        print("Run scripts/pull_national_history.py first.")
        return

    memory = EventMemory(str(ROOT / "data/memory/event_memory.jsonl"))

    detected = 0
    missed = 0
    false_alarms = 0
    true_quiets = 0
    severe_by_category = defaultdict(lambda: {"tested": 0, "detected": 0})
    severe_by_engine = defaultdict(list)
    quiet_by_engine = defaultdict(list)

    print("GAIA National Backtest")
    print("=" * 60)
    print(f"Severe fixtures: {len(severe_files)}")
    print(f"Quiet fixtures:  {len(quiet_files)}")
    print()

    for severe_file in severe_files:
        dataset = json.loads(severe_file.read_text())
        if not dataset.get("observations"):
            continue
        result = run_dataset(dataset)
        hit = result["max_decision"] in {"WARNING", "EMERGENCY"}
        category = dataset.get("sample_category", "unknown")
        severe_by_category[category]["tested"] += 1
        if hit:
            detected += 1
            severe_by_category[category]["detected"] += 1
        else:
            missed += 1
        last_scores = result["timeline"][-1]["engine_scores"] if result["timeline"] else {}
        for name, value in last_scores.items():
            if isinstance(value, (int, float)):
                severe_by_engine[name].append(value)
        memory.record_outcome(
            dataset["event_id"],
            {
                "event_occurred": True,
                "event_type": dataset.get("event_type"),
                "event_severity": dataset.get("sample_category"),
                "was_correct": hit,
                "was_false_alarm": False,
                "was_miss": not hit,
            },
        )

    for quiet_file in quiet_files:
        dataset = json.loads(quiet_file.read_text())
        if not dataset.get("observations"):
            continue
        result = run_dataset(dataset)
        alarm = result["max_decision"] in {"WARNING", "EMERGENCY"}
        if alarm:
            false_alarms += 1
        else:
            true_quiets += 1
        last_scores = result["timeline"][-1]["engine_scores"] if result["timeline"] else {}
        for name, value in last_scores.items():
            if isinstance(value, (int, float)):
                quiet_by_engine[name].append(value)
        memory.record_outcome(
            dataset["quiet_id"],
            {
                "event_occurred": False,
                "event_type": "quiet_day",
                "event_severity": "none",
                "was_correct": not alarm,
                "was_false_alarm": alarm,
                "was_miss": False,
            },
        )

    severe_total = detected + missed
    quiet_total = false_alarms + true_quiets
    detection_rate = round((detected / severe_total * 100.0), 1) if severe_total else 0.0
    false_alarm_rate = round((false_alarms / quiet_total * 100.0), 1) if quiet_total else 0.0

    engine_discrimination = {}
    for engine in sorted(set(severe_by_engine) | set(quiet_by_engine)):
        severe_values = severe_by_engine.get(engine, [])
        quiet_values = quiet_by_engine.get(engine, [])
        if not severe_values and not quiet_values:
            continue
        engine_discrimination[engine] = {
            "severe_avg": round(sum(severe_values) / len(severe_values), 4) if severe_values else None,
            "quiet_avg": round(sum(quiet_values) / len(quiet_values), 4) if quiet_values else None,
        }

    calibration = memory.compute_calibration()

    print(f"Detection rate:    {detected}/{severe_total} ({detection_rate:.1f}%)")
    print(f"False alarm rate:  {false_alarms}/{quiet_total} ({false_alarm_rate:.1f}%)")
    print()
    print("By category:")
    for category, stats in sorted(severe_by_category.items()):
        rate = round((stats['detected'] / stats['tested'] * 100.0), 1) if stats["tested"] else 0.0
        print(f"  {category:18s} {stats['detected']}/{stats['tested']} ({rate:.1f}%)")
    print()
    print("Engine discrimination (severe avg vs quiet avg):")
    for engine, stats in engine_discrimination.items():
        print(f"  {engine:18s} {stats['severe_avg']} vs {stats['quiet_avg']}")
    print()
    print("Memory calibration snapshot:")
    print(json.dumps(calibration, indent=2))

    results = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "severe_tested": severe_total,
        "quiet_tested": quiet_total,
        "detected": detected,
        "missed": missed,
        "false_alarms": false_alarms,
        "true_quiets": true_quiets,
        "detection_rate": detection_rate,
        "false_alarm_rate": false_alarm_rate,
        "by_category": severe_by_category,
        "engine_discrimination": engine_discrimination,
        "memory_calibration": calibration,
    }
    output = ROOT / "runs/national_backtest_results.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(results, indent=2) + "\n")
    print()
    print(f"Saved to: {output}")


if __name__ == "__main__":
    main()
