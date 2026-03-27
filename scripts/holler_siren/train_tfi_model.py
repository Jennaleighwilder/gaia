#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
import math
import random
import sys
from pathlib import Path

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.preprocessing import StandardScaler


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


random.seed(42)
np.random.seed(42)

OUTPUT_DIR = ROOT / "data" / "holler_siren"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

TFI_V2_PATH = OUTPUT_DIR / "tfi_v2_yancey_mitchell.json"
HELENE_PATH = OUTPUT_DIR / "helene_landslides.csv"
TFI_LEARNED_PATH = OUTPUT_DIR / "tfi_learned_yancey_mitchell.json"
MODEL_WEIGHTS_PATH = OUTPUT_DIR / "tfi_model_weights.json"
MODEL_REPORT_PATH = OUTPUT_DIR / "tfi_model_report.json"

BBOX = (35.82, -82.38, 36.12, -81.82)  # min_lat, min_lon, max_lat, max_lon
FEATURES = [
    "slope_mean",
    "slope_max",
    "pct_steep",
    "pct_very_steep",
    "pct_se_facing",
    "pct_se_steep",
    "elev_m",
    "road_dist_km",
    "pct_forest_loss",
]


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


def main() -> int:
    with TFI_V2_PATH.open() as f:
        tfi_data = json.load(f)
    cells = tfi_data["cells"]

    with HELENE_PATH.open() as f:
        landslides = list(csv.DictReader(f))

    lat_col, lon_col = find_lat_lon_cols(landslides[0])
    if lat_col is None or lon_col is None:
        raise RuntimeError("Could not find lat/lon columns in Helene inventory")

    pilot_slides: list[dict[str, float]] = []
    for ls in landslides:
        try:
            lat = float(ls.get(lat_col, 0))
            lon = float(ls.get(lon_col, 0))
        except (TypeError, ValueError):
            continue
        if BBOX[0] <= lat <= BBOX[2] and BBOX[1] <= lon <= BBOX[3]:
            pilot_slides.append({"lat": lat, "lon": lon})

    print(f"Helene failures in pilot area: {len(pilot_slides)}")
    print(f"TFI cells available: {len(cells)}")

    slide_coords = {(round(ls["lat"], 3), round(ls["lon"], 3)) for ls in pilot_slides}
    records: list[dict[str, float | int]] = []

    for ls in pilot_slides:
        cell, dist = nearest_cell(ls["lat"], ls["lon"], cells)
        if cell is not None and dist < 0.02:
            feat = {feature: float(cell.get(feature, 0)) for feature in FEATURES}
            feat["label"] = 1
            records.append(feat)

    n_failures = sum(int(r["label"]) for r in records)
    print(f"Failures matched to cells: {n_failures}")

    for ls in pilot_slides:
        candidates = [
            cell
            for cell in cells
            if abs(cell["lat"] - ls["lat"]) < 0.05
            and abs(cell["lon"] - ls["lon"]) < 0.05
            and (round(cell["lat"], 3), round(cell["lon"], 3)) not in slide_coords
        ]
        if candidates:
            ctrl = random.choice(candidates)
            feat = {feature: float(ctrl.get(feature, 0)) for feature in FEATURES}
            feat["label"] = 0
            records.append(feat)

    print(f"Total records: {len(records)} ({n_failures} failures, {len(records) - n_failures} controls)")
    print()

    X = np.array([[float(r[feature]) for feature in FEATURES] for r in records], dtype=float)
    y = np.array([int(r["label"]) for r in records], dtype=int)
    ob_idx = y == 1
    non_idx = y == 0

    print("=== FEATURE SEPARATION ===")
    print(f"{'Feature':<20} {'Failure':>10} {'Control':>10} {'Sep(σ)':>8}")
    print("-" * 52)
    separation_rows: list[dict[str, float]] = []
    for idx, feature in enumerate(FEATURES):
        failure_mean = float(np.mean(X[ob_idx, idx]))
        control_mean = float(np.mean(X[non_idx, idx]))
        sep = float((failure_mean - control_mean) / (np.std(X[non_idx, idx]) + 0.001))
        flag = " <<" if abs(sep) > 0.3 else ""
        print(f"{feature:<20} {failure_mean:>10.3f} {control_mean:>10.3f} {sep:>8.2f}{flag}")
        separation_rows.append(
            {
                "feature": feature,
                "failure_mean": round(failure_mean, 4),
                "control_mean": round(control_mean, 4),
                "separation_sigma": round(sep, 4),
            }
        )

    print()
    scaler = StandardScaler()
    Xs = scaler.fit_transform(X)
    lr = LogisticRegression(class_weight="balanced", max_iter=1000, random_state=42)
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    aucs = cross_val_score(lr, Xs, y, cv=cv, scoring="roc_auc")

    print("=== LEARNED MODEL (logistic regression) ===")
    print(f"Folds: {[round(a, 3) for a in aucs]}")
    print(f"Mean AUC: {np.mean(aucs):.3f}  std={np.std(aucs):.3f}")
    print()
    print("Comparison:")
    print("  Hand-crafted v0.1 (slope+aspect penalties):  0.654")
    print("  Hand-crafted v1   (+road penalties):          0.605")
    print("  Hand-crafted v2   (+forest loss penalties):   0.561")
    print(f"  Learned model     (all features, CV):         {np.mean(aucs):.3f}")

    lr.fit(Xs, y)
    importances = sorted(zip(FEATURES, lr.coef_[0]), key=lambda item: abs(item[1]), reverse=True)
    print()
    print("Feature weights (learned):")
    for feature, coef in importances:
        bar = "+" * int(abs(coef) * 5) if coef > 0 else "-" * int(abs(coef) * 5)
        print(f"  {feature:<20}: {coef:+.3f}  {bar}")

    X_all = np.array([[float(cell.get(feature, 0)) for feature in FEATURES] for cell in cells], dtype=float)
    X_all_scaled = scaler.transform(X_all)
    probs = lr.predict_proba(X_all_scaled)[:, 1]

    by_regime: dict[str, int] = {}
    updated_cells: list[dict] = []
    for idx, cell in enumerate(cells):
        tfi_learned = round(float(probs[idx]), 4)
        if tfi_learned > 0.65:
            regime = "CRITICAL"
        elif tfi_learned > 0.45:
            regime = "HIGH"
        elif tfi_learned > 0.25:
            regime = "ELEVATED"
        else:
            regime = "STABLE"
        by_regime[regime] = by_regime.get(regime, 0) + 1
        updated = cell.copy()
        updated["tfi_learned"] = tfi_learned
        updated["regime_learned"] = regime
        updated["rain_threshold_learned"] = round(25.0 - (25.0 - 9.0) * tfi_learned, 1)
        updated_cells.append(updated)

    print()
    print("Learned TFI regime summary:")
    for regime in ["CRITICAL", "HIGH", "ELEVATED", "STABLE"]:
        count = by_regime.get(regime, 0)
        print(f"  {regime:<12}: {count:4d} ({100 * count / len(updated_cells):.1f}%)")

    critical = sorted(
        [cell for cell in updated_cells if cell["regime_learned"] == "CRITICAL"],
        key=lambda cell: cell["tfi_learned"],
        reverse=True,
    )
    print()
    print("Top 10 highest-risk cells (learned model):")
    print(f"{'Lat':>8} {'Lon':>9} {'TFI':>7} {'Slope°':>7} {'SE%':>6} {'RoadKm':>8} {'Rain':>6}")
    print("-" * 60)
    for cell in critical[:10]:
        print(
            f"{cell['lat']:>8.3f} {cell['lon']:>9.3f} {cell['tfi_learned']:>7.4f} "
            f"{cell['slope_mean']:>7.1f} {cell['pct_se_facing']:>6.1f} "
            f"{cell['road_dist_km']:>8.3f} {cell['rain_threshold_learned']:>6.1f}"
        )

    out = tfi_data.copy()
    out["cells"] = updated_cells
    out["model"] = {
        "type": "logistic_regression",
        "features": FEATURES,
        "cv_auc": round(float(np.mean(aucs)), 4),
        "cv_std": round(float(np.std(aucs)), 4),
        "trained_on": f"{n_failures} Helene failure points",
    }
    with TFI_LEARNED_PATH.open("w") as f:
        json.dump(out, f)
    print(f"\nSaved learned model to {TFI_LEARNED_PATH}")

    model_export = {
        "features": FEATURES,
        "coefficients": {feature: round(float(coef), 4) for feature, coef in zip(FEATURES, lr.coef_[0])},
        "intercept": round(float(lr.intercept_[0]), 4),
        "scaler_mean": [round(float(value), 4) for value in scaler.mean_],
        "scaler_std": [round(float(value), 4) for value in scaler.scale_],
        "cv_auc": round(float(np.mean(aucs)), 4),
        "cv_std": round(float(np.std(aucs)), 4),
        "trained_on": "USGS Helene landslide inventory, Yancey+Mitchell NC",
        "validation": "Holler Siren v3 — trained on real failures",
    }
    with MODEL_WEIGHTS_PATH.open("w") as f:
        json.dump(model_export, f, indent=2)
    print(f"Saved model weights to {MODEL_WEIGHTS_PATH}")

    report = {
        "n_failures_pilot": len(pilot_slides),
        "n_failures_matched": n_failures,
        "n_controls": len(records) - n_failures,
        "features": FEATURES,
        "feature_separation": separation_rows,
        "fold_aucs": [round(float(a), 4) for a in aucs],
        "cv_auc": round(float(np.mean(aucs)), 4),
        "cv_std": round(float(np.std(aucs)), 4),
        "feature_weights": {feature: round(float(coef), 4) for feature, coef in importances},
        "regime_summary_learned": by_regime,
        "top_cells_learned": [
            {
                "lat": cell["lat"],
                "lon": cell["lon"],
                "tfi_learned": cell["tfi_learned"],
                "slope_mean": cell["slope_mean"],
                "pct_se_facing": cell["pct_se_facing"],
                "road_dist_km": cell["road_dist_km"],
                "rain_threshold_learned": cell["rain_threshold_learned"],
            }
            for cell in critical[:10]
        ],
    }
    with MODEL_REPORT_PATH.open("w") as f:
        json.dump(report, f, indent=2)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
