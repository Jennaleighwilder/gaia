#!/usr/bin/env python3
"""
Fetch NEXRAD data for historical tornado events.
Saves to tests/fixtures/nexrad/{date}_{station}.json
"""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def main():
    tornado_path = ROOT / "tests" / "fixtures" / "east_tn_tornado_events.json"
    out_dir = ROOT / "tests" / "fixtures" / "nexrad"
    out_dir.mkdir(parents=True, exist_ok=True)

    from runtime.data.nexrad_fetch import detect_velocity_couplet, fetch_nexrad_for_datetime

    events = json.loads(tornado_path.read_text())
    station = "KMRX"
    fetched = 0
    failed = 0

    for ev in events:
        dt_str = ev.get("event_datetime_utc", "")
        if not dt_str:
            continue
        try:
            dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
        except ValueError:
            continue
        date_str = ev["date"]
        out_file = out_dir / f"{date_str}_{ev['event_id']}_{station}.json"
        if out_file.exists():
            fetched += 1
            continue
        print(f"Fetching {date_str} {ev['event_id']} ...")
        data = fetch_nexrad_for_datetime(station, dt)
        if not data:
            failed += 1
            continue
        rotation_score = detect_velocity_couplet(data)
        result = {
            "event_id": ev["event_id"],
            "date": date_str,
            "event_datetime_utc": dt_str,
            "magnitude": ev.get("magnitude", ""),
            "county": ev.get("county", ""),
            "station": station,
            "composite_reflectivity": data.get("composite_reflectivity"),
            "velocity_max": data.get("velocity_max"),
            "velocity_min": data.get("velocity_min"),
            "rotation_couplet_kt": data.get("rotation_couplet_kt"),
            "rotation_score": rotation_score,
            "vil": data.get("vil"),
            "echo_top_km": data.get("echo_top_km"),
            "tornado_indicated": rotation_score > 0.7,
            "file_key": data.get("file_key"),
        }
        out_file.write_text(json.dumps(result, indent=2) + "\n")
        fetched += 1
        print(f"  -> rotation={rotation_score:.2f} dbz={result.get('composite_reflectivity')}")

    print(f"\nFetched: {fetched}, Failed: {failed}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
