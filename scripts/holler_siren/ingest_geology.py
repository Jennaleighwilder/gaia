#!/usr/bin/env python3
from __future__ import annotations

import json
import math
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data" / "holler_siren"
DATA_DIR.mkdir(parents=True, exist_ok=True)

USER_AGENT = "HollerSiren/1.0"
FULL_WESTERN_BBOX = (-84.3, 35.0, -81.8, 36.6)  # west, south, east, north
GEO_CACHE = DATA_DIR / "nc_geology.json"

WEAK_ROCKS = ["schist", "phyllite", "meta", "gneiss", "slate", "shale"]
STRONG_ROCKS = ["granite", "quartzite", "rhyolite", "basalt", "sandstone"]


def rock_risk(rock_type: str) -> float:
    value = rock_type.lower()
    if any(token in value for token in WEAK_ROCKS):
        return 0.2
    if any(token in value for token in STRONG_ROCKS):
        return 0.0
    return 0.1


def macrostrat_point(lat: float, lon: float) -> dict | None:
    url = f"https://macrostrat.org/api/v2/geologic_units/map?lat={lat:.4f}&lng={lon:.4f}"
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=30) as resp:
        payload = json.loads(resp.read().decode())
    rows = payload.get("success", {}).get("data", [])
    if not rows:
        return None
    row = rows[0]
    rock_type = str(row.get("lith") or row.get("name") or "unknown")
    return {
        "lat": round(lat, 4),
        "lon": round(lon, 4),
        "rock_type": rock_type,
        "unit_name": row.get("name", ""),
        "risk": rock_risk(rock_type),
    }


def build_sample_grid(step_deg: float = 0.10) -> dict:
    if GEO_CACHE.exists():
        with GEO_CACHE.open() as f:
            return json.load(f)

    west, south, east, north = FULL_WESTERN_BBOX
    samples = []
    lat = south
    while lat <= north + 1e-9:
        lon = west
        while lon <= east + 1e-9:
            try:
                result = macrostrat_point(lat, lon)
                if result is not None:
                    samples.append(result)
            except Exception:
                pass
            lon += step_deg
        lat += step_deg

    payload = {
        "source": "Macrostrat fallback",
        "bbox": FULL_WESTERN_BBOX,
        "step_deg": step_deg,
        "samples": samples,
    }
    with GEO_CACHE.open("w") as f:
        json.dump(payload, f)
    return payload


def main() -> int:
    print("=== STEP 2: NC BEDROCK GEOLOGY ===")
    print("NC OneMap WFS not exposed from the current public service list; using Macrostrat fallback.")
    data = build_sample_grid()
    samples = data.get("samples", [])
    print(f"Geology features available: {len(samples)}")
    rock_types = sorted({sample.get('rock_type', '') for sample in samples if sample.get('rock_type')})
    print(f"Rock types found: {rock_types[:10]}")
    print(f"Saved geology cache to {GEO_CACHE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
