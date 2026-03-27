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
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.preprocessing import StandardScaler


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


random.seed(42)
np.random.seed(42)

DATA_DIR = ROOT / "data" / "holler_siren"
TWI_PATH = DATA_DIR / "tfi_twi_yancey_mitchell.json"
HELENE_PATH = DATA_DIR / "helene_landslides.csv"
OUTPUT_PATH = DATA_DIR / "tfi_v4_yancey_mitchell.json"
WEIGHTS_PATH = DATA_DIR / "tfi_model_weights_v4.json"

BBOX = (35.82, -82.38, 36.12, -81.82)  # min_lat, min_lon, max_lat, max_lon
FEATURES = [
    "slope_mean",
    "slope_max",
    "pct_steep",
    "pct_se_facing",
    "pct_se_steep",
    "twi_mean",
    "twi_p90",
    "prior_failure_score",
]


def _find_lat_lon_cols(sample: dict) -> tuple[str | None, str | None]:
    lat_col = next((k for k in sample if "lat" in k.lower()), None)
    lon_col = next((k for k in sample if "lon" in k.lower() or k.lower() == "x"), None)
    return lat_col, lon_col


def _nearest_cell(lat: float, lon: float, cells: list[dict]) -> tuple[dict | None, float]:
    best = None
    best_d = float("inf")
    for cell in cells:
        d = math.sqrt((cell["lat"] - lat) ** 2 + (cell["lon"] - lon) ** 2)
        if d < best_d:
            best = cell
            best_d = d
    return best, best_d


def _calibrated_threshold(tfi: float, p75: float, p85: float, p90: float, p95: float) -> float:
    if tfi >= p95:
        return 10.0
    if tfi >= p90:
        return 15.0
    if tfi >= p85:
        return 20.0
    if tfi >= p75:
        return 25.0
    return 35.0


def main() -> int:
    with TWI_PATH.open() as f:
        tfi_data = json.load(f)
    cells = tfi_data["cells"]

    with HELENE_PATH.open() as f:
        landslides = list(csv.DictReader(f))

    lat_col, lon_col = _find_lat_lon_cols(landslides[0])
    if lat_col is None or lon_col is None:
        raise RuntimeError("Could not find lat/lon columns in Helene inventory")

    all_failures: list[dict[str, float]] = []
    pilot_slides: list[dict[str, float]] = []
    for landslide in landslides:
        try:
            lat = float(landslide.get(lat_col, 0))
            lon = float(landslide.get(lon_col, 0))
        except (TypeError, ValueError):
            continue
        if not (lat and lon):
            continue
        all_failures.append({"lat": lat, "lon": lon})
        if BBOX[0] <= lat <= BBOX[2] and BBOX[1] <= lon <= BBOX[3]:
            pilot_slides.append({"lat": lat, "lon": lon})

    print(f"Failure points in full Helene inventory: {len(all_failures)}")
    print(f"Failure points in pilot area: {len(pilot_slides)}")
    print(f"Cells available: {len(cells)}")
    print("Note: training labels remain pilot-area-only because terrain cells only exist for Yancey/Mitchell.")

    slide_coords = {(round(ls["lat"], 3), round(ls["lon"], 3)) for ls in pilot_slides}
    records: list[dict[str, float | int]] = []

    for landslide in pilot_slides:
        cell, dist = _nearest_cell(landslide["lat"], landslide["lon"], cells)
        if cell is not None and dist < 0.02:
            record = {feature: float(cell.get(feature, 0.0)) for feature in FEATURES}
            record["label"] = 1
            records.append(record)

    n_fail = sum(int(record["label"]) for record in records)
    for landslide in pilot_slides:
        candidates = [
            cell
            for cell in cells
            if abs(cell["lat"] - landslide["lat"]) < 0.05
            and abs(cell["lon"] - landslide["lon"]) < 0.05
            and (round(cell["lat"], 3), round(cell["lon"], 3)) not in slide_coords
        ]
        if candidates:
            ctrl = random.choice(candidates)
            record = {feature: float(ctrl.get(feature, 0.0)) for feature in FEATURES}
            record["label"] = 0
            records.append(record)

    print(f"Total records: {len(records)} ({n_fail} failures)")

    X = np.array([[float(record[feature]) for feature in FEATURES] for record in records], dtype=float)
    y = np.array([int(record["label"]) for record in records], dtype=int)
    ob = y == 1
    non = y == 0

    print()
    print("=== FEATURE SEPARATION (expanded) ===")
    print(f"{'Feature':<25} {'Failure':>10} {'Control':>10} {'Sep(σ)':>8}")
    print("-" * 57)
    separation_rows: list[dict[str, float]] = []
    for idx, feature in enumerate(FEATURES):
        failure_mean = float(np.mean(X[ob, idx]))
        control_mean = float(np.mean(X[non, idx]))
        sep = float((failure_mean - control_mean) / (np.std(X[non, idx]) + 0.001))
        flag = " <<<" if abs(sep) > 0.4 else (" <<" if abs(sep) > 0.2 else "")
        print(f"{feature:<25} {failure_mean:>10.3f} {control_mean:>10.3f} {sep:>8.2f}{flag}")
        separation_rows.append(
            {
                "feature": feature,
                "failure_mean": round(failure_mean, 4),
                "control_mean": round(control_mean, 4),
                "separation_sigma": round(sep, 4),
            }
        )

    scaler = StandardScaler()
    Xs = scaler.fit_transform(X)
    model = LogisticRegression(class_weight="balanced", max_iter=1000, random_state=42)
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    aucs = cross_val_score(model, Xs, y, cv=cv, scoring="roc_auc")

    print()
    print("=== FULL MODEL AUC ===")
    print(f"Folds: {[round(a, 3) for a in aucs]}")
    print(f"Mean AUC: {np.mean(aucs):.3f}  std={np.std(aucs):.3f}")
    print()
    print("Version history:")
    print("  v0.1 slope+aspect (hand-crafted):   0.654")
    print("  v3   learned (slope+aspect only):   0.629")
    print(f"  v4   learned (+TWI +prior failure): {np.mean(aucs):.3f}")

    model.fit(Xs, y)
    weights = sorted(zip(FEATURES, model.coef_[0]), key=lambda item: abs(item[1]), reverse=True)
    print()
    print("Feature weights (v4):")
    for feature, coef in weights:
        print(f"  {feature:<25}: {coef:+.3f}")

    X_all = np.array([[float(cell.get(feature, 0.0)) for feature in FEATURES] for cell in cells], dtype=float)
    probs = model.predict_proba(scaler.transform(X_all))[:, 1]

    p75 = float(np.percentile(probs, 75))
    p85 = float(np.percentile(probs, 85))
    p90 = float(np.percentile(probs, 90))
    p95 = float(np.percentile(probs, 95))

    updated: list[dict] = []
    by_regime: dict[str, int] = {}
    for idx, cell in enumerate(cells):
        tfi = round(float(probs[idx]), 4)
        threshold = _calibrated_threshold(tfi, p75, p85, p90, p95)
        if tfi >= p95:
            regime = "CRITICAL"
        elif tfi >= p85:
            regime = "HIGH"
        elif tfi >= p75:
            regime = "ELEVATED"
        else:
            regime = "STABLE"
        by_regime[regime] = by_regime.get(regime, 0) + 1
        updated_cell = cell.copy()
        updated_cell["tfi_v4"] = tfi
        updated_cell["regime_v4"] = regime
        updated_cell["rain_threshold_v4"] = threshold
        updated.append(updated_cell)

    print()
    print("v4 regime summary:")
    for regime in ["CRITICAL", "HIGH", "ELEVATED", "STABLE"]:
        count = by_regime.get(regime, 0)
        print(f"  {regime:<12}: {count:4d} ({100 * count / len(updated):.1f}%)")

    slide_tfis: list[float] = []
    for landslide in pilot_slides:
        cell, dist = _nearest_cell(landslide["lat"], landslide["lon"], cells)
        if cell is not None and dist < 0.02:
            idx = cells.index(cell)
            slide_tfis.append(float(probs[idx]))

    ctrl_tfis: list[float] = []
    for landslide in pilot_slides:
        candidates = [
            cell
            for cell in cells
            if abs(cell["lat"] - landslide["lat"]) < 0.05
            and abs(cell["lon"] - landslide["lon"]) < 0.05
            and (round(cell["lat"], 3), round(cell["lon"], 3)) not in slide_coords
        ]
        if candidates:
            ctrl = random.choice(candidates)
            idx = cells.index(ctrl)
            ctrl_tfis.append(float(probs[idx]))

    auc_final = None
    if slide_tfis and ctrl_tfis:
        auc_final = float(
            roc_auc_score([1] * len(slide_tfis) + [0] * len(ctrl_tfis), slide_tfis + ctrl_tfis)
        )
        print(f"\nFinal validation AUC (v4): {auc_final:.3f}")

    ranked = sorted(updated, key=lambda cell: cell["tfi_v4"], reverse=True)
    print("\nTop 10 highest-risk cells (v4):")
    print(f"{'Lat':>8} {'Lon':>9} {'TFI':>7} {'TWI':>7} {'Prior':>7} {'Slope':>7}")
    print("-" * 60)
    for cell in ranked[:10]:
        print(
            f"{cell['lat']:>8.3f} {cell['lon']:>9.3f} {cell['tfi_v4']:>7.4f} "
            f"{cell.get('twi_mean', 0):>7.2f} {cell.get('prior_failure_score', 0):>7.3f} "
            f"{cell.get('slope_mean', 0):>7.1f}"
        )

    tfi_data["cells"] = updated
    tfi_data["model_v4"] = {
        "type": "logistic_regression",
        "features": FEATURES,
        "cv_auc": round(float(np.mean(aucs)), 4),
        "cv_std": round(float(np.std(aucs)), 4),
        "final_auc": round(auc_final, 4) if auc_final is not None else None,
        "note": "Logistic regression with TWI and prior failure layer",
        "training_scope": "Pilot-area labels with full Helene inventory used for prior-failure context",
    }
    tfi_data["calibration"] = {
        "method": "percentile-anchored nonlinear",
        "anchors": {
            "p75": round(p75, 4),
            "p85": round(p85, 4),
            "p90": round(p90, 4),
            "p95": round(p95, 4),
        },
        "thresholds_mm_hr": {
            "top_5pct": 10,
            "top_10pct": 15,
            "top_15pct": 20,
            "top_25pct": 25,
            "bottom_75pct": 35,
        },
        "physical_basis": (
            "Top quartile terrain gets lower rain thresholds; "
            "bottom 75 percent remains at 35 mm/hr unless extreme rain arrives."
        ),
    }
    tfi_data["helene_count"] = len(pilot_slides)
    with OUTPUT_PATH.open("w") as f:
        json.dump(tfi_data, f)

    weights_payload = {
        "features": FEATURES,
        "coefficients": {feature: round(float(coef), 4) for feature, coef in zip(FEATURES, model.coef_[0])},
        "intercept": round(float(model.intercept_[0]), 4),
        "scaler_mean": [round(float(value), 4) for value in scaler.mean_],
        "scaler_std": [round(float(value), 4) for value in scaler.scale_],
        "cv_auc": round(float(np.mean(aucs)), 4),
        "cv_std": round(float(np.std(aucs)), 4),
        "final_auc": round(auc_final, 4) if auc_final is not None else None,
        "p75": round(p75, 4),
        "p85": round(p85, 4),
        "p90": round(p90, 4),
        "p95": round(p95, 4),
    }
    with WEIGHTS_PATH.open("w") as f:
        json.dump(weights_payload, f, indent=2)

    print(f"\nSaved v4 model to {OUTPUT_PATH}")
    print(f"Saved weights to {WEIGHTS_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
