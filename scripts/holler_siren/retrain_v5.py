#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
import math
import pickle
import random
import subprocess
import sys
from collections import Counter
from pathlib import Path

import numpy as np
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.preprocessing import StandardScaler


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


random.seed(42)
np.random.seed(42)

DATA_DIR = ROOT / "data" / "holler_siren"
RUNS_DIR = ROOT / "runs"
RUNS_DIR.mkdir(parents=True, exist_ok=True)

FULL_BBOX_SWE = "35.0,-84.3,36.6,-81.8"
FULL_BBOX_WSEN = (-84.3, 35.0, -81.8, 36.6)
PILOT_BBOX = (35.82, -82.38, 36.12, -81.82)  # min_lat, min_lon, max_lat, max_lon

WESTERN_TERRAIN_PATH = DATA_DIR / "terrain_western_nc.json"
SOIL_CACHE = DATA_DIR / "statsgo_soil.json"
SOIL_POLY_CACHE = DATA_DIR / "statsgo_soil_polygons.json"
GEO_CACHE = DATA_DIR / "nc_geology.json"
HELENE_PATH = DATA_DIR / "helene_landslides.csv"
OUTPUT_PATH = DATA_DIR / "tfi_v5_western_nc.json"
PILOT_OUTPUT_PATH = DATA_DIR / "tfi_v5_yancey_mitchell.json"
MODEL_PICKLE_PATH = DATA_DIR / "model_v5.pkl"

FEATURES = [
    "slope_mean",
    "slope_max",
    "pct_steep",
    "pct_se_facing",
    "pct_se_steep",
    "twi_mean",
    "twi_p90",
    "prior_failure_score",
    "soil_risk",
    "geology_risk",
]


def point_in_polygon(lat: float, lon: float, ring: list[list[float]]) -> bool:
    inside = False
    j = len(ring) - 1
    for i in range(len(ring)):
        yi, xi = ring[i]
        yj, xj = ring[j]
        intersects = ((xi > lon) != (xj > lon)) and (
            lat < (yj - yi) * (lon - xi) / ((xj - xi) + 1e-12) + yi
        )
        if intersects:
            inside = not inside
        j = i
    return inside


def ensure_western_terrain() -> None:
    if WESTERN_TERRAIN_PATH.exists():
        return
    cmd = [
        str(ROOT / ".venv" / "bin" / "python"),
        str(ROOT / "scripts" / "holler_siren" / "ingest_terrain.py"),
        "--bbox",
        FULL_BBOX_SWE,
        "--output",
        str(WESTERN_TERRAIN_PATH),
        "--raw-dir",
        str(DATA_DIR / "raw_dem_western_nc"),
        "--area-name",
        "Western NC Helene footprint",
        "--coarse-res-m",
        "100",
        "--include-twi",
    ]
    subprocess.run(cmd, check=True, cwd=ROOT)


def load_json(path: Path) -> dict:
    with path.open() as f:
        return json.load(f)


def assign_soil(cells: list[dict], soil_polygons: list[dict], soil_by_mukey: dict[str, dict]) -> None:
    index: dict[tuple[int, int], list[dict]] = {}
    for polygon in soil_polygons:
        west, south, east, north = polygon["bbox"]
        for lat_key in range(int(math.floor(south * 10)), int(math.ceil(north * 10)) + 1):
            for lon_key in range(int(math.floor(west * 10)), int(math.ceil(east * 10)) + 1):
                index.setdefault((lat_key, lon_key), []).append(polygon)

    for cell in cells:
        lat = float(cell["lat"])
        lon = float(cell["lon"])
        key = (int(round(lat * 10)), int(round(lon * 10)))
        match = None
        for polygon in index.get(key, []):
            west, south, east, north = polygon["bbox"]
            if not (west <= lon <= east and south <= lat <= north):
                continue
            if point_in_polygon(lat, lon, polygon["ring"]):
                match = polygon
                break
        if match:
            info = soil_by_mukey.get(match["mukey"], {})
            hydgrp = info.get("hydgrp") or match.get("hydgrpdcd") or "B"
            risk = info.get("risk", {"A": 0.0, "B": 0.1, "C": 0.2, "D": 0.3}.get(hydgrp, 0.1))
        else:
            hydgrp = "B"
            risk = 0.1
        cell["soil_hydgrp"] = hydgrp
        cell["soil_risk"] = round(float(risk), 3)


def assign_geology(cells: list[dict], geology_samples: dict) -> None:
    samples = geology_samples.get("samples", [])
    if not samples:
        for cell in cells:
            cell["geology_type"] = "unknown"
            cell["geology_risk"] = 0.1
        return

    west, south, east, north = geology_samples.get("bbox", FULL_BBOX_WSEN)
    step = float(geology_samples.get("step_deg", 0.05))
    grid = {(sample["lat"], sample["lon"]): sample for sample in samples}

    def nearest_sample(lat: float, lon: float) -> dict:
        lat_s = round(round((lat - south) / step) * step + south, 4)
        lon_s = round(round((lon - west) / step) * step + west, 4)
        sample = grid.get((lat_s, lon_s))
        if sample is not None:
            return sample
        return min(samples, key=lambda row: (row["lat"] - lat) ** 2 + (row["lon"] - lon) ** 2)

    for cell in cells:
        sample = nearest_sample(float(cell["lat"]), float(cell["lon"]))
        cell["geology_type"] = sample.get("rock_type", "unknown")
        cell["geology_risk"] = round(float(sample.get("risk", 0.1)), 3)


def assign_prior_failure(cells: list[dict], failures: list[dict[str, float]]) -> None:
    for cell in cells:
        lat = float(cell["lat"])
        lon = float(cell["lon"])
        count = 0
        min_dist = float("inf")
        for failure in failures:
            dlat = (failure["lat"] - lat) * 111.32
            dlon = (failure["lon"] - lon) * 111.32 * math.cos(math.radians(lat))
            dist = math.sqrt(dlat**2 + dlon**2)
            if dist < 2.0:
                count += 1
            if dist < min_dist:
                min_dist = dist
        cell["helene_failures_within_2km"] = count
        cell["nearest_helene_km"] = round(min_dist, 3)
        cell["prior_failure_score"] = round(min(count / 5.0, 1.0) * 0.30, 3)


def find_lat_lon_cols(sample: dict) -> tuple[str | None, str | None]:
    lat_col = next((k for k in sample if "lat" in k.lower()), None)
    lon_col = next((k for k in sample if "lon" in k.lower() or k.lower() == "x"), None)
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


def threshold_from_prob(prob: float, p75: float, p85: float, p90: float, p95: float) -> float:
    if prob >= p95:
        return 10.0
    if prob >= p90:
        return 15.0
    if prob >= p85:
        return 20.0
    if prob >= p75:
        return 25.0
    return 35.0


def main() -> int:
    print("=== STEP 4: RETRAIN ON FULL HELENE INVENTORY ===")
    ensure_western_terrain()

    terrain_data = load_json(WESTERN_TERRAIN_PATH)
    cells = terrain_data["cells"]
    print(f"Terrain cells: {len(cells)}")

    soil_tabular = load_json(SOIL_CACHE)
    soil_polygons = load_json(SOIL_POLY_CACHE)
    headers = soil_tabular["Table"][0]
    soil_by_mukey = {
        str(dict(zip(headers, row)).get("mukey", "")).strip(): {
            "hydgrp": str(dict(zip(headers, row)).get("hydgrpdcd") or dict(zip(headers, row)).get("hydgrp") or "B").strip(),
            "risk": {"A": 0.0, "B": 0.1, "C": 0.2, "D": 0.3, "A/D": 0.15, "B/D": 0.2, "C/D": 0.25}.get(
                str(dict(zip(headers, row)).get("hydgrpdcd") or dict(zip(headers, row)).get("hydgrp") or "B").strip(),
                0.1,
            ),
        }
        for row in soil_tabular["Table"][1:]
    }
    assign_soil(cells, soil_polygons.get("polygons", []), soil_by_mukey)

    geology_data = load_json(GEO_CACHE)
    assign_geology(cells, geology_data)

    with HELENE_PATH.open() as f:
        landslides = list(csv.DictReader(f))
    lat_col, lon_col = find_lat_lon_cols(landslides[0])
    if lat_col is None or lon_col is None:
        raise RuntimeError("Could not find lat/lon columns in Helene inventory")

    failures: list[dict[str, float]] = []
    for landslide in landslides:
        try:
            lat = float(landslide.get(lat_col, 0))
            lon = float(landslide.get(lon_col, 0))
        except (TypeError, ValueError):
            continue
        if lat and lon:
            failures.append({"lat": lat, "lon": lon})
    print(f"Total Helene failures: {len(failures)}")

    assign_prior_failure(cells, failures)

    slide_coords = set()
    records: list[dict[str, float | int]] = []
    matched_failures: list[dict[str, float]] = []
    print("Matching all failures to terrain cells...")
    for failure in failures:
        cell, dist = nearest_cell(failure["lat"], failure["lon"], cells)
        if cell is not None and dist < 0.02:
            record = {feature: float(cell.get(feature, 0.0)) for feature in FEATURES}
            record["label"] = 1
            records.append(record)
            matched_failures.append(failure)
            slide_coords.add((round(cell["lat"], 3), round(cell["lon"], 3)))

    matched = len(matched_failures)
    print(f"Failures matched to cells: {matched}")

    for failure in matched_failures:
        center, _ = nearest_cell(failure["lat"], failure["lon"], cells)
        if center is None:
            continue
        candidates = [
            cell
            for cell in cells
            if abs(cell["lat"] - center["lat"]) < 0.08
            and abs(cell["lon"] - center["lon"]) < 0.08
            and (round(cell["lat"], 3), round(cell["lon"], 3)) not in slide_coords
        ]
        if candidates:
            ctrl = random.choice(candidates)
            record = {feature: float(ctrl.get(feature, 0.0)) for feature in FEATURES}
            record["label"] = 0
            records.append(record)

    n_fail = sum(1 for record in records if record["label"] == 1)
    print(f"Total records: {len(records)} ({n_fail} failures, {len(records) - n_fail} controls)")

    X = np.array([[record[feature] for feature in FEATURES] for record in records], dtype=float)
    y = np.array([record["label"] for record in records], dtype=int)
    scaler = StandardScaler()
    Xs = scaler.fit_transform(X)
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)

    print()
    print("=== MODEL COMPARISON ===")
    models = {
        "LogisticRegression": LogisticRegression(class_weight="balanced", max_iter=1000, C=1.0, random_state=42),
        "RandomForest": RandomForestClassifier(
            n_estimators=200, class_weight="balanced", max_depth=6, random_state=42
        ),
        "GradientBoosting": GradientBoostingClassifier(
            n_estimators=150, max_depth=3, learning_rate=0.08, random_state=42
        ),
    }

    best_auc = -1.0
    best_name = ""
    best_model = None
    model_scores: dict[str, dict] = {}
    for name, model in models.items():
        X_input = Xs if name == "LogisticRegression" else X
        aucs = cross_val_score(model, X_input, y, cv=cv, scoring="roc_auc")
        mean_auc = float(np.mean(aucs))
        std_auc = float(np.std(aucs))
        model_scores[name] = {"mean_auc": round(mean_auc, 4), "std_auc": round(std_auc, 4)}
        print(f"  {name:<25}: AUC {mean_auc:.3f} std={std_auc:.3f} folds={[round(float(a), 3) for a in aucs]}")
        if mean_auc > best_auc:
            best_auc = mean_auc
            best_name = name
            best_model = model

    assert best_model is not None
    print(f"\nBest model: {best_name} (AUC {best_auc:.3f})")
    print()
    print("Version history:")
    print("  v0.1 hand-crafted slope+aspect:      0.654")
    print("  v3   learned slope+aspect:           0.629")
    print("  v4   +TWI +prior failure (378 pts):  0.716")
    print(f"  v5   best model ({matched} pts):           {best_auc:.3f}")

    if best_name == "LogisticRegression":
        best_model.fit(Xs, y)
        X_all = scaler.transform(np.array([[cell.get(feature, 0.0) for feature in FEATURES] for cell in cells]))
        probs = best_model.predict_proba(X_all)[:, 1]
    else:
        best_model.fit(X, y)
        X_all = np.array([[cell.get(feature, 0.0) for feature in FEATURES] for cell in cells], dtype=float)
        probs = best_model.predict_proba(X_all)[:, 1]

    p75 = float(np.percentile(probs, 75))
    p85 = float(np.percentile(probs, 85))
    p90 = float(np.percentile(probs, 90))
    p95 = float(np.percentile(probs, 95))

    by_regime = Counter()
    updated_cells: list[dict] = []
    for idx, cell in enumerate(cells):
        prob = round(float(probs[idx]), 4)
        if prob >= p95:
            regime = "CRITICAL"
        elif prob >= p85:
            regime = "HIGH"
        elif prob >= p75:
            regime = "ELEVATED"
        else:
            regime = "STABLE"
        by_regime[regime] += 1
        updated = cell.copy()
        updated["tfi_v5"] = prob
        updated["regime_v5"] = regime
        updated["rain_threshold_v5"] = threshold_from_prob(prob, p75, p85, p90, p95)
        updated_cells.append(updated)

    print()
    print("v5 regime summary:")
    for regime in ["CRITICAL", "HIGH", "ELEVATED", "STABLE"]:
        count = by_regime.get(regime, 0)
        print(f"  {regime:<12}: {count:5d} ({100 * count / len(updated_cells):.1f}%)")

    terrain_data["cells"] = updated_cells
    terrain_data["pilot_area"] = "Western NC Helene footprint"
    terrain_data["helene_count"] = matched
    terrain_data["model_v5"] = {
        "type": best_name,
        "features": FEATURES,
        "cv_auc": round(best_auc, 4),
        "trained_on": f"All {matched} Helene failures across western NC",
        "p75": round(p75, 4),
        "p85": round(p85, 4),
        "p90": round(p90, 4),
        "p95": round(p95, 4),
        "model_scores": model_scores,
    }
    terrain_data["calibration"] = {
        "method": "percentile-anchored nonlinear",
        "anchors": {"p75": round(p75, 4), "p85": round(p85, 4), "p90": round(p90, 4), "p95": round(p95, 4)},
        "thresholds_mm_hr": {
            "top_5pct": 10,
            "top_10pct": 15,
            "top_15pct": 20,
            "top_25pct": 25,
            "bottom_75pct": 35,
        },
    }

    with OUTPUT_PATH.open("w") as f:
        json.dump(terrain_data, f)

    pilot_cells = [
        cell
        for cell in updated_cells
        if PILOT_BBOX[0] <= cell["lat"] <= PILOT_BBOX[2] and PILOT_BBOX[1] <= cell["lon"] <= PILOT_BBOX[3]
    ]
    pilot_payload = dict(terrain_data)
    pilot_payload["pilot_area"] = "Yancey + Mitchell Counties, NC"
    pilot_payload["cells"] = pilot_cells
    with PILOT_OUTPUT_PATH.open("w") as f:
        json.dump(pilot_payload, f)

    with MODEL_PICKLE_PATH.open("wb") as f:
        pickle.dump(
            {
                "model": best_model,
                "scaler": scaler if best_name == "LogisticRegression" else None,
                "features": FEATURES,
                "auc": best_auc,
                "model_name": best_name,
            },
            f,
        )

    print(f"\nSaved v5 full model to {OUTPUT_PATH}")
    print(f"Saved pilot subset to {PILOT_OUTPUT_PATH}")
    print(f"Saved model pickle to {MODEL_PICKLE_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
