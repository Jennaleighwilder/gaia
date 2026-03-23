"""
Build a geographically diverse national backtest sample.
"""

from __future__ import annotations

import json
import random
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
SEED = 42
SAMPLE_PLAN = [
    ("tornado", 50),
    ("destructive_wind", 30),
    ("flash_flood", 20),
    ("winter", 20),
    ("hail", 20),
]
FALLBACK_ORDER = ["flash_flood", "destructive_wind", "hail", "tornado"]


def _is_tornado(event: dict) -> bool:
    return event["event_type"] == "Tornado" and (event.get("tor_f_scale") or "").upper() in {"EF2", "EF3", "EF4", "EF5", "F2", "F3", "F4", "F5"}


def _is_destructive_wind(event: dict) -> bool:
    if event["event_type"] not in {"Thunderstorm Wind", "High Wind", "Strong Wind"}:
        return False
    try:
        return float(event.get("magnitude") or 0.0) >= 75.0 or event.get("is_major")
    except (TypeError, ValueError):
        return bool(event.get("is_major"))


def _is_flash_flood(event: dict) -> bool:
    return event["event_type"] in {"Flash Flood", "Flood", "Heavy Rain"}


def _is_winter(event: dict) -> bool:
    return event["event_type"] in {"Heavy Snow", "Ice Storm", "Winter Storm", "Blizzard", "Winter Weather", "Freezing Rain"}


def _is_hail(event: dict) -> bool:
    if event["event_type"] != "Hail":
        return False
    try:
        return float(event.get("magnitude") or 0.0) >= 2.0 or event.get("is_major")
    except (TypeError, ValueError):
        return bool(event.get("is_major"))


CATEGORY_FILTERS = {
    "tornado": _is_tornado,
    "destructive_wind": _is_destructive_wind,
    "flash_flood": _is_flash_flood,
    "winter": _is_winter,
    "hail": _is_hail,
}


def has_location(event: dict) -> bool:
    return bool(event.get("begin_lat")) and bool(event.get("begin_lon"))


def event_datetime_utc(event: dict) -> str:
    clock = event.get("time_utc") or "18:00"
    return f"{event['date']}T{clock}:00Z"


def balanced_sample(events: list[dict], count: int, rng: random.Random) -> list[dict]:
    buckets: dict[str, list[dict]] = defaultdict(list)
    for event in events:
        buckets[event["state"]].append(event)
    for values in buckets.values():
        rng.shuffle(values)

    ordered_states = sorted(buckets.keys(), key=lambda state: (-len(buckets[state]), state))
    selected = []
    while len(selected) < count and ordered_states:
        next_states = []
        for state in ordered_states:
            if len(selected) >= count:
                break
            if buckets[state]:
                selected.append(buckets[state].pop())
            if buckets[state]:
                next_states.append(state)
        ordered_states = next_states
    return selected


def main() -> None:
    source = ROOT / "data/national_events_major.json"
    if not source.exists():
        print("Missing data/national_events_major.json")
        print("Run scripts/build_national_event_db.py first.")
        return

    events = json.loads(source.read_text())
    events = [event for event in events if has_location(event)]
    rng = random.Random(SEED)

    sampled = []
    used_ids = set()
    shortages = {}
    for category, count in SAMPLE_PLAN:
        filtered = [event for event in events if CATEGORY_FILTERS[category](event) and event["event_id"] not in used_ids]
        picked = balanced_sample(filtered, count, rng)
        shortages[category] = max(0, count - len(picked))
        for event in picked:
            used_ids.add(event["event_id"])
            sampled.append(
                {
                    **event,
                    "sample_category": category,
                    "event_datetime_utc": event_datetime_utc(event),
                }
            )

    for category in FALLBACK_ORDER:
        needed = shortages.get("winter", 0)
        if needed <= 0:
            break
        filtered = [event for event in events if CATEGORY_FILTERS[category](event) and event["event_id"] not in used_ids]
        picked = balanced_sample(filtered, needed, rng)
        for event in picked:
            used_ids.add(event["event_id"])
            sampled.append(
                {
                    **event,
                    "sample_category": "winter_fallback",
                    "fallback_source_category": category,
                    "event_datetime_utc": event_datetime_utc(event),
                }
            )
        shortages["winter"] = max(0, shortages["winter"] - len(picked))

    sampled.sort(key=lambda event: (event["date"], event["state"], event["event_id"]))
    output = ROOT / "data/national_backtest_sample.json"
    output.write_text(json.dumps(sampled, indent=2) + "\n")

    print(f"Sample built: {len(sampled)} severe events")
    for category, _count in SAMPLE_PLAN:
        print(f"  {category}: {sum(1 for event in sampled if event['sample_category'] == category)}")
    print(f"Saved to: {output}")


if __name__ == "__main__":
    main()
