#!/usr/bin/env python3
from __future__ import annotations

import csv
import io
import json
import math
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


DATA_DIR = ROOT / "data" / "bio_signal"
DATA_DIR.mkdir(parents=True, exist_ok=True)
STUDIES_PATH = DATA_DIR / "movebank_studies.json"
RESULT_PATH = DATA_DIR / "movebank_anomaly.json"
MOVEBANK_BASE = "https://www.movebank.org/movebank/service/direct-read"
USER_AGENT = "GAIA-Research/1.0 (theforgottencode780@gmail.com)"
SE_BBOX = (-95.0, 30.0, -80.0, 40.0)
OUTBREAKS = [
    ("2023-03-24", "Rolling Fork MS"),
    ("2023-03-31", "Little Rock AR"),
    ("2011-04-27", "SE Super Outbreak"),
    ("2011-05-22", "Joplin MO"),
]


def movebank_query(params: dict[str, str]) -> tuple[int, str, str]:
    url = f"{MOVEBANK_BASE}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "text/csv"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.status, resp.read().decode("utf-8", errors="replace"), url
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8", errors="replace"), url


def displacement_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius_km = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    return 2.0 * radius_km * math.asin(math.sqrt(a))


def main() -> int:
    print("=== ANIMAL MOVEMENT ANOMALY BEFORE TORNADO OUTBREAKS ===")
    print("Looking for behavioral changes 24-48 hours before events...")
    print()

    if not STUDIES_PATH.exists():
        print("Run Step 1 first to find relevant studies")
        return 0

    with STUDIES_PATH.open() as f:
        studies_payload = json.load(f)

    studies = studies_payload.get("relevant_studies", [])
    attempts = studies_payload.get("attempts", [])
    auth_blocked = any(attempt.get("status") in (401, 403) for attempt in attempts)

    output = {
        "source": "Movebank direct-read API event query",
        "bbox": SE_BBOX,
        "auth_blocked": auth_blocked,
        "studies_tested": [],
        "outbreak_results": {},
    }

    if not studies:
        print("No relevant studies are available locally from Step 1.")
        if auth_blocked:
            print("Live Movebank direct-read access appears to require authentication despite public-access docs.")
        with RESULT_PATH.open("w") as f:
            json.dump(output, f, indent=2)
        print(f"Saved to {RESULT_PATH}")
        return 0

    for study in studies[:5]:
        study_id = study.get("id")
        study_name = study.get("name", "")
        output["studies_tested"].append({"id": study_id, "name": study_name})
        print(f"Testing study: {study_name[:60]} (ID: {study_id})")

        for outbreak_date, outbreak_name in OUTBREAKS:
            odate = datetime.strptime(outbreak_date, "%Y-%m-%d")
            start = odate - timedelta(hours=48)
            end = odate + timedelta(hours=6)
            params = {
                "entity_type": "event",
                "study_id": str(study_id),
                "timestamp_start": start.strftime("%Y%m%d%H%M%S000"),
                "timestamp_end": end.strftime("%Y%m%d%H%M%S000"),
                "sensor_type_id": "653",
                "attributes": "individual_id,timestamp,location_lat,location_long,height_above_ellipsoid",
                "bbox": f"{SE_BBOX[0]},{SE_BBOX[1]},{SE_BBOX[2]},{SE_BBOX[3]}",
            }
            status, body, url = movebank_query(params)
            if status != 200 or body.lstrip().startswith("<!doctype html"):
                continue

            rows = list(csv.DictReader(io.StringIO(body)))
            if not rows:
                continue

            print(f"  {outbreak_name}: {len(rows)} location fixes")
            by_animal: dict[str, list[tuple[str, float, float]]] = {}
            for row in rows:
                aid = row.get("individual_id", "")
                try:
                    lat = float(row.get("location_lat", ""))
                    lon = float(row.get("location_long", ""))
                except ValueError:
                    continue
                if not aid:
                    continue
                by_animal.setdefault(aid, []).append((row.get("timestamp", ""), lat, lon))

            displacements: list[float] = []
            for animal_rows in by_animal.values():
                animal_rows.sort(key=lambda item: item[0])
                if len(animal_rows) < 2:
                    continue
                total = 0.0
                for idx in range(1, len(animal_rows)):
                    total += displacement_km(
                        animal_rows[idx - 1][1],
                        animal_rows[idx - 1][2],
                        animal_rows[idx][1],
                        animal_rows[idx][2],
                    )
                displacements.append(total / len(animal_rows))

            if displacements:
                mean_disp = round(sum(displacements) / len(displacements), 3)
                print(f"    Mean displacement/fix: {mean_disp:.2f} km ({len(displacements)} animals)")
                output["outbreak_results"].setdefault(outbreak_name, {})[study_name[:40]] = {
                    "study_id": study_id,
                    "n_animals": len(displacements),
                    "n_fixes": len(rows),
                    "mean_displacement_km": mean_disp,
                    "query_url": url,
                }

    with RESULT_PATH.open("w") as f:
        json.dump(output, f, indent=2)
    print()
    print(f"Saved to {RESULT_PATH}")
    print("WHAT TO LOOK FOR IN RESULTS:")
    print("  Higher displacement before outbreak vs baseline = animals moving more")
    print("  This matches Streby 2014: birds evacuated before TN tornado outbreak")
    print("  Even partial separation adds signal to GAIA ensemble")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
