#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path

import numpy as np
import rasterio
from rasterio.merge import merge
from scipy.ndimage import uniform_filter

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

TNM_URL = "https://tnmaccess.nationalmap.gov/api/v1/products"
DEFAULT_BBOX = (-82.38, 35.82, -81.82, 36.12)  # west, south, east, north
DEFAULT_BBOX_STR = "-82.38,35.82,-81.82,36.12"
DEFAULT_OUTPUT = ROOT / "data" / "holler_siren" / "terrain_yancey_mitchell.json"
DEFAULT_RAW_DIR = ROOT / "data" / "holler_siren" / "raw_dem"
DEFAULT_AREA_NAME = "Yancey + Mitchell Counties, NC"
DATASET = "National Elevation Dataset (NED) 1/3 arc-second"
USER_AGENT = "HollerSiren/1.0 (research@theforgottencode.com)"
MIN_SLOPE_RAD = 0.001


def _slugify_region(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
    return slug or "custom_region"


def _pretty_region_name(region: str) -> str:
    parts = [part for part in region.replace("-", "_").split("_") if part]
    if not parts:
        return "Custom Region"
    return " ".join(part.capitalize() for part in parts)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ingest TNM DEM and compute 1km terrain cells.")
    parser.add_argument(
        "--region",
        default="yancey_mitchell",
        help="Region slug used for default output/cache paths",
    )
    parser.add_argument(
        "--bbox",
        default="35.82,-82.38,36.12,-81.82",
        help="Bounding box as south,west,north,east",
    )
    parser.add_argument(
        "--output",
        default=str(DEFAULT_OUTPUT),
        help="Output JSON path",
    )
    parser.add_argument(
        "--raw-dir",
        default=str(DEFAULT_RAW_DIR),
        help="Directory for raw DEM tiles",
    )
    parser.add_argument(
        "--area-name",
        default=DEFAULT_AREA_NAME,
        help="Human-readable area name",
    )
    parser.add_argument(
        "--coarse-res-m",
        type=float,
        default=0.0,
        help="Optional merge resolution in meters to keep large regions tractable",
    )
    parser.add_argument(
        "--include-twi",
        action="store_true",
        help="Compute TWI-style convergence metrics for each 1km cell",
    )
    args = parser.parse_args()
    args.region = _slugify_region(args.region)
    if args.output == str(DEFAULT_OUTPUT):
        args.output = str(ROOT / "data" / "holler_siren" / f"terrain_{args.region}.json")
    if args.raw_dir == str(DEFAULT_RAW_DIR):
        args.raw_dir = str(ROOT / "data" / "holler_siren" / f"raw_dem_{args.region}")
    if args.area_name == DEFAULT_AREA_NAME and args.region != "yancey_mitchell":
        args.area_name = _pretty_region_name(args.region)
    return args


def bbox_from_user_arg(bbox_arg: str) -> tuple[tuple[float, float, float, float], str]:
    south, west, north, east = [float(part) for part in bbox_arg.split(",")]
    bbox = (west, south, east, north)
    bbox_str = f"{west},{south},{east},{north}"
    return bbox, bbox_str


def fetch_json(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode())


def query_tnm_products(bbox_str: str) -> list[dict]:
    params = {
        "datasets": DATASET,
        "bbox": bbox_str,
        "prodFormats": "GeoTIFF",
        "max": "50",
    }
    url = f"{TNM_URL}?{urllib.parse.urlencode(params)}"
    print("Querying TNM API...")
    print(f"URL: {url[:120]}...")
    data = fetch_json(url)
    items = data.get("items", [])
    print(f"Found {len(items)} elevation products")
    if items:
        return items

    print("No products found. Trying broader search...")
    params["prodFormats"] = "IMG,GeoTIFF"
    url = f"{TNM_URL}?{urllib.parse.urlencode(params)}"
    data = fetch_json(url)
    items = data.get("items", [])
    print(f"Found {len(items)} products")
    return items


def select_latest_tiles(items: list[dict]) -> list[dict]:
    by_tile: dict[str, dict] = {}
    for item in items:
        title = item.get("title", "")
        if "1/3 Arc Second" not in title:
            continue
        match = re.search(r"(n\d{2}w\d{3})", title.lower())
        if not match:
            continue
        tile = match.group(1)
        current = by_tile.get(tile)
        if current is None or (item.get("publicationDate") or "") > (current.get("publicationDate") or ""):
            by_tile[tile] = item
    selected = [by_tile[key] for key in sorted(by_tile)]
    print(f"Selected {len(selected)} latest 1/3 arc-second tiles")
    for item in selected[:12]:
        title = item.get("title", "no title")
        size_mb = float(item.get("sizeInBytes", 0)) / 1e6
        urls = item.get("urls", {})
        download_url = urls.get("TIFF") or urls.get("GeoTIFF") or next(iter(urls.values()), None)
        print(f"  {title}")
        print(f"    Size: {size_mb:.1f} MB")
        print(f"    URL: {str(download_url)[:80]}...")
    return selected


def download_tiles(items: list[dict], raw_dir: Path) -> list[Path]:
    paths: list[Path] = []
    raw_dir.mkdir(parents=True, exist_ok=True)
    for item in items:
        urls = item.get("urls", {})
        download_url = urls.get("TIFF") or urls.get("GeoTIFF") or next(iter(urls.values()), None)
        if not download_url:
            continue
        name = Path(urllib.parse.urlparse(str(download_url)).path).name or f"{item.get('title', 'dem').replace(' ', '_')}.tif"
        out_path = raw_dir / name
        if out_path.exists() and out_path.stat().st_size > 0:
            print(f"DEM already cached at {out_path}")
            paths.append(out_path)
            continue
        size_mb = float(item.get("sizeInBytes", 0)) / 1e6
        print(f"\nDownloading {item.get('title', 'DEM')} ({size_mb:.1f} MB)...")
        req = urllib.request.Request(str(download_url), headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=300) as resp, out_path.open("wb") as f:
            f.write(resp.read())
        print(f"Downloaded {out_path.stat().st_size / 1e6:.1f} MB to {out_path}")
        paths.append(out_path)
    return paths


def build_clipped_dem(
    tile_paths: list[Path],
    bbox: tuple[float, float, float, float],
    coarse_res_m: float = 0.0,
) -> tuple[np.ndarray, rasterio.Affine]:
    sources = [rasterio.open(path) for path in tile_paths]
    try:
        res = None
        if coarse_res_m and coarse_res_m > 0:
            lat_mid = (bbox[1] + bbox[3]) / 2.0
            x_res = coarse_res_m / (111320.0 * math.cos(math.radians(lat_mid)))
            y_res = coarse_res_m / 111320.0
            res = (x_res, y_res)
        mosaic, transform = merge(sources, bounds=bbox, nodata=np.nan, dtype="float32", res=res)
        dem = mosaic[0].astype("float32")
        return dem, transform
    finally:
        for src in sources:
            src.close()


def compute_twi(dem: np.ndarray, px_ns: float, px_ew: float) -> np.ndarray:
    dem_filled = np.where(np.isnan(dem), np.nanmean(dem), dem).astype(np.float32)
    dy, dx = np.gradient(dem_filled, px_ns, px_ew)
    slope_rad = np.arctan(np.sqrt(dx**2 + dy**2)).astype(np.float32)
    slope_rad = np.maximum(slope_rad, MIN_SLOPE_RAD)

    dem_smooth = uniform_filter(dem_filled, size=5, mode="nearest")
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


def compute_terrain_cells(
    dem: np.ndarray,
    transform,
    bbox: tuple[float, float, float, float],
    include_twi: bool,
) -> tuple[list[dict], dict]:
    west, south, east, north = bbox
    lat_mid = (north + south) / 2
    px_ns = abs(transform.e) * 111320.0
    px_ew = abs(transform.a) * 111320.0 * math.cos(math.radians(lat_mid))

    dy, dx = np.gradient(dem, px_ns, px_ew)
    slope_rad = np.arctan(np.sqrt(dx**2 + dy**2))
    slope_deg = np.degrees(slope_rad)
    aspect_rad = np.arctan2(-dx, dy)
    aspect_deg = np.degrees(aspect_rad) % 360.0
    se_facing = ((aspect_deg >= 90.0) & (aspect_deg <= 200.0)).astype(float)
    twi = compute_twi(dem, px_ns, px_ew) if include_twi else None

    print("\nTerrain statistics:")
    print(f"  Mean slope: {np.nanmean(slope_deg):.1f}°")
    print(f"  Max slope: {np.nanmax(slope_deg):.1f}°")
    print(f"  % slope > 30°: {100 * np.nanmean(slope_deg > 30):.1f}%")
    print(f"  % slope > 40°: {100 * np.nanmean(slope_deg > 40):.1f}%")
    print(f"  % SE-facing: {100 * np.nanmean(se_facing):.1f}%")
    print(f"  % SE-facing AND slope>30°: {100 * np.nanmean((se_facing == 1) & (slope_deg > 30)):.1f}%")
    if twi is not None:
        print(f"  TWI mean: {np.nanmean(twi):.2f}")
        print(f"  TWI max: {np.nanmax(twi):.2f}")

    print("\nAggregating to 1km grid...")
    pix_per_km_ns = max(1, int(round(1000.0 / px_ns)))
    pix_per_km_ew = max(1, int(round(1000.0 / px_ew)))
    print(f"  Pixels per km: {pix_per_km_ns}x{pix_per_km_ew}")

    rows, cols = dem.shape
    grid_cells: list[dict] = []
    for r in range(0, rows, pix_per_km_ns):
        for c in range(0, cols, pix_per_km_ew):
            elev = dem[r : r + pix_per_km_ns, c : c + pix_per_km_ew]
            slope = slope_deg[r : r + pix_per_km_ns, c : c + pix_per_km_ew]
            se = se_facing[r : r + pix_per_km_ns, c : c + pix_per_km_ew]
            valid = np.isfinite(elev)
            if int(np.sum(valid)) < 10:
                continue
            lon = transform.c + (c + (elev.shape[1] / 2.0)) * transform.a
            lat = transform.f + (r + (elev.shape[0] / 2.0)) * transform.e
            cell = {
                "lat": round(float(lat), 4),
                "lon": round(float(lon), 4),
                "elev_m": round(float(np.nanmean(elev)), 0),
                "slope_mean": round(float(np.nanmean(slope)), 1),
                "slope_max": round(float(np.nanmax(slope)), 1),
                "pct_steep": round(float(np.nanmean(slope > 30.0) * 100.0), 1),
                "pct_very_steep": round(float(np.nanmean(slope > 40.0) * 100.0), 1),
                "pct_se_facing": round(float(np.nanmean(se) * 100.0), 1),
                "pct_se_steep": round(float(np.nanmean((se == 1) & (slope > 30.0)) * 100.0), 1),
                "aspect_risk": round(float(np.nanmean(se) * 0.12), 3),
                "slope_risk": round(float(min(np.nanmean(slope) / 45.0, 1.0) * 0.30), 3),
            }
            if twi is not None:
                twi_window = twi[r : r + pix_per_km_ns, c : c + pix_per_km_ew]
                twi_valid = twi_window[np.isfinite(twi_window)]
                if twi_valid.size:
                    cell["twi_mean"] = round(float(np.mean(twi_valid)), 3)
                    cell["twi_p90"] = round(float(np.percentile(twi_valid, 90)), 3)
                    cell["twi_max"] = round(float(np.max(twi_valid)), 3)
                else:
                    cell["twi_mean"] = 0.0
                    cell["twi_p90"] = 0.0
                    cell["twi_max"] = 0.0
            grid_cells.append(cell)

    grid_cells.sort(key=lambda cell: cell["slope_risk"] + cell["aspect_risk"], reverse=True)
    print(f"  Grid cells computed: {len(grid_cells)}")
    print("\nTop 10 highest terrain risk cells:")
    for cell in grid_cells[:10]:
        extra = f" twi={cell.get('twi_mean', 0):.2f}" if include_twi else ""
        print(
            f"  ({cell['lat']:.3f}, {cell['lon']:.3f}): "
            f"slope={cell['slope_mean']:.0f}° steep%={cell['pct_steep']:.0f}% "
            f"SE%={cell['pct_se_facing']:.0f}%{extra}"
        )
    stats = {
        "mean_slope_deg": round(float(np.nanmean(slope_deg)), 3),
        "pct_steep_gt30": round(float(100 * np.nanmean(slope_deg > 30.0)), 3),
        "pct_se_facing": round(float(100 * np.nanmean(se_facing)), 3),
    }
    if twi is not None:
        stats["twi_mean"] = round(float(np.nanmean(twi)), 3)
        stats["twi_max"] = round(float(np.nanmax(twi)), 3)
    return grid_cells, stats


def main() -> int:
    args = parse_args()
    bbox, bbox_str = bbox_from_user_arg(args.bbox)
    output_path = Path(args.output)
    raw_dir = Path(args.raw_dir)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    items = query_tnm_products(bbox_str)
    selected = select_latest_tiles(items)
    tile_paths = download_tiles(selected, raw_dir)

    print("\nComputing terrain derivatives from downloaded DEM tiles...")
    dem, transform = build_clipped_dem(tile_paths, bbox, coarse_res_m=args.coarse_res_m)
    approx_res_m = abs(transform.a) * 111000.0
    print(f"  Shape: {dem.shape}")
    print(f"  Resolution: {abs(transform.a):.6f} deg (~{approx_res_m:.0f}m)")
    print(f"  Elevation range: {np.nanmin(dem):.0f}m to {np.nanmax(dem):.0f}m")

    grid_cells, stats = compute_terrain_cells(dem, transform, bbox, include_twi=args.include_twi)
    output = {
        "region": args.region,
        "pilot_area": args.area_name,
        "bbox": bbox_str,
        "n_cells": len(grid_cells),
        "cell_size_km": 1.0,
        "helene_context": "USGS mapped 2217 landslides here after Hurricane Helene 2024",
        "data_source": "USGS 3DEP 1/3 arc-second DEM",
        "tnm_products_found": len(items),
        "selected_tiles": [
            {
                "title": item.get("title"),
                "publication_date": item.get("publicationDate"),
                "size_mb": round(float(item.get("sizeInBytes", 0)) / 1e6, 1),
            }
            for item in selected
        ],
        "coarse_res_m": args.coarse_res_m if args.coarse_res_m > 0 else None,
        "terrain_stats": stats,
        "cells": grid_cells,
    }
    with output_path.open("w") as f:
        json.dump(output, f)
    print(f"\nSaved {len(grid_cells)} terrain cells to {output_path}")
    print(f"File size: {output_path.stat().st_size / 1e3:.0f} KB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
