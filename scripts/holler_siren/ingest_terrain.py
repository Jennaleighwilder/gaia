#!/usr/bin/env python3
from __future__ import annotations

import json
import math
import re
import sys
import urllib.parse
import urllib.request
from collections import defaultdict
from pathlib import Path

import numpy as np
import rasterio
from rasterio.merge import merge

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

TNM_URL = "https://tnmaccess.nationalmap.gov/api/v1/products"
BBOX_STR = "-82.38,35.82,-81.82,36.12"
BBOX = (-82.38, 35.82, -81.82, 36.12)  # west, south, east, north
DATASET = "National Elevation Dataset (NED) 1/3 arc-second"
OUT_DIR = ROOT / "data" / "holler_siren"
RAW_DIR = OUT_DIR / "raw_dem"
DEM_SUMMARY_PATH = OUT_DIR / "terrain_yancey_mitchell.json"
USER_AGENT = "HollerSiren/1.0 (research@theforgottencode.com)"


def fetch_json(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode())


def query_tnm_products() -> list[dict]:
    params = {
        "datasets": DATASET,
        "bbox": BBOX_STR,
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
    for item in selected:
        title = item.get("title", "no title")
        size_mb = float(item.get("sizeInBytes", 0)) / 1e6
        urls = item.get("urls", {})
        download_url = urls.get("TIFF") or urls.get("GeoTIFF") or next(iter(urls.values()), None)
        print(f"  {title}")
        print(f"    Size: {size_mb:.1f} MB")
        print(f"    URL: {str(download_url)[:80]}...")
    return selected


def download_tiles(items: list[dict]) -> list[Path]:
    paths: list[Path] = []
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    for item in items:
        urls = item.get("urls", {})
        download_url = urls.get("TIFF") or urls.get("GeoTIFF") or next(iter(urls.values()), None)
        if not download_url:
            continue
        name = Path(urllib.parse.urlparse(str(download_url)).path).name or f"{item.get('title', 'dem').replace(' ', '_')}.tif"
        out_path = RAW_DIR / name
        if out_path.exists() and out_path.stat().st_size > 0:
            print(f"DEM already cached at {out_path}")
            paths.append(out_path)
            continue
        size_mb = float(item.get("sizeInBytes", 0)) / 1e6
        print(f"\nDownloading {item.get('title', 'DEM')} ({size_mb:.1f} MB)...")
        print(f"Downloading from: {str(download_url)[:100]}...")
        req = urllib.request.Request(str(download_url), headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=300) as resp, out_path.open("wb") as f:
            f.write(resp.read())
        print(f"Downloaded {out_path.stat().st_size / 1e6:.1f} MB to {out_path}")
        paths.append(out_path)
    return paths


def build_clipped_dem(tile_paths: list[Path]) -> tuple[np.ndarray, rasterio.Affine]:
    sources = [rasterio.open(path) for path in tile_paths]
    try:
        mosaic, transform = merge(sources, bounds=BBOX, nodata=np.nan, dtype="float32")
        dem = mosaic[0].astype("float64")
        return dem, transform
    finally:
        for src in sources:
            src.close()


def compute_terrain_cells(dem: np.ndarray, transform) -> list[dict]:
    west, south, east, north = BBOX
    lat_mid = (north + south) / 2
    px_ns = abs(transform.e) * 111320.0
    px_ew = abs(transform.a) * 111320.0 * math.cos(math.radians(lat_mid))

    dy, dx = np.gradient(dem, px_ns, px_ew)
    slope_rad = np.arctan(np.sqrt(dx**2 + dy**2))
    slope_deg = np.degrees(slope_rad)
    aspect_rad = np.arctan2(-dx, dy)
    aspect_deg = np.degrees(aspect_rad) % 360.0
    se_facing = ((aspect_deg >= 90.0) & (aspect_deg <= 200.0)).astype(float)

    print("\nTerrain statistics:")
    print(f"  Mean slope: {np.nanmean(slope_deg):.1f}°")
    print(f"  Max slope: {np.nanmax(slope_deg):.1f}°")
    print(f"  % slope > 30°: {100 * np.nanmean(slope_deg > 30):.1f}%")
    print(f"  % slope > 40°: {100 * np.nanmean(slope_deg > 40):.1f}%")
    print(f"  % SE-facing: {100 * np.nanmean(se_facing):.1f}%")
    print(f"  % SE-facing AND slope>30°: {100 * np.nanmean((se_facing == 1) & (slope_deg > 30)):.1f}%")

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
            grid_cells.append(cell)

    grid_cells.sort(key=lambda cell: cell["slope_risk"] + cell["aspect_risk"], reverse=True)
    print(f"  Grid cells computed: {len(grid_cells)}")
    print("\nTop 10 highest terrain risk cells:")
    for cell in grid_cells[:10]:
        print(
            f"  ({cell['lat']:.3f}, {cell['lon']:.3f}): "
            f"slope={cell['slope_mean']:.0f}° "
            f"steep%={cell['pct_steep']:.0f}% "
            f"SE%={cell['pct_se_facing']:.0f}%"
        )
    return grid_cells


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    items = query_tnm_products()
    selected = select_latest_tiles(items)
    tile_paths = download_tiles(selected)

    print("\nComputing terrain derivatives from downloaded DEM tiles...")
    dem, transform = build_clipped_dem(tile_paths)
    print(f"  Shape: {dem.shape}")
    print(f"  Resolution: {abs(transform.a):.6f} deg (~{abs(transform.a) * 111000:.0f}m)")
    print(f"  Elevation range: {np.nanmin(dem):.0f}m to {np.nanmax(dem):.0f}m")

    grid_cells = compute_terrain_cells(dem, transform)
    output = {
        "pilot_area": "Yancey + Mitchell Counties, NC",
        "bbox": BBOX_STR,
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
        "cells": grid_cells,
    }
    with DEM_SUMMARY_PATH.open("w") as f:
        json.dump(output, f)
    print(f"\nSaved {len(grid_cells)} terrain cells to {DEM_SUMMARY_PATH}")
    print(f"File size: {DEM_SUMMARY_PATH.stat().st_size / 1e3:.0f} KB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
