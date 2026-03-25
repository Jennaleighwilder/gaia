#!/usr/bin/env python3
"""Sample Iowa Mesonet ASOS request for pre-1996 major-event locations (demo)."""
from __future__ import annotations

import csv
import io
import json
import math
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    major_path = ROOT / "tests/fixtures/major_events_1950_present.json"
    if not major_path.exists():
        print("Run build_major_storm_corpus.py first.")
        return 1
    events = json.loads(major_path.read_text())
    pre96 = [
        e
        for e in events
        if int(e.get("year") or 0) < 1996 and float(e.get("lat") or 0) != 0 and float(e.get("lon") or 0) != 0
    ]
    print(f"Pre-1996 major events with coordinates: {len(pre96)}")
    stations = json.loads((ROOT / "data" / "asos_stations.json").read_text())

    def dist(s: dict, lat: float, lon: float) -> float:
        dlat = float(s["lat"]) - lat
        dlon = float(s["lon"]) - lon
        return math.sqrt(dlat**2 + dlon**2)

    out_dir = ROOT / "tests/fixtures/historical_observations_pre96"
    out_dir.mkdir(parents=True, exist_ok=True)
    for i, event in enumerate(pre96[:20]):
        date = event.get("date") or ""
        if len(date) < 10:
            continue
        y, m, d = date[:10].split("-")
        lat = float(event["lat"])
        lon = float(event["lon"])
        nearest = min(stations, key=lambda s: dist(s, lat, lon))
        station = nearest["id"]
        url = (
            "https://mesonet.agron.iastate.edu/cgi-bin/request/asos.py"
            f"?station={station}&data=all"
            f"&year1={y}&month1={m}&day1={d}"
            f"&year2={y}&month2={m}&day2={d}"
            "&tz=UTC&format=comma&latlon=yes"
            "&missing=M&trace=T&direct=no&report_type=3"
        )
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "GAIA/1.0"})
            with urllib.request.urlopen(req, timeout=30) as r:
                text = r.read().decode()
            rows = list(csv.DictReader(io.StringIO(text)))
            if rows:
                out = out_dir / f"{date}_{station}_{i}.json"
                out.write_text(json.dumps({"event": event, "station": station, "observations": rows}, indent=2))
                print(f"  {date} {station}: {len(rows)} obs")
            else:
                print(f"  {date} {station}: no rows")
            time.sleep(0.5)
        except Exception as e:
            print(f"  {date}: {e}")
    print("Pre-96 sample fetch complete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
