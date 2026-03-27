#!/usr/bin/env python3
from __future__ import annotations

import csv
import io
import json
import math
import struct
import sys
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


OUTPUT_DIR = ROOT / "data" / "holler_siren"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
RUNS_DIR = ROOT / "runs"
RUNS_DIR.mkdir(parents=True, exist_ok=True)
TIGER_URLS = {
    "yancey": "https://www2.census.gov/geo/tiger/TIGER2023/ROADS/tl_2023_37199_roads.zip",
    "mitchell": "https://www2.census.gov/geo/tiger/TIGER2023/ROADS/tl_2023_37121_roads.zip",
}
TFI_PATH = OUTPUT_DIR / "tfi_yancey_mitchell.json"
HELENE_PATH = OUTPUT_DIR / "helene_landslides.csv"
TFI_V1_PATH = OUTPUT_DIR / "tfi_v1_yancey_mitchell.json"
VALIDATION_V1_PATH = OUTPUT_DIR / "tfi_v1_validation_report.json"
USER_AGENT = "HollerSiren/1.0 (theforgottencode780@gmail.com)"
BBOX = (35.82, -82.38, 36.12, -81.82)  # min_lat, min_lon, max_lat, max_lon
BIN_SIZE_DEG = 0.02


def http_get_bytes(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=120) as resp:
        return resp.read()


def parse_polyline_segments(shp_bytes: bytes) -> list[list[float]]:
    segs: list[list[float]] = []
    pos = 100
    while pos + 8 <= len(shp_bytes):
        _rec_num = struct.unpack_from(">i", shp_bytes, pos)[0]
        content_len = struct.unpack_from(">i", shp_bytes, pos + 4)[0] * 2
        pos += 8
        if pos + content_len > len(shp_bytes):
            break

        shape_type = struct.unpack_from("<i", shp_bytes, pos)[0]
        if shape_type == 3:  # Polyline
            num_parts = struct.unpack_from("<i", shp_bytes, pos + 36)[0]
            num_points = struct.unpack_from("<i", shp_bytes, pos + 40)[0]
            parts_offset = pos + 44
            points_offset = parts_offset + num_parts * 4

            parts = [struct.unpack_from("<i", shp_bytes, parts_offset + i * 4)[0] for i in range(num_parts)]
            parts.append(num_points)
            points: list[tuple[float, float]] = []
            for idx in range(num_points):
                x = struct.unpack_from("<d", shp_bytes, points_offset + idx * 16)[0]
                y = struct.unpack_from("<d", shp_bytes, points_offset + idx * 16 + 8)[0]
                points.append((y, x))  # lat, lon

            for pidx in range(len(parts) - 1):
                start = parts[pidx]
                end = parts[pidx + 1]
                for i in range(start, max(start, end - 1)):
                    lat1, lon1 = points[i]
                    lat2, lon2 = points[i + 1]
                    segs.append([lat1, lon1, lat2, lon2])

        pos += content_len
    return segs


def thin_segments(segs: list[list[float]], max_segments: int = 15000) -> list[list[float]]:
    if len(segs) <= max_segments:
        return segs
    step = max(1, math.ceil(len(segs) / max_segments))
    return segs[::step]


def load_or_download_roads() -> list[list[float]]:
    road_segments: list[list[float]] = []
    for county, url in TIGER_URLS.items():
        road_cache = OUTPUT_DIR / f"roads_{county}.json"
        if road_cache.exists():
            print(f"Loading cached {county} roads...")
            with road_cache.open() as f:
                segs = json.load(f)
            road_segments.extend(segs)
            print(f"  {len(segs)} segments loaded")
            continue

        print(f"Downloading {county} roads from TIGER...")
        try:
            zip_bytes = http_get_bytes(url)
            print(f"  Downloaded {len(zip_bytes) / 1e6:.1f} MB")
        except Exception as exc:
            print(f"  Download failed: {exc}")
            continue

        try:
            archive = zipfile.ZipFile(io.BytesIO(zip_bytes))
            shp_name = next(name for name in archive.namelist() if name.endswith(".shp"))
            segs = parse_polyline_segments(archive.read(shp_name))
            print(f"  Parsed {len(segs)} road segments")
            segs = thin_segments(segs)
            print(f"  Thinned to {len(segs)} segments")
            with road_cache.open("w") as f:
                json.dump(segs, f)
            road_segments.extend(segs)
        except Exception as exc:
            print(f"  Shapefile parse failed: {exc}")

    print(f"\nTotal road segments: {len(road_segments)}")
    return road_segments


def point_to_segment_km(lat: float, lon: float, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    scale_lat = 111_320.0
    scale_lon = 111_320.0 * math.cos(math.radians((lat1 + lat2) / 2.0))

    px = (lon - lon1) * scale_lon
    py = (lat - lat1) * scale_lat
    dx = (lon2 - lon1) * scale_lon
    dy = (lat2 - lat1) * scale_lat

    seg_len_sq = dx * dx + dy * dy
    if seg_len_sq < 1.0:
        return math.sqrt(px * px + py * py) / 1000.0

    t = max(0.0, min(1.0, (px * dx + py * dy) / seg_len_sq))
    nx = px - t * dx
    ny = py - t * dy
    return math.sqrt(nx * nx + ny * ny) / 1000.0


def road_cut_penalty(dist_km: float) -> float:
    if dist_km < 0.05:
        return 0.51
    if dist_km < 0.10:
        return 0.25
    if dist_km < 0.20:
        return 0.10
    return 0.0


def bin_key(lat: float, lon: float) -> tuple[int, int]:
    return (int(math.floor(lat / BIN_SIZE_DEG)), int(math.floor(lon / BIN_SIZE_DEG)))


def build_segment_index(segments: list[list[float]]) -> dict[tuple[int, int], list[list[float]]]:
    seg_index: dict[tuple[int, int], list[list[float]]] = {}
    for seg in segments:
        lat1, lon1, lat2, lon2 = seg
        min_lat, max_lat = sorted((lat1, lat2))
        min_lon, max_lon = sorted((lon1, lon2))
        lat_start = int(math.floor(min_lat / BIN_SIZE_DEG))
        lat_end = int(math.floor(max_lat / BIN_SIZE_DEG))
        lon_start = int(math.floor(min_lon / BIN_SIZE_DEG))
        lon_end = int(math.floor(max_lon / BIN_SIZE_DEG))
        for lat_bin in range(lat_start, lat_end + 1):
            for lon_bin in range(lon_start, lon_end + 1):
                seg_index.setdefault((lat_bin, lon_bin), []).append(seg)
    return seg_index


def nearest_road_dist(lat: float, lon: float, seg_index: dict[tuple[int, int], list[list[float]]], all_segments: list[list[float]]) -> float:
    base_lat_bin, base_lon_bin = bin_key(lat, lon)
    candidates: list[list[float]] = []
    for radius in range(0, 4):
        for dlat in range(-radius, radius + 1):
            for dlon in range(-radius, radius + 1):
                candidates.extend(seg_index.get((base_lat_bin + dlat, base_lon_bin + dlon), []))
        if candidates:
            break
    if not candidates:
        candidates = all_segments

    min_dist = float("inf")
    for seg in candidates:
        d = point_to_segment_km(lat, lon, seg[0], seg[1], seg[2], seg[3])
        if d < min_dist:
            min_dist = d
    return min_dist if math.isfinite(min_dist) else 10.0


def find_lat_lon_cols(sample: dict) -> tuple[str | None, str | None]:
    lat_col = next((k for k in sample if "lat" in k.lower()), None)
    lon_col = next((k for k in sample if "lon" in k.lower() or "lng" in k.lower() or k.lower() == "x"), None)
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


def main() -> int:
    road_segments = load_or_download_roads()

    print("\nComputing road proximity for each TFI cell...")
    with TFI_PATH.open() as f:
        tfi_data = json.load(f)
    tfi_cells = tfi_data["cells"]

    seg_index = build_segment_index(road_segments)

    updated_cells: list[dict] = []
    road_penalty_applied = 0
    regime_changes = {
        "STABLE→ELEVATED": 0,
        "ELEVATED→HIGH": 0,
        "HIGH→CRITICAL": 0,
        "STABLE→HIGH": 0,
        "ELEVATED→CRITICAL": 0,
        "STABLE→CRITICAL": 0,
    }

    for cell in tfi_cells:
        dist = nearest_road_dist(cell["lat"], cell["lon"], seg_index, road_segments)
        penalty = road_cut_penalty(dist)
        old_regime = cell["regime"]
        new_tfi = min(1.0, float(cell["tfi"]) + penalty)

        if new_tfi > 0.65:
            new_regime = "CRITICAL"
        elif new_tfi > 0.45:
            new_regime = "HIGH"
        elif new_tfi > 0.25:
            new_regime = "ELEVATED"
        else:
            new_regime = "STABLE"

        if old_regime != new_regime:
            regime_changes[f"{old_regime}→{new_regime}"] = regime_changes.get(f"{old_regime}→{new_regime}", 0) + 1

        if penalty > 0:
            road_penalty_applied += 1

        baseline = 25.0
        minimum = 9.0
        new_rain_threshold = baseline - (baseline - minimum) * new_tfi

        updated = dict(cell)
        comps = dict(updated.get("components", {}))
        comps["road_cut"] = round(penalty, 3)
        updated.update(
            {
                "tfi_v1": round(new_tfi, 3),
                "road_dist_km": round(dist, 3),
                "road_penalty": round(penalty, 3),
                "regime_v1": new_regime,
                "rain_threshold_v1": round(new_rain_threshold, 1),
                "components": comps,
            }
        )
        updated_cells.append(updated)

    by_regime: dict[str, int] = {}
    for cell in updated_cells:
        by_regime[cell["regime_v1"]] = by_regime.get(cell["regime_v1"], 0) + 1

    print(f"\nRoad proximity computed for {len(updated_cells)} cells")
    print(f"Cells with road penalty applied: {road_penalty_applied}")
    print()
    print("Updated TFI v1 regime summary:")
    for regime in ("CRITICAL", "HIGH", "ELEVATED", "STABLE"):
        n = by_regime.get(regime, 0)
        pct = 100.0 * n / len(updated_cells)
        print(f"  {regime:<12}: {n:4d} cells ({pct:.1f}%)")

    print()
    print("Regime upgrades from road data:")
    for change, count in sorted(regime_changes.items(), key=lambda item: (-item[1], item[0])):
        if count > 0:
            print(f"  {change}: {count} cells")

    critical = [cell for cell in updated_cells if cell["regime_v1"] == "CRITICAL"]
    critical.sort(key=lambda cell: cell["tfi_v1"], reverse=True)
    print("\nTop CRITICAL cells after road layer:")
    print(f"{'Lat':>8} {'Lon':>9} {'TFI_v1':>8} {'Road_km':>8} {'Slope°':>7} {'Rain(mm/hr)':>12}")
    print("-" * 62)
    for cell in critical[:10]:
        print(
            f"{cell['lat']:>8.3f} {cell['lon']:>9.3f} "
            f"{cell['tfi_v1']:>8.3f} {cell['road_dist_km']:>8.3f} "
            f"{cell['slope_mean']:>7.1f} {cell['rain_threshold_v1']:>12.1f}"
        )

    output = dict(tfi_data)
    output["cells"] = updated_cells
    output["data_layers_included"] = [
        "slope",
        "aspect",
        "steep_pct",
        "se_steep_pct",
        "road_cut_proximity",
    ]
    output["data_layers_pending"] = ["deforestation_nlcd", "soil_type", "prior_failure"]
    output["note"] = "TFI v1 - slope + aspect + road cut proximity."
    with TFI_V1_PATH.open("w") as f:
        json.dump(output, f)
    print(f"\nSaved TFI v1 to {TFI_V1_PATH}")

    print("\n=== RE-VALIDATING TFI v1 vs HELENE INVENTORY ===")
    with HELENE_PATH.open() as f:
        reader = csv.DictReader(f)
        landslides = list(reader)

    lat_col, lon_col = find_lat_lon_cols(landslides[0]) if landslides else (None, None)
    pilot_slides: list[dict] = []
    for row in landslides:
        try:
            lat = float(row.get(lat_col or "", ""))
            lon = float(row.get(lon_col or "", ""))
        except (TypeError, ValueError):
            continue
        if BBOX[0] <= lat <= BBOX[2] and BBOX[1] <= lon <= BBOX[3]:
            pilot_slides.append({"lat": lat, "lon": lon})

    slide_tfis: list[float] = []
    failed_cell_ids: set[int] = set()
    slide_coords = {(round(slide["lat"], 3), round(slide["lon"], 3)) for slide in pilot_slides}
    for slide in pilot_slides:
        cell, dist = nearest_cell(slide["lat"], slide["lon"], updated_cells)
        if cell and dist < 0.02:
            slide_tfis.append(cell["tfi_v1"])
            failed_cell_ids.add(id(cell))

    random = __import__("random")
    random.seed(42)
    control_tfis: list[float] = []
    for slide in pilot_slides:
        candidates = [
            cell
            for cell in updated_cells
            if id(cell) not in failed_cell_ids
            and abs(cell["lat"] - slide["lat"]) < 0.05
            and abs(cell["lon"] - slide["lon"]) < 0.05
            and (round(cell["lat"], 3), round(cell["lon"], 3)) not in slide_coords
        ]
        if candidates:
            control_tfis.append(random.choice(candidates)["tfi_v1"])

    if slide_tfis and control_tfis:
        s_mean = float(np.mean(slide_tfis))
        c_mean = float(np.mean(control_tfis))
        sep = (s_mean - c_mean) / (float(np.std(control_tfis)) + 0.001)
        auc = roc_auc_score_manual([1] * len(slide_tfis) + [0] * len(control_tfis), slide_tfis + control_tfis)
        print(f"TFI v1 - Landslide mean: {s_mean:.3f}  Control mean: {c_mean:.3f}")
        print(f"Separation: {sep:+.2f}σ  (was +0.54σ with v0.1)")
        print(f"ROC-AUC v1: {auc:.3f}  (was 0.654 with v0.1)")
        if auc >= 0.80:
            print("RESULT: STRONG VALIDATION - Holler Siren ready for next layer")
        elif auc >= 0.70:
            print("RESULT: GOOD - add deforestation layer next")
        else:
            print("RESULT: IMPROVING - continue adding layers")

        report = {
            "total_road_segments": len(road_segments),
            "cells_with_road_penalty": road_penalty_applied,
            "regime_summary_v1": by_regime,
            "regime_upgrades": regime_changes,
            "n_landslides_pilot": len(pilot_slides),
            "n_matched": len(slide_tfis),
            "n_controls": len(control_tfis),
            "landslide_mean_tfi_v1": round(s_mean, 4),
            "control_mean_tfi_v1": round(c_mean, 4),
            "separation_sigma_v1": round(sep, 3),
            "auc_v1": round(auc, 4),
            "top_critical_cells": [
                {
                    "lat": cell["lat"],
                    "lon": cell["lon"],
                    "tfi_v1": cell["tfi_v1"],
                    "road_dist_km": cell["road_dist_km"],
                    "slope_mean": cell["slope_mean"],
                    "rain_threshold_v1": cell["rain_threshold_v1"],
                }
                for cell in critical[:10]
            ],
            "note": "TFI v1 includes road cut proximity penalty from TIGER roads.",
        }
        with VALIDATION_V1_PATH.open("w") as f:
            json.dump(report, f, indent=2)
        print(f"Saved validation report to {VALIDATION_V1_PATH}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
