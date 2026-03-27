#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
import math
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


DATA_DIR = ROOT / "data" / "holler_siren"
HELENE_PATH = DATA_DIR / "helene_landslides.csv"
TWI_PATH = DATA_DIR / "tfi_twi_yancey_mitchell.json"


def _find_lat_lon_cols(sample: dict) -> tuple[str | None, str | None]:
    lat_col = next((k for k in sample if "lat" in k.lower()), None)
    lon_col = next((k for k in sample if "lon" in k.lower() or k.lower() == "x"), None)
    return lat_col, lon_col


def _failure_proximity_score(lat: float, lon: float, failures: list[tuple[float, float]]) -> tuple[float, float, int]:
    count = 0
    min_dist = float("inf")
    km_per_deg_lat = 111.32

    for f_lat, f_lon in failures:
        dlat = (f_lat - lat) * km_per_deg_lat
        dlon = (f_lon - lon) * km_per_deg_lat * math.cos(math.radians(lat))
        dist = math.sqrt(dlat**2 + dlon**2)
        if dist < 2.0:
            count += 1
        if dist < min_dist:
            min_dist = dist

    score = min(count / 5.0, 1.0) * 0.30
    return round(score, 3), round(min_dist, 3), count


def main() -> int:
    print("=== PRIOR FAILURE LAYER ===")
    with HELENE_PATH.open() as f:
        landslides = list(csv.DictReader(f))

    lat_col, lon_col = _find_lat_lon_cols(landslides[0])
    if lat_col is None or lon_col is None:
        raise RuntimeError("Could not find lat/lon columns in Helene inventory")

    all_failures: list[tuple[float, float]] = []
    for landslide in landslides:
        try:
            lat = float(landslide.get(lat_col, 0))
            lon = float(landslide.get(lon_col, 0))
        except (TypeError, ValueError):
            continue
        if lat and lon:
            all_failures.append((lat, lon))

    print(f"Total Helene failures: {len(all_failures)}")

    with TWI_PATH.open() as f:
        tfi_data = json.load(f)
    cells = tfi_data["cells"]

    print("Computing prior failure proximity for each cell...")
    updated: list[dict] = []
    for cell in cells:
        score, min_dist, nearby = _failure_proximity_score(
            float(cell["lat"]),
            float(cell["lon"]),
            all_failures,
        )
        updated_cell = cell.copy()
        updated_cell["prior_failure_score"] = score
        updated_cell["nearest_helene_km"] = min_dist
        updated_cell["helene_failures_within_2km"] = nearby
        updated.append(updated_cell)

    print(f"Cells with nearby Helene failures: {sum(1 for cell in updated if cell['prior_failure_score'] > 0)}")
    print(f"Cells with score > 0.1: {sum(1 for cell in updated if cell['prior_failure_score'] > 0.1)}")
    print(f"Cells with score > 0.2: {sum(1 for cell in updated if cell['prior_failure_score'] > 0.2)}")

    ranked = sorted(updated, key=lambda cell: (cell["prior_failure_score"], -cell["nearest_helene_km"]), reverse=True)
    print("\nTop 10 prior-failure cells:")
    for cell in ranked[:10]:
        print(
            f"  ({cell['lat']:.4f}, {cell['lon']:.4f}): "
            f"score={cell['prior_failure_score']:.3f} "
            f"nearby={cell['helene_failures_within_2km']} "
            f"nearest={cell['nearest_helene_km']:.3f}km"
        )

    tfi_data["cells"] = updated
    layers = list(tfi_data.get("data_layers_included", []))
    if "prior_failure" not in layers:
        layers.append("prior_failure")
    tfi_data["data_layers_included"] = layers
    with TWI_PATH.open("w") as f:
        json.dump(tfi_data, f)
    print("Prior failure layer added and saved")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
