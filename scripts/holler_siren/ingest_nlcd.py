#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
import math
import sys
import urllib.request
from pathlib import Path

import numpy as np
import rasterio
from rasterio.transform import rowcol
from rasterio.warp import transform, transform_bounds
from rasterio.windows import from_bounds


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


OUTPUT_DIR = ROOT / "data" / "holler_siren"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
RUNS_DIR = ROOT / "runs"
RUNS_DIR.mkdir(parents=True, exist_ok=True)
USER_AGENT = "HollerSiren/1.0 (theforgottencode780@gmail.com)"

TFI_V1_PATH = OUTPUT_DIR / "tfi_v1_yancey_mitchell.json"
HELENE_PATH = OUTPUT_DIR / "helene_landslides.csv"
NLCD_2001_PATH = OUTPUT_DIR / "nlcd_2001_yancey_mitchell.tif"
NLCD_2021_PATH = OUTPUT_DIR / "nlcd_2021_yancey_mitchell.tif"
TFI_V2_PATH = OUTPUT_DIR / "tfi_v2_yancey_mitchell.json"
VALIDATION_V2_PATH = OUTPUT_DIR / "tfi_v2_validation_report.json"

BBOX_4326 = (-82.38, 35.82, -81.82, 36.12)  # min_lon, min_lat, max_lon, max_lat
NLCD_INDEX_TO_CLASS = {
    1: 11,
    3: 21,
    4: 22,
    5: 23,
    6: 24,
    7: 31,
    8: 41,
    9: 42,
    10: 43,
    11: 52,
    12: 71,
    13: 81,
    14: 82,
    15: 90,
    16: 95,
}
FOREST_CLASSES = {41, 42, 43}
DISTURBED_CLASSES = {21, 22, 23, 24, 31}
PIXEL_SIZE_M = 30.0
CELL_HALF_SIZE_M = 500.0
BASELINE_AUC_V0 = 0.6537
BASELINE_SEP_V0 = 0.54
BASELINE_AUC_V1 = 0.6049
BASELINE_SEP_V1 = 0.368


def http_get_bytes(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=180) as resp:
        return resp.read()


def bbox_5070() -> tuple[float, float, float, float]:
    return transform_bounds("EPSG:4326", "EPSG:5070", *BBOX_4326, densify_pts=21)


def download_annual_nlcd(year: int, output_path: Path) -> tuple[bool, int]:
    if output_path.exists():
        return True, output_path.stat().st_size

    minx, miny, maxx, maxy = bbox_5070()
    width = int(round((maxx - minx) / PIXEL_SIZE_M))
    height = int(round((maxy - miny) / PIXEL_SIZE_M))
    time_value = f"{year:04d}-01-01T00:00:00.000Z"
    url = (
        "https://dmsdata.cr.usgs.gov/geoserver/mrlc_Land-Cover-Native_conus_year_data/wms"
        f"?service=WMS&version=1.3.0&request=GetMap"
        f"&layers=Land-Cover-Native_conus_year_data"
        f"&styles=&crs=EPSG:5070"
        f"&bbox={minx},{miny},{maxx},{maxy}"
        f"&width={width}&height={height}"
        f"&format=image/geotiff"
        f"&time={time_value}"
    )
    print(f"  Downloading NLCD {year}...")
    data = http_get_bytes(url)
    if len(data) < 1024:
        return False, len(data)
    output_path.write_bytes(data)
    return True, len(data)


def deforestation_penalty(pct_forest_loss: float, slope_deg: float) -> float:
    if slope_deg <= 20.0 or pct_forest_loss < 5.0:
        return 0.0
    if pct_forest_loss < 20.0:
        base = 0.05
    elif pct_forest_loss < 50.0:
        base = 0.12
    else:
        base = 0.20
    slope_factor = min(slope_deg / 35.0, 1.5)
    return round(base * slope_factor, 3)


def remap_nlcd_classes(arr: np.ndarray) -> np.ndarray:
    remapped = np.zeros(arr.shape, dtype=np.uint8)
    for src_val, dst_val in NLCD_INDEX_TO_CLASS.items():
        remapped[arr == src_val] = dst_val
    return remapped


def find_lat_lon_cols(sample: dict) -> tuple[str | None, str | None]:
    lat_col = next((k for k in sample if "lat" in k.lower()), None)
    lon_col = next((k for k in sample if "lon" in k.lower() or "lng" in k.lower() or k.lower() == "x"), None)
    return lat_col, lon_col


def nearest_cell(lat: float, lon: float, cells: list[dict], tfi_key: str) -> tuple[float | None, dict | None, float]:
    best_val = None
    best_cell = None
    best_d = float("inf")
    for cell in cells:
        d = math.sqrt((cell["lat"] - lat) ** 2 + (cell["lon"] - lon) ** 2)
        if d < best_d:
            best_d = d
            best_cell = cell
            best_val = cell[tfi_key]
    return best_val, best_cell, best_d


def roc_auc_score_manual(y_true: list[int], scores: list[float]) -> float:
    pos = [score for score, y in zip(scores, y_true) if y == 1]
    neg = [score for score, y in zip(scores, y_true) if y == 0]
    wins = 0.0
    for ps in pos:
        for ns in neg:
            if ps > ns:
                wins += 1.0
            elif ps == ns:
                wins += 0.5
    return wins / (len(pos) * len(neg))


def compute_cell_forest_loss(forest_loss: np.ndarray, src: rasterio.DatasetReader, lat: float, lon: float) -> tuple[float, int]:
    xs, ys = transform("EPSG:4326", src.crs, [lon], [lat])
    x = xs[0]
    y = ys[0]
    window = from_bounds(
        x - CELL_HALF_SIZE_M,
        y - CELL_HALF_SIZE_M,
        x + CELL_HALF_SIZE_M,
        y + CELL_HALF_SIZE_M,
        transform=src.transform,
    ).round_offsets().round_lengths()
    row_off = max(0, int(window.row_off))
    col_off = max(0, int(window.col_off))
    row_end = min(src.height, row_off + int(window.height))
    col_end = min(src.width, col_off + int(window.width))
    if row_end <= row_off or col_end <= col_off:
        return 0.0, 0
    patch = forest_loss[row_off:row_end, col_off:col_end]
    valid = patch.size
    if valid == 0:
        return 0.0, 0
    return float(np.mean(patch) * 100.0), valid


def main() -> int:
    print("Downloading NLCD land cover rasters...")
    ok_2001, size_2001 = download_annual_nlcd(2001, NLCD_2001_PATH)
    ok_2021, size_2021 = download_annual_nlcd(2021, NLCD_2021_PATH)
    if not (ok_2001 and ok_2021):
        raise RuntimeError("NLCD annual downloads failed")

    with rasterio.open(NLCD_2001_PATH) as src_2001, rasterio.open(NLCD_2021_PATH) as src_2021:
        arr_2001 = remap_nlcd_classes(src_2001.read(1))
        arr_2021 = remap_nlcd_classes(src_2021.read(1))
        forest_2001 = np.isin(arr_2001, list(FOREST_CLASSES))
        disturbed_2021 = np.isin(arr_2021, list(DISTURBED_CLASSES))
        forest_loss = forest_2001 & disturbed_2021
        total_pixels = int(arr_2001.size)
        loss_pixels = int(np.sum(forest_loss))
        pct_loss_area = float(loss_pixels / total_pixels * 100.0)

        print("\nComputing NLCD land cover change...")
        print(f"Total pixels: {total_pixels:,}")
        print(f"Forest loss pixels (2001→2021): {loss_pixels:,} ({pct_loss_area:.2f}%)")

        with TFI_V1_PATH.open() as f:
            tfi_data = json.load(f)
        tfi_cells = tfi_data["cells"]

        updated_v2: list[dict] = []
        deforest_applied = 0
        for cell in tfi_cells:
            pct_forest_loss, covered_pixels = compute_cell_forest_loss(
                forest_loss,
                src_2001,
                cell["lat"],
                cell["lon"],
            )
            penalty = deforestation_penalty(pct_forest_loss, float(cell["slope_mean"]))
            base_tfi = float(cell.get("tfi_v1", cell["tfi"]))
            new_tfi = min(1.0, base_tfi + penalty)

            if new_tfi > 0.65:
                regime = "CRITICAL"
            elif new_tfi > 0.45:
                regime = "HIGH"
            elif new_tfi > 0.25:
                regime = "ELEVATED"
            else:
                regime = "STABLE"

            rain_threshold = 25.0 - (25.0 - 9.0) * new_tfi
            updated = cell.copy()
            updated.update(
                {
                    "tfi_v2": round(new_tfi, 3),
                    "regime_v2": regime,
                    "pct_forest_loss": round(pct_forest_loss, 1),
                    "forest_loss_pixels": int(round(covered_pixels * pct_forest_loss / 100.0)),
                    "nlcd_pixels_sampled": covered_pixels,
                    "deforest_penalty": penalty,
                    "rain_threshold_v2": round(rain_threshold, 1),
                }
            )
            if penalty > 0:
                deforest_applied += 1
            updated_v2.append(updated)

    by_regime: dict[str, int] = {}
    for cell in updated_v2:
        by_regime[cell["regime_v2"]] = by_regime.get(cell["regime_v2"], 0) + 1

    print(f"Cells with deforestation penalty: {deforest_applied}")
    print("\nTFI v2 regime summary:")
    for regime in ["CRITICAL", "HIGH", "ELEVATED", "STABLE"]:
        count = by_regime.get(regime, 0)
        pct = count / len(updated_v2) * 100.0
        print(f"  {regime:<12}: {count:4d} cells ({pct:.1f}%)")

    print("\n=== RE-VALIDATING TFI v2 vs HELENE INVENTORY ===")
    with HELENE_PATH.open() as f:
        landslides = list(csv.DictReader(f))
    lat_col, lon_col = find_lat_lon_cols(landslides[0])
    pilot_slides = []
    for slide in landslides:
        try:
            lat = float(slide.get(lat_col, 0))
            lon = float(slide.get(lon_col, 0))
        except (TypeError, ValueError):
            continue
        if BBOX_4326[1] <= lat <= BBOX_4326[3] and BBOX_4326[0] <= lon <= BBOX_4326[2]:
            pilot_slides.append({"lat": lat, "lon": lon})

    slide_coords = {(round(slide["lat"], 3), round(slide["lon"], 3)) for slide in pilot_slides}
    slide_tfis: list[float] = []
    matched_slide_cells: list[dict] = []
    for slide in pilot_slides:
        score, cell, dist = nearest_cell(slide["lat"], slide["lon"], updated_v2, "tfi_v2")
        if cell is not None and dist < 0.02:
            slide_tfis.append(score)
            matched_slide_cells.append(cell)

    rng = np.random.default_rng(42)
    control_tfis: list[float] = []
    for slide in pilot_slides:
        candidates = [
            cell["tfi_v2"]
            for cell in updated_v2
            if abs(cell["lat"] - slide["lat"]) < 0.05
            and abs(cell["lon"] - slide["lon"]) < 0.05
            and (round(cell["lat"], 3), round(cell["lon"], 3)) not in slide_coords
        ]
        if candidates:
            control_tfis.append(float(rng.choice(candidates)))

    if not slide_tfis or not control_tfis:
        raise RuntimeError("Insufficient matched slides or controls for validation")

    slide_mean = float(np.mean(slide_tfis))
    control_mean = float(np.mean(control_tfis))
    sep_sigma = float((slide_mean - control_mean) / (np.std(control_tfis) + 0.001))
    auc_v2 = float(roc_auc_score_manual([1] * len(slide_tfis) + [0] * len(control_tfis), slide_tfis + control_tfis))

    print(f"Landslide mean TFI v2: {slide_mean:.3f}")
    print(f"Control mean TFI v2:   {control_mean:.3f}")
    print(f"Separation: {sep_sigma:+.2f}σ")
    print(f"AUC v2: {auc_v2:.3f}")
    print(f"  v0.1 (slope+aspect):     {BASELINE_AUC_V0:.3f}")
    print(f"  v1   (+road proximity):  {BASELINE_AUC_V1:.3f}")
    print(f"  v2   (+forest loss):     {auc_v2:.3f}")
    if auc_v2 > BASELINE_AUC_V0:
        print("IMPROVEMENT over baseline")
    elif auc_v2 > BASELINE_AUC_V1:
        print("BETTER than road-only, approaching baseline")
    else:
        print("NO IMPROVEMENT — current forest-loss layer is too blunt")

    top_cells = sorted(updated_v2, key=lambda cell: cell["tfi_v2"], reverse=True)[:10]
    output = tfi_data.copy()
    output["cells"] = updated_v2
    output["data_layers_included"] = [
        "slope",
        "aspect",
        "steep_pct",
        "se_steep_pct",
        "road_cut_proximity",
        "forest_loss_2001_2021",
    ]
    output["data_layers_pending"] = ["soil_type", "prior_failure_helene"]
    output["note"] = "TFI v2 — slope + aspect + road proximity + NLCD forest loss."
    with TFI_V2_PATH.open("w") as f:
        json.dump(output, f)

    report = {
        "nlcd_2001_download_bytes": size_2001,
        "nlcd_2021_download_bytes": size_2021,
        "total_pixels": total_pixels,
        "forest_loss_pixels": loss_pixels,
        "forest_loss_pct_area": round(pct_loss_area, 4),
        "cells_with_deforestation_penalty": deforest_applied,
        "regime_summary_v2": by_regime,
        "n_landslides_pilot": len(pilot_slides),
        "n_matched": len(slide_tfis),
        "n_controls": len(control_tfis),
        "landslide_mean_tfi_v2": round(slide_mean, 4),
        "control_mean_tfi_v2": round(control_mean, 4),
        "separation_sigma_v2": round(sep_sigma, 3),
        "auc_v2": round(auc_v2, 4),
        "comparison": {
            "v0_1_auc": BASELINE_AUC_V0,
            "v0_1_sep_sigma": BASELINE_SEP_V0,
            "v1_auc": BASELINE_AUC_V1,
            "v1_sep_sigma": BASELINE_SEP_V1,
            "v2_auc": round(auc_v2, 4),
            "v2_sep_sigma": round(sep_sigma, 3),
        },
        "top_cells_v2": [
            {
                "lat": cell["lat"],
                "lon": cell["lon"],
                "tfi_v2": cell["tfi_v2"],
                "pct_forest_loss": cell["pct_forest_loss"],
                "deforest_penalty": cell["deforest_penalty"],
                "road_dist_km": cell.get("road_dist_km"),
                "slope_mean": cell["slope_mean"],
            }
            for cell in top_cells
        ],
        "note": "TFI v2 adds NLCD 2001→2021 forest loss on steep terrain.",
    }
    with VALIDATION_V2_PATH.open("w") as f:
        json.dump(report, f, indent=2)

    print(f"\nSaved TFI v2 to {TFI_V2_PATH}")
    print(f"Saved validation report to {VALIDATION_V2_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
