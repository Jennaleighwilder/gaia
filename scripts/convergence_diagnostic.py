#!/usr/bin/env python3
"""
GAIA Convergence Voting Diagnostic

Compares engine voting at first WARNING/EMERGENCY for:
- ONE real event: 2023-08-07 tornado
- ONE false alarm: quiet_2020-04-18_TYS

Shows exactly which engines vote and why.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from runtime.governor import governor
from runtime.governor.governor import (
    CONTEXT_ONLY_ENGINES,
    ENGINE_ORDER,
    GAIA_THRESHOLDS,
    compute_decision_for_payload,
    reset_runtime_state,
)


def load_event_observations(event_id: str) -> dict | None:
    path = ROOT / f"tests/fixtures/historical_observations/event_{event_id}.json"
    if not path.exists():
        return None
    return json.loads(path.read_text())


def load_quiet_dataset(quiet_id: str) -> dict | None:
    path = ROOT / f"tests/fixtures/historical_observations/{quiet_id}.json"
    if not path.exists():
        return None
    return json.loads(path.read_text())


def _pressure_trend(history: list, current: dict) -> str | None:
    if not history:
        return None
    current_pressure = current.get("pressure_mb")
    if current_pressure is None:
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


def _daily_extrema(history: list, current: dict):
    from datetime import datetime, timezone
    current_dt = datetime.fromisoformat(current["timestamp"].replace("Z", "+00:00"))
    same_day = [o for o in history + [current] if
                datetime.fromisoformat(o["timestamp"].replace("Z", "+00:00")).date() == current_dt.date()]
    temps = [o.get("temperature_f") for o in same_day if o.get("temperature_f") is not None]
    if not temps:
        return None, None
    return max(temps), min(temps)


def _describe_sky(obs: dict) -> str:
    sky = obs.get("sky_condition") or ""
    if "OVC" in sky:
        return "overcast"
    if "BKN" in sky:
        return "broken"
    if "SCT" in sky:
        return "scattered"
    return "clear"


def _environmental_context(window: list, event: dict | None) -> dict:
    precip_total = sum((obs.get("precip_1h_in") or 0.0) for obs in window)
    stream_ratio = min(1.5, 0.8 + (precip_total / 2.0))
    return {
        "recent_event_severity": 0.0,
        "precip_7d_ratio": round(min(2.0, precip_total / 1.25), 4),
        "stream_level_ratio": round(stream_ratio, 4),
        "drought_class": 0,
    }


def build_payload(event: dict | None, dataset: dict, obs: dict, history: list, window: list) -> dict:
    previous = history[-1] if history else {}
    daily_high_f, daily_low_f = _daily_extrema(history, obs)
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
    date_str = obs["timestamp"][:10] if obs.get("timestamp") else None
    celestial_ctx = {"date": date_str} if date_str else {}
    return {
        "region": (event or {}).get("county", "quiet_day"),
        "timestamp": obs["timestamp"],
        "station_observations": [station_obs],
        "expected_station_ids": [obs["station_id"]],
        "environmental_context": _environmental_context(window, event),
        "upper_air": dataset.get("upper_air"),
        "celestial": celestial_ctx,
    }


def run_to_first_alarm(dataset: dict, event: dict | None, label: str, celestial_fixture: Path | None):
    """Run observations until first WARNING/EMERGENCY, return that result."""
    reset_runtime_state()
    if celestial_fixture and celestial_fixture.exists():
        governor.CELESTIAL_ENGINE.load_fixture(str(celestial_fixture))

    observations = dataset.get("observations", [])
    history = []
    for obs in observations:
        payload = build_payload(event, dataset, obs, history, observations)
        result = compute_decision_for_payload(payload)
        history.append(obs)
        if result["decision"] in ("WARNING", "EMERGENCY"):
            return result, obs
    return None, None


def print_voting_breakdown(result: dict, label: str):
    """Print the voting breakdown from a governor result."""
    engine_scores = result.get("engine_scores", {})
    convergence_engines = result.get("convergence_engines", [])
    convergence_count = result.get("convergence_count", 0)
    oscillation_score = engine_scores.get("oscillation") or 0.0

    warning_score = GAIA_THRESHOLDS["warning_score"]
    if oscillation_score > 0.5:
        warning_score *= 0.9
    elif oscillation_score < 0.2:
        warning_score *= 1.1

    # Engines that CAN vote = not in CONTEXT_ONLY
    voting_pool = [name for name in ENGINE_ORDER if name not in CONTEXT_ONLY_ENGINES]

    print(f"\n{'='*80}")
    print(f"  {label}")
    print(f"{'='*80}")
    print(f"\n  CONVERGENCE_ENGINES (can vote): {sorted(voting_pool)}")
    print(f"  CONTEXT_ONLY_ENGINES (excluded from voting): {sorted(CONTEXT_ONLY_ENGINES)}")
    print(f"\n  warning_score threshold used: {warning_score:.4f} (base 0.6, oscillation modulates)")
    print(f"  Siren gate: must also have score > 0.3 to vote")
    print(f"\n  Engine voting at first WARNING/EMERGENCY:")
    print(f"  {'Engine':<22} {'Score':>8} {'>=0.6':>8} {'>=thresh':>10} {'Voted':>8} {'In conv':>8}")
    print(f"  {'-'*66}")

    for name in ENGINE_ORDER:
        score = engine_scores.get(name)
        if score is None:
            score_str = "None"
            score_val = None
        else:
            score_val = float(score)
            score_str = f"{score_val:.4f}"

        in_context_only = name in CONTEXT_ONLY_ENGINES
        can_vote = not in_context_only
        ge_06 = "YES" if score_val is not None and score_val >= 0.6 else "NO"
        ge_thresh = "YES" if (score_val is not None and can_vote and
                              (name != "siren" or score_val > 0.3) and score_val >= warning_score) else "NO"
        voted = name in convergence_engines
        in_conv = "YES" if voted else "NO"

        if in_context_only:
            marker = " [CONTEXT]"
        else:
            marker = ""
        print(f"  {name:<22} {score_str:>8} {ge_06:>8} {ge_thresh:>10} {in_conv:>8}{marker}")

    print(f"\n  convergence_count: {convergence_count}")
    print(f"  convergence_engines (who voted): {convergence_engines}")
    print()


def main():
    celestial_fixture = ROOT / "tests/fixtures/historical_kp.json"

    # Real event: 2023-08-07 tornado
    events = json.loads((ROOT / "tests/fixtures/east_tn_severe_events.json").read_text())
    tornado_event = next(e for e in events if e["date"] == "2023-08-07" and e["event_type"] == "tornado")
    tornado_dataset = load_event_observations(tornado_event["event_id"])
    if not tornado_dataset:
        print("ERROR: Could not load 2023-08-07 tornado dataset")
        sys.exit(1)

    tornado_result, _ = run_to_first_alarm(
        tornado_dataset, tornado_event,
        "2023-08-07 tornado (REAL EVENT)",
        celestial_fixture
    )

    # False alarm: quiet_2020-04-18_TYS
    quiet_dataset = load_quiet_dataset("quiet_2020-04-18_TYS")
    if not quiet_dataset:
        print("ERROR: Could not load quiet_2020-04-18_TYS dataset")
        sys.exit(1)

    quiet_result, _ = run_to_first_alarm(
        quiet_dataset, None,
        "quiet_2020-04-18_TYS (FALSE ALARM)",
        celestial_fixture
    )

    if tornado_result:
        print_voting_breakdown(tornado_result, "2023-08-07 tornado (REAL EVENT)")
    else:
        print("ERROR: 2023-08-07 tornado never reached WARNING/EMERGENCY")

    if quiet_result:
        print_voting_breakdown(quiet_result, "quiet_2020-04-18_TYS (FALSE ALARM)")
    else:
        print("ERROR: quiet_2020-04-18_TYS never reached WARNING/EMERGENCY")

    # Side-by-side summary
    print(f"\n{'='*80}")
    print("  SIDE-BY-SIDE SUMMARY")
    print(f"{'='*80}")
    if tornado_result and quiet_result:
        t_conv = tornado_result.get("convergence_engines", [])
        q_conv = quiet_result.get("convergence_engines", [])
        t_count = tornado_result.get("convergence_count", 0)
        q_count = quiet_result.get("convergence_count", 0)
        print(f"\n  {'':20} {'2023-08-07 tornado':>25} {'quiet_2020-04-18':>25}")
        print(f"  {'convergence_count':20} {t_count:>25} {q_count:>25}")
        print(f"  {'convergence_engines':20} {str(t_conv):>25} {str(q_conv):>25}")
        print(f"\n  Engines that vote YES on FALSE ALARM but NOT on REAL EVENT:")
        fa_only = set(q_conv) - set(t_conv)
        print(f"    {fa_only if fa_only else '(none)'}")
        print(f"\n  Engines that vote YES on REAL EVENT but NOT on FALSE ALARM:")
        real_only = set(t_conv) - set(q_conv)
        print(f"    {real_only if real_only else '(none)'}")


def run_all_false_alarms():
    """Run diagnostic on all quiet files that reach WARNING/EMERGENCY."""
    celestial_fixture = ROOT / "tests/fixtures/historical_kp.json"
    quiet_dir = ROOT / "tests/fixtures/historical_observations"
    quiet_files = sorted(quiet_dir.glob("quiet_*.json"))

    results = []
    for path in quiet_files:
        quiet_id = path.stem
        dataset = json.loads(path.read_text())
        reset_runtime_state()
        if celestial_fixture.exists():
            governor.CELESTIAL_ENGINE.load_fixture(str(celestial_fixture))

        observations = dataset.get("observations", [])
        history = []
        for obs in observations:
            payload = build_payload(None, dataset, obs, history, observations)
            result = compute_decision_for_payload(payload)
            history.append(obs)
            if result["decision"] in ("WARNING", "EMERGENCY"):
                eng = result["engine_scores"]
                conv = result.get("convergence_engines", [])
                instability_score = eng.get("instability")
                hist_score = eng.get("historical_analog")
                instability_voted = "instability" in conv
                hist_voted = "historical_analog" in conv
                results.append({
                    "id": quiet_id,
                    "instability_score": instability_score,
                    "instability_voted": instability_voted,
                    "historical_analog_score": hist_score,
                    "historical_analog_voted": hist_voted,
                    "convergence_engines": conv,
                    "convergence_count": result.get("convergence_count", 0),
                })
                break
        else:
            results.append({"id": quiet_id, "alarm": False})

    return results


def main_all_false_alarms():
    """Print breakdown for all quiet days that reach WARNING/EMERGENCY."""
    results = run_all_false_alarms()
    false_alarms = [r for r in results if "convergence_engines" in r]

    print("=" * 80)
    print("FALSE ALARM CONVERGENCE BREAKDOWN (all quiet days that reach WARNING/EMERGENCY)")
    print("=" * 80)

    pattern_count = 0
    for r in false_alarms:
        if "convergence_engines" not in r:
            print(f"\n  {r['id']}: did not reach WARNING/EMERGENCY")
            continue

        inst_s = r.get("instability_score")
        inst_s = f"{inst_s:.4f}" if inst_s is not None else "None"
        inst_v = "YES" if r.get("instability_voted") else "NO"

        hist_s = r.get("historical_analog_score")
        hist_s = f"{hist_s:.4f}" if hist_s is not None else "None"
        hist_v = "YES" if r.get("historical_analog_voted") else "NO"

        if r.get("historical_analog_voted") and not r.get("instability_voted"):
            pattern = "  <-- HIST_YES + INST_NO"
            pattern_count += 1
        else:
            pattern = ""

        print(f"\n  {r['id']}:")
        print(f"    instability:       score={inst_s:>8}  voted={inst_v}")
        print(f"    historical_analog: score={hist_s:>8}  voted={hist_v}")
        print(f"    convergence_count: {r.get('convergence_count', 0)}")
        print(f"    voters: {r.get('convergence_engines', [])}{pattern}")

    print(f"\n{'='*80}")
    print(f"  PATTERN COUNT: historical_analog YES + instability NO = {pattern_count}/{len(false_alarms)}")
    print("=" * 80)


def main_real_event(event_date: str, event_type: str):
    """Print first-alarm scores for a real event (e.g. 2023-03-25 thunderstorm_wind)."""
    celestial_fixture = ROOT / "tests/fixtures/historical_kp.json"
    events = json.loads((ROOT / "tests/fixtures/east_tn_severe_events.json").read_text())
    evt = next((e for e in events if e["date"] == event_date and e["event_type"] == event_type), None)
    if not evt:
        print(f"Event {event_date} {event_type} not found")
        return
    ds = load_event_observations(evt["event_id"])
    if not ds:
        print(f"No dataset for {evt['event_id']}")
        return
    result, _ = run_to_first_alarm(ds, evt, f"{event_date} {event_type}", celestial_fixture)
    if result:
        eng = result["engine_scores"]
        conv = result.get("convergence_engines", [])
        print(f"{event_date} {event_type} first alarm:")
        print(f"  instability={eng.get('instability')}, historical_analog={eng.get('historical_analog')}")
        print(f"  convergence_count={result.get('convergence_count')}, voters={conv}")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--all-false-alarms":
        main_all_false_alarms()
    elif len(sys.argv) >= 3 and sys.argv[1] == "--real-event":
        main_real_event(sys.argv[2], sys.argv[3])
    else:
        main()
