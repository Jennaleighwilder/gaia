#!/usr/bin/env python3
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np
import rasterio
import rasterio.merge
from rasterio.windows import from_bounds
from scipy.ndimage import uniform_filter


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


DATA_DIR = ROOT / "data" / "holler_siren"
RAW_DEM_DIR = DATA_DIR / "raw_dem"
MERGED_DEM_PATH = DATA_DIR / "dem_yancey_mitchell.tif"
INPUT_TFI_PATH = DATA_DIR / "tfi_calibrated_yancey_mitchell.json"
OUTPUT_TFI_PATH = DATA_DIR / "tfi_twi_yancey_mitchell.json"

BBOX = (-82.38, 35.82, -81.82, 36.12)  # min_lon, min_lat, max_lon, max_lat
BBOX_BUFFER_DEG = 0.03
MIN_SLOPE_RAD = 0.001
KERNEL_SIZE = 5


def _load_dem() -> tuple[np.ndarray, rasterio.Affine, float | None]:
    tif_files = sorted(RAW_DEM_DIR.glob("*.tif")) if RAW_DEM_DIR.exists() else []
    if MERGED_DEM_PATH.exists():
        tif_files = [MERGED_DEM_PATH]
    if not tif_files:
        raise FileNotFoundError("No DEM found. Run ingest_terrain.py first.")

    min_lon, min_lat, max_lon, max_lat = BBOX
    bounds = (
        min_lon - BBOX_BUFFER_DEG,
        min_lat - BBOX_BUFFER_DEG,
        max_lon + BBOX_BUFFER_DEG,
        max_lat + BBOX_BUFFER_DEG,
    )

    if len(tif_files) == 1:
        with rasterio.open(tif_files[0]) as src:
            window = from_bounds(*bounds, transform=src.transform).round_offsets().round_lengths()
            window = window.intersection(((0, src.height), (0, src.width)))
            dem = src.read(1, window=window).astype(np.float32)
            transform = src.window_transform(window)
            nodata = src.nodata
    else:
        datasets = [rasterio.open(path) for path in tif_files]
        try:
            dem, transform = rasterio.merge.merge(datasets, bounds=bounds)
            dem = dem[0].astype(np.float32)
            nodata = datasets[0].nodata
        finally:
            for dataset in datasets:
                dataset.close()

    if nodata is not None:
        dem[dem == nodata] = np.nan
    return dem, transform, nodata


def _compute_twi(dem: np.ndarray, transform: rasterio.Affine) -> np.ndarray:
    lat_mid = (BBOX[1] + BBOX[3]) / 2.0
    px_ns = abs(transform.e) * 111320.0
    px_ew = abs(transform.a) * 111320.0 * math.cos(math.radians(lat_mid))

    dem_filled = np.where(np.isnan(dem), np.nanmean(dem), dem).astype(np.float32)
    dy, dx = np.gradient(dem_filled, px_ns, px_ew)
    slope_rad = np.arctan(np.sqrt(dx**2 + dy**2)).astype(np.float32)
    slope_rad = np.maximum(slope_rad, MIN_SLOPE_RAD)

    dem_smooth = uniform_filter(dem_filled, size=KERNEL_SIZE, mode="nearest")
    lap = (
        np.roll(dem_smooth, -1, axis=0)
        + np.roll(dem_smooth, 1, axis=0)
        + np.roll(dem_smooth, -1, axis=1)
        + np.roll(dem_smooth, 1, axis=1)
        - 4.0 * dem_smooth
    ) / (px_ns * px_ew)

    convergence = -lap
    conv_min = float(np.nanmin(convergence))
    conv_max = float(np.nanmax(convergence))
    conv_norm = (convergence - conv_min) / (conv_max - conv_min + 1e-10)
    upslope_proxy = 1.0 + conv_norm * 100.0

    twi = np.log(upslope_proxy / np.tan(slope_rad)).astype(np.float32)
    twi[np.isnan(dem)] = np.nan
    return twi


def _window_for_cell(
    lat: float,
    lon: float,
    transform: rasterio.Affine,
    shape: tuple[int, int],
    pix_per_km_ns: int,
    pix_per_km_ew: int,
) -> tuple[int, int, int, int]:
    row, col = rasterio.transform.rowcol(transform, lon, lat)
    rows, cols = shape
    half_r = max(1, pix_per_km_ns // 2)
    half_c = max(1, pix_per_km_ew // 2)
    r0 = max(0, row - half_r)
    r1 = min(rows, row + half_r + 1)
    c0 = max(0, col - half_c)
    c1 = min(cols, col + half_c + 1)
    return r0, r1, c0, c1


def main() -> int:
    print("=== TOPOGRAPHIC WETNESS INDEX ===")
    dem, transform, _ = _load_dem()
    print(f"DEM shape: {dem.shape}")
    print(f"Resolution: {transform.a:.8f} deg")

    lat_mid = (BBOX[1] + BBOX[3]) / 2.0
    px_ns = abs(transform.e) * 111320.0
    px_ew = abs(transform.a) * 111320.0 * math.cos(math.radians(lat_mid))
    print(f"Pixel size: ~{px_ew:.0f}m x {px_ns:.0f}m")

    twi = _compute_twi(dem, transform)
    print(f"TWI range: {np.nanmin(twi):.2f} to {np.nanmax(twi):.2f}")
    print(f"TWI mean: {np.nanmean(twi):.2f}")

    with INPUT_TFI_PATH.open() as f:
        tfi_data = json.load(f)
    cells = tfi_data["cells"]

    print("\nAssigning TWI to terrain cells...")
    pix_per_km_ns = max(1, int(round(1000.0 / px_ns)))
    pix_per_km_ew = max(1, int(round(1000.0 / px_ew)))

    updated: list[dict] = []
    for cell in cells:
        r0, r1, c0, c1 = _window_for_cell(
            lat=float(cell["lat"]),
            lon=float(cell["lon"]),
            transform=transform,
            shape=twi.shape,
            pix_per_km_ns=pix_per_km_ns,
            pix_per_km_ew=pix_per_km_ew,
        )
        cell_twi = twi[r0:r1, c0:c1]
        valid = cell_twi[~np.isnan(cell_twi)]
        if valid.size:
            twi_mean = float(np.mean(valid))
            twi_max = float(np.max(valid))
            twi_p90 = float(np.percentile(valid, 90))
        else:
            twi_mean = twi_max = twi_p90 = 0.0

        updated_cell = cell.copy()
        updated_cell["twi_mean"] = round(twi_mean, 3)
        updated_cell["twi_max"] = round(twi_max, 3)
        updated_cell["twi_p90"] = round(twi_p90, 3)
        updated.append(updated_cell)

    twi_vals = [cell["twi_mean"] for cell in updated]
    ranked = sorted(updated, key=lambda cell: cell["twi_mean"], reverse=True)
    print(f"TWI assigned to {len(updated)} cells")
    print(f"Cell TWI range: {min(twi_vals):.2f} to {max(twi_vals):.2f}")
    print("\nTop 10 high-TWI cells:")
    for cell in ranked[:10]:
        print(
            f"  ({cell['lat']:.4f}, {cell['lon']:.4f}): "
            f"twi_mean={cell['twi_mean']:.2f} twi_p90={cell['twi_p90']:.2f} "
            f"slope={cell['slope_mean']:.1f}"
        )

    tfi_data["cells"] = updated
    layers = list(tfi_data.get("data_layers_included", []))
    if "twi" not in layers:
        layers.append("twi")
    tfi_data["data_layers_included"] = layers
    with OUTPUT_TFI_PATH.open("w") as f:
        json.dump(tfi_data, f)
    print(f"\nSaved to {OUTPUT_TFI_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
