#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import pickle
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


DATA_DIR = ROOT / "data" / "holler_siren"
MODEL_PATH = DATA_DIR / "model_v5.pkl"
WESTERN_PATH = DATA_DIR / "tfi_v5_western_nc.json"


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
    return slug or "custom_region"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Apply the western-NC v5 Holler Siren model to a new region.")
    parser.add_argument("--region", required=True, help="Region slug, e.g. east_tennessee")
    parser.add_argument("--terrain-path", help="Optional explicit terrain JSON path")
    parser.add_argument("--output", help="Optional explicit output JSON path")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    region = _slugify(args.region)
    terrain_path = Path(args.terrain_path) if args.terrain_path else DATA_DIR / f"terrain_{region}.json"
    output_path = Path(args.output) if args.output else DATA_DIR / f"tfi_{region}_transfer.json"

    if not MODEL_PATH.exists():
        print(f"ERROR: model file missing at {MODEL_PATH}")
        return 1
    if not terrain_path.exists():
        print(f"ERROR: terrain file missing at {terrain_path}")
        return 1

    try:
        with MODEL_PATH.open("rb") as f:
            model_bundle = pickle.load(f)
    except ModuleNotFoundError as e:
        print(f"ERROR: model unpickle requires installed sklearn runtime: {e}")
        return 1

    model = model_bundle["model"]
    scaler = model_bundle["scaler"]
    features = model_bundle["features"]

    with terrain_path.open() as f:
        terrain = json.load(f)
    with WESTERN_PATH.open() as f:
        western = json.load(f)

    cells = terrain.get("cells") or []
    print(f"Loaded {len(cells)} terrain cells for {region}")
    print(f"Features: {features}")

    X = np.array([[cell.get(feature, 0.0) for feature in features] for cell in cells], dtype=float)
    if X.size == 0:
        print("ERROR: no terrain cells to score")
        return 1

    Xs = scaler.transform(X) if scaler is not None else X
    probs = model.predict_proba(Xs)[:, 1]

    p75, p85, p90, p95 = np.percentile(probs, [75, 85, 90, 95])

    def threshold(prob: float) -> float:
        if prob >= p95:
            return 10.0
        if prob >= p90:
            return 15.0
        if prob >= p85:
            return 20.0
        if prob >= p75:
            return 25.0
        return 35.0

    def regime(prob: float) -> str:
        if prob >= p95:
            return "CRITICAL"
        if prob >= p90:
            return "HIGH"
        if prob >= p85:
            return "ELEVATED"
        if prob >= p75:
            return "WATCH"
        return "STABLE"

    updated = []
    for idx, cell in enumerate(cells):
        tfi = float(probs[idx])
        scored = cell.copy()
        scored.setdefault("prior_failure_score", 0.0)
        scored["region"] = region
        scored["tfi"] = round(tfi, 4)
        scored["rain_threshold_calibrated"] = threshold(tfi)
        scored["regime"] = regime(tfi)
        updated.append(scored)

    by_regime: dict[str, int] = {}
    for cell in updated:
        key = cell["regime"]
        by_regime[key] = by_regime.get(key, 0) + 1

    print(f"\nTransfer model applied to {region}:")
    for key in ["CRITICAL", "HIGH", "ELEVATED", "WATCH", "STABLE"]:
        count = by_regime.get(key, 0)
        print(f"  {key:<10} {count:5d} cells ({(100 * count / len(updated)):.1f}%)")

    top = sorted(updated, key=lambda row: row["tfi"], reverse=True)[:10]
    print(f"\nTop 10 highest-risk cells in {region}:")
    for cell in top:
        print(
            f"  ({cell['lat']:.4f}, {cell['lon']:.4f}) "
            f"TFI={cell['tfi']:.4f} [{cell['regime']}] "
            f"threshold={cell['rain_threshold_calibrated']} mm/hr"
        )

    model_meta = western.get("model_v5") or {}
    output = {
        "region": region,
        "pilot_area": terrain.get("pilot_area") or region.replace("_", " ").title(),
        "bbox": terrain.get("bbox"),
        "n_cells": len(updated),
        "model_source": "v5 transfer model trained on western NC Helene data",
        "validation_note": (
            "Transfer model — not trained on local failure data yet. "
            "Use for terrain susceptibility until Tennessee/Virginia validation inventory is ingested."
        ),
        "transfer_defaults": {
            "missing_features_default_to_zero": [feature for feature in features if feature not in updated[0]],
            "prior_failure_score": "0.0 outside Helene training inventory unless local failures are added",
        },
        "model_v5": {
            **model_meta,
            "transfer_region_percentiles": {
                "p75": round(float(p75), 4),
                "p85": round(float(p85), 4),
                "p90": round(float(p90), 4),
                "p95": round(float(p95), 4),
            },
        },
        "calibration_transfer": {
            "method": "regional percentiles from transfer-model TFI distribution",
            "thresholds_mm_hr": {
                "top_5pct": 10,
                "top_10pct": 15,
                "top_15pct": 20,
                "top_25pct": 25,
                "background": 35,
            },
        },
        "computed": datetime.now(timezone.utc).isoformat(),
        "regime_summary": by_regime,
        "cells": updated,
    }

    with output_path.open("w") as f:
        json.dump(output, f)
    print(f"\nSaved transfer model output to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
