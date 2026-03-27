#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TERRAIN_PATH = ROOT / "data" / "holler_siren" / "terrain_yancey_mitchell.json"
TFI_PATH = ROOT / "data" / "holler_siren" / "tfi_yancey_mitchell.json"


def main() -> int:
    with TERRAIN_PATH.open() as f:
        terrain = json.load(f)

    print(f"Computing TFI for {terrain['n_cells']} cells...")
    print(f"Pilot area: {terrain['pilot_area']}")
    print()

    tfi_cells: list[dict] = []
    for cell in terrain["cells"]:
        slope_score = min(float(cell["slope_mean"]) / 45.0, 1.0)
        aspect_score = float(cell["pct_se_facing"]) / 100.0
        steep_score = float(cell["pct_steep"]) / 100.0
        se_steep_score = float(cell["pct_se_steep"]) / 100.0

        tfi = min(
            slope_score * 0.35
            + aspect_score * 0.15
            + steep_score * 0.25
            + se_steep_score * 0.25,
            1.0,
        )

        if tfi > 0.65:
            regime = "CRITICAL"
        elif tfi > 0.45:
            regime = "HIGH"
        elif tfi > 0.25:
            regime = "ELEVATED"
        else:
            regime = "STABLE"

        baseline_threshold = 25.0
        min_threshold = 9.0
        rain_threshold = baseline_threshold - (baseline_threshold - min_threshold) * tfi

        enriched = cell.copy()
        enriched.update(
            {
                "tfi": round(tfi, 3),
                "regime": regime,
                "rain_threshold_mm_hr": round(rain_threshold, 1),
                "components": {
                    "slope": round(slope_score * 0.35, 3),
                    "aspect": round(aspect_score * 0.15, 3),
                    "steep_pct": round(steep_score * 0.25, 3),
                    "se_steep_pct": round(se_steep_score * 0.25, 3),
                    "road_cut": 0.0,
                    "deforestation": 0.0,
                },
            }
        )
        tfi_cells.append(enriched)

    tfi_cells.sort(key=lambda cell: cell["tfi"], reverse=True)

    regime_summary: dict[str, int] = {}
    for cell in tfi_cells:
        regime_summary[cell["regime"]] = regime_summary.get(cell["regime"], 0) + 1

    print("TFI Summary:")
    for regime in ("CRITICAL", "HIGH", "ELEVATED", "STABLE"):
        n = regime_summary.get(regime, 0)
        pct = 100.0 * n / len(tfi_cells) if tfi_cells else 0.0
        print(f"  {regime:<12}: {n:4d} cells ({pct:.1f}%)")

    print("\nTop 15 highest TFI cells (most fragile terrain):")
    print(f"{'Lat':>8} {'Lon':>9} {'TFI':>6} {'Regime':<12} {'Slope°':>7} {'Rain(mm/hr)':>12}")
    print("-" * 62)
    for cell in tfi_cells[:15]:
        print(
            f"{cell['lat']:>8.3f} {cell['lon']:>9.3f} "
            f"{cell['tfi']:>6.3f} {cell['regime']:<12} "
            f"{cell['slope_mean']:>7.1f} {cell['rain_threshold_mm_hr']:>12.1f}"
        )

    print("\nLowest TFI cells (most stable terrain):")
    for cell in tfi_cells[-5:]:
        print(
            f"  ({cell['lat']:.3f}, {cell['lon']:.3f}): "
            f"TFI={cell['tfi']:.3f} [{cell['regime']}] "
            f"slope={cell['slope_mean']:.0f}°"
        )

    output = {
        "pilot_area": terrain["pilot_area"],
        "n_cells": len(tfi_cells),
        "regime_summary": regime_summary,
        "data_layers_included": ["slope", "aspect", "steep_pct", "se_steep_pct"],
        "data_layers_pending": ["road_cuts", "deforestation_nlcd", "soil_type", "prior_failure"],
        "note": "TFI v0.1 - slope/aspect only. Road cuts will add 0.51 penalty when within 50m.",
        "cells": tfi_cells,
    }
    with TFI_PATH.open("w") as f:
        json.dump(output, f)

    print(f"\nSaved TFI data to {TFI_PATH}")
    print(f"File size: {TFI_PATH.stat().st_size / 1e3:.0f} KB")
    print()
    print("NEXT STEPS:")
    print("  1. Ingest USGS Helene landslide inventory -> validate TFI")
    print("  2. Ingest road network (TIGER) -> add road_cut proximity penalty")
    print("  3. Ingest NLCD land cover -> add deforestation penalty")
    print("  4. Ingest Census + 911 addresses -> add human vulnerability layer")
    print("  5. Connect to GAIA alert pipeline")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
