#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
import math
import random
import sys
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


TFI_PATH = ROOT / "data" / "holler_siren" / "tfi_yancey_mitchell.json"
INVENTORY_PATH = ROOT / "data" / "holler_siren" / "helene_landslides.csv"
REPORT_PATH = ROOT / "data" / "holler_siren" / "tfi_validation_report.json"
BBOX = (35.82, -82.38, 36.12, -81.82)  # min_lat, min_lon, max_lat, max_lon
MATCH_THRESHOLD_DEG = 0.02  # about 2 km
CONTROL_RADIUS_DEG = 0.05  # about 5 km


def load_json(path: Path) -> dict:
    with path.open() as f:
        return json.load(f)


def find_lat_lon_cols(sample: dict) -> tuple[str | None, str | None]:
    lat_col = next((key for key in sample if "lat" in key.lower()), None)
    lon_col = next((key for key in sample if "lon" in key.lower() or "lng" in key.lower() or key.lower() == "x"), None)
    return lat_col, lon_col


def nearest_cell(lat: float, lon: float, cells: list[dict]) -> tuple[dict | None, float]:
    best = None
    best_d = float("inf")
    for cell in cells:
        d = math.sqrt((cell["lat"] - lat) ** 2 + (cell["lon"] - lon) ** 2)
        if d < best_d:
            best = cell
            best_d = d
    return best, best_d


def roc_auc_score_manual(y_true: list[int], scores: list[float]) -> float:
    pos = [(s, y) for s, y in zip(scores, y_true) if y == 1]
    neg = [(s, y) for s, y in zip(scores, y_true) if y == 0]
    if not pos or not neg:
        return float("nan")
    wins = 0.0
    for ps, _ in pos:
        for ns, _ in neg:
            if ps > ns:
                wins += 1.0
            elif ps == ns:
                wins += 0.5
    return wins / (len(pos) * len(neg))


def main() -> int:
    tfi_data = load_json(TFI_PATH)
    tfi_cells = []
    for idx, cell in enumerate(tfi_data["cells"]):
        enriched = dict(cell)
        enriched["cell_id"] = idx
        tfi_cells.append(enriched)

    print(f"TFI cells loaded: {len(tfi_cells)}")
    print(f"Pilot area: {tfi_data['pilot_area']}")
    print()

    if not INVENTORY_PATH.exists():
        raise SystemExit("ERROR: Helene inventory not downloaded. Run download_helene_inventory.py first.")

    with INVENTORY_PATH.open() as f:
        reader = csv.DictReader(f)
        landslides = list(reader)

    print(f"Helene landslides loaded: {len(landslides)}")
    sample = landslides[0] if landslides else {}
    lat_col, lon_col = find_lat_lon_cols(sample)
    print(f"Lat column: {lat_col}, Lon column: {lon_col}")

    pilot_slides: list[dict] = []
    for row in landslides:
        try:
            lat = float(row.get(lat_col or "", ""))
            lon = float(row.get(lon_col or "", ""))
        except (TypeError, ValueError):
            continue
        if BBOX[0] <= lat <= BBOX[2] and BBOX[1] <= lon <= BBOX[3]:
            pilot_slides.append(
                {
                    "lat": lat,
                    "lon": lon,
                    "impact": row.get("impact") or row.get("Impact") or "",
                }
            )

    print(f"Landslides in pilot area (Yancey/Mitchell): {len(pilot_slides)}")
    print()

    if not pilot_slides:
        print("No landslides found in pilot bbox.")
        all_lats = []
        all_lons = []
        for row in landslides[:200]:
            try:
                all_lats.append(float(row.get(lat_col or "", "")))
                all_lons.append(float(row.get(lon_col or "", "")))
            except (TypeError, ValueError):
                pass
        if all_lats:
            print(f"Inventory lat range: {min(all_lats):.3f} to {max(all_lats):.3f}")
            print(f"Inventory lon range: {min(all_lons):.3f} to {max(all_lons):.3f}")
        return 0

    print("Matching landslides to TFI cells...")
    slide_tfis: list[dict] = []
    failed_cell_ids: set[int] = set()
    for slide in pilot_slides:
        cell, dist = nearest_cell(slide["lat"], slide["lon"], tfi_cells)
        if cell and dist < MATCH_THRESHOLD_DEG:
            failed_cell_ids.add(cell["cell_id"])
            slide_tfis.append(
                {
                    "cell_id": cell["cell_id"],
                    "tfi": cell["tfi"],
                    "regime": cell["regime"],
                    "slope": cell["slope_mean"],
                    "impact": slide["impact"],
                    "dist_deg": round(dist, 4),
                }
            )

    print(f"Landslides matched to TFI cells: {len(slide_tfis)}")
    print(f"Unique failed TFI cells: {len(failed_cell_ids)}")
    print()

    random.seed(42)
    control_tfis: list[dict] = []
    failed_slide_points = {(round(slide['lat'], 3), round(slide['lon'], 3)) for slide in pilot_slides}
    for slide in pilot_slides:
        candidates = [
            cell
            for cell in tfi_cells
            if cell["cell_id"] not in failed_cell_ids
            and abs(cell["lat"] - slide["lat"]) < CONTROL_RADIUS_DEG
            and abs(cell["lon"] - slide["lon"]) < CONTROL_RADIUS_DEG
            and (round(cell["lat"], 3), round(cell["lon"], 3)) not in failed_slide_points
        ]
        if candidates:
            ctrl = random.choice(candidates)
            control_tfis.append(
                {
                    "cell_id": ctrl["cell_id"],
                    "tfi": ctrl["tfi"],
                    "regime": ctrl["regime"],
                    "slope": ctrl["slope_mean"],
                }
            )

    print(f"Control cells generated: {len(control_tfis)}")
    print()

    if not slide_tfis or not control_tfis:
        print("Insufficient data for validation statistics")
        return 0

    slide_vals = [row["tfi"] for row in slide_tfis]
    control_vals = [row["tfi"] for row in control_tfis]
    s_mean = float(np.mean(slide_vals))
    c_mean = float(np.mean(control_vals))
    sep = (s_mean - c_mean) / (float(np.std(control_vals)) + 0.001)

    print("=== TFI VALIDATION vs HELENE INVENTORY ===")
    print()
    print(f"Landslide cells:  n={len(slide_vals)}  mean TFI={s_mean:.3f}  std={np.std(slide_vals):.3f}")
    print(f"Control cells:    n={len(control_vals)}  mean TFI={c_mean:.3f}  std={np.std(control_vals):.3f}")
    print(f"Separation:       {sep:+.2f}σ")
    print()

    if sep > 1.0:
        print("RESULT: STRONG - TFI clearly discriminates failed slopes")
    elif sep > 0.5:
        print("RESULT: MODERATE - TFI shows real signal")
    elif sep > 0.2:
        print("RESULT: WEAK but positive - direction correct")
    else:
        print("RESULT: NO SIGNAL - TFI v0.1 (slope/aspect only) insufficient")
        print("ACTION: Add road cut proximity data to rescue signal")

    print()
    print("Regime of FAILED cells:")
    regime_counts: dict[str, int] = {}
    for row in slide_tfis:
        regime_counts[row["regime"]] = regime_counts.get(row["regime"], 0) + 1
    for regime in ("CRITICAL", "HIGH", "ELEVATED", "STABLE"):
        n = regime_counts.get(regime, 0)
        pct = 100.0 * n / max(len(slide_tfis), 1)
        print(f"  {regime:<12}: {n:4d} ({pct:.1f}%)")

    auc = roc_auc_score_manual([1] * len(slide_vals) + [0] * len(control_vals), slide_vals + control_vals)
    print()
    print(f"ROC-AUC (TFI v0.1, slope+aspect only): {auc:.3f}")
    if auc >= 0.80:
        print("  STRONG VALIDATION - ready to add road cut layer")
    elif auc >= 0.65:
        print("  MODERATE - add road cut data to improve")
    else:
        print("  WEAK - road cuts and deforestation layers needed")

    report = {
        "n_inventory_total": len(landslides),
        "n_landslides_pilot": len(pilot_slides),
        "n_matched": len(slide_tfis),
        "n_unique_failed_cells": len(failed_cell_ids),
        "n_controls": len(control_tfis),
        "landslide_mean_tfi": round(s_mean, 4),
        "control_mean_tfi": round(c_mean, 4),
        "separation_sigma": round(sep, 3),
        "auc": round(float(auc), 4),
        "regime_of_failures": regime_counts,
        "note": "TFI v0.1 slope+aspect only. Road cuts pending.",
    }
    with REPORT_PATH.open("w") as f:
        json.dump(report, f, indent=2)
    print()
    print(f"Saved to {REPORT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
