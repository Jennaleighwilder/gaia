#!/usr/bin/env python3
"""
National multi-hazard backtest runner.
Tests GAIA engines against real historical events by hazard type.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

os.environ.setdefault("GAIA_OFFLINE", "1")
os.environ.setdefault("GAIA_NO_EVIDENCE", "1")


def haversine_mi(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 3959
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    return R * 2 * math.asin(math.sqrt(min(1, a)))


HAZMAT_SITES = [
    {"name": "Holston AAP", "lat": 36.548, "lon": -82.566},
    {"name": "Hanford WA", "lat": 46.65, "lon": -119.60},
    {"name": "Savannah River SC", "lat": 33.35, "lon": -81.73},
    {"name": "Oak Ridge TN", "lat": 36.02, "lon": -84.25},
]


def run_seismic_backtest(limit: int = 200) -> dict:
    """Test seismic engine on M4+ earthquakes."""
    from runtime.engines.seismic_engine import SeismicEngine

    corpus_path = ROOT / "tests" / "fixtures" / "national_validation_corpus.json"
    if not corpus_path.exists():
        return {"error": "corpus not found"}

    corpus = json.loads(corpus_path.read_text())
    m4_events = corpus.get("earthquakes_m4plus", [])[:limit]

    se = SeismicEngine()
    detected = missed = hazmat_alerts = 0
    hazmat_log = []

    for eq in m4_events:
        mag = eq.get("magnitude", 0)
        eq_lat = eq.get("lat", 0)
        eq_lon = eq.get("lon", 0)

        payload = {"earthquakes": [eq], "county_lat": eq_lat, "county_lon": eq_lon}
        result = se.score("event_location", payload)
        score = result.get("score", 0)

        if score >= 0.7:
            detected += 1
        else:
            missed += 1

        for site in HAZMAT_SITES:
            dist = haversine_mi(eq_lat, eq_lon, site["lat"], site["lon"])
            if dist < 50 and mag >= 4.0:
                hazmat_alerts += 1
                hazmat_log.append(f"M{mag} {eq.get('date','')} near {site['name']} ({dist:.0f}mi)")

    return {
        "hazard": "earthquake",
        "total": len(m4_events),
        "detected": detected,
        "missed": missed,
        "detection_rate_pct": round(detected / len(m4_events) * 100, 1) if m4_events else 0,
        "hazmat_alerts": hazmat_alerts,
        "hazmat_log": hazmat_log[:10],
    }


def run_landslide_backtest(limit: int = 100) -> dict:
    """Placeholder: mudslide engine on landslide events."""
    landslide_path = ROOT / "tests" / "fixtures" / "usgs_landslides" / "landslide_events.json"
    if not landslide_path.exists():
        return {"error": "landslide corpus not found"}

    events = json.loads(landslide_path.read_text())[:limit]
    return {
        "hazard": "landslide",
        "total": len(events),
        "note": "Mudslide engine validation pending",
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--hazard", choices=["earthquake", "landslide", "all"], default="earthquake")
    ap.add_argument("--limit", type=int, default=200)
    args = ap.parse_args()

    results = []
    if args.hazard in ("earthquake", "all"):
        r = run_seismic_backtest(limit=args.limit)
        results.append(r)
    if args.hazard in ("landslide", "all"):
        r = run_landslide_backtest(limit=args.limit)
        results.append(r)

    for r in results:
        print(json.dumps(r, indent=2))
        print()


if __name__ == "__main__":
    main()
