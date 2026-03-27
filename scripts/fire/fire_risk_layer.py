#!/usr/bin/env python3
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = ROOT / "data" / "fire"

TFI_CANDIDATES = [
    ROOT / "data" / "holler_siren" / "tfi_v5_western_nc.json",
    ROOT / "data" / "holler_siren" / "tfi_v5_yancey_mitchell.json",
    ROOT / "data" / "holler_siren" / "tfi_calibrated_yancey_mitchell.json",
]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _pick_tfi_source() -> Path:
    for path in TFI_CANDIDATES:
        if path.exists():
            return path
    raise FileNotFoundError("No Holler Siren terrain file found")


def _best_tfi(cell: dict) -> float:
    for key in ("tfi_v5", "tfi_v4", "tfi_learned", "tfi_v2", "tfi_v1", "tfi"):
        value = cell.get(key)
        if value is not None:
            return float(value)
    return 0.5


def _best_regime(cell: dict) -> str:
    for key in ("regime_v5", "regime_v4", "regime_learned", "regime_v2", "regime_v1", "regime"):
        value = cell.get(key)
        if value:
            return str(value)
    return "UNKNOWN"


def _float_or_zero(value) -> float:
    try:
        if value in (None, ""):
            return 0.0
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def sw_facing_score(pct_se_facing: float) -> float:
    return min(max(pct_se_facing / 100.0, 0.0), 1.0)


def helene_debris_score(prior_failure_score: float) -> float:
    return min(max(prior_failure_score * 2.0, 0.0), 1.0)


def compute_fire_risk(cell: dict) -> float:
    slope_component = min(_float_or_zero(cell.get("slope_mean")) / 45.0, 1.0) * 0.30
    aspect_component = sw_facing_score(_float_or_zero(cell.get("pct_se_facing"))) * 0.20
    debris_component = helene_debris_score(_float_or_zero(cell.get("prior_failure_score"))) * 0.25
    forest_loss_component = min(_float_or_zero(cell.get("pct_forest_loss")) / 100.0, 1.0) * 0.15

    twi = _float_or_zero(cell.get("twi_mean")) or 5.0
    twi_component = max(0.0, (8.0 - twi) / 8.0) * 0.10

    fire_risk = slope_component + aspect_component + debris_component + forest_loss_component + twi_component
    return min(fire_risk, 1.0)


def classify_fire_regime(fire_risk: float) -> str:
    if fire_risk > 0.60:
        return "EXTREME"
    if fire_risk > 0.45:
        return "HIGH"
    if fire_risk > 0.30:
        return "MODERATE"
    return "LOW"


def main() -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("=== FIRE RISK LAYER - HOLLER SIREN INTEGRATION ===")
    tfi_path = _pick_tfi_source()
    tfi_data = _load_json(tfi_path)
    cells = tfi_data["cells"]
    print(f"Terrain cells loaded: {len(cells)} from {tfi_path.name}")

    firms_data = _load_json(OUTPUT_DIR / "firms_results.json") if (OUTPUT_DIR / "firms_results.json").exists() else {}
    mtbs_data = _load_json(OUTPUT_DIR / "mtbs_historical.json") if (OUTPUT_DIR / "mtbs_historical.json").exists() else {}
    current_wx = _load_json(OUTPUT_DIR / "current_wx.json") if (OUTPUT_DIR / "current_wx.json").exists() else {}

    active_fires = firms_data.get("fires") or []
    historical_fires = mtbs_data.get("fires") or []

    print(f"Active fires: {len(active_fires)}")
    print(f"Historical fire events: {len(historical_fires)}")

    updated_cells = []
    by_fire_regime: dict[str, int] = {}

    for cell in cells:
        fire_risk = round(compute_fire_risk(cell), 4)
        fire_regime = classify_fire_regime(fire_risk)
        by_fire_regime[fire_regime] = by_fire_regime.get(fire_regime, 0) + 1

        landslide_tfi = round(_best_tfi(cell), 4)
        landslide_regime = _best_regime(cell)
        double_threat = landslide_regime in {"CRITICAL", "HIGH"} and fire_risk > 0.45

        updated = dict(cell)
        updated["fire_risk"] = fire_risk
        updated["fire_regime"] = fire_regime
        updated["double_threat"] = double_threat
        updated["landslide_tfi"] = landslide_tfi
        updated["landslide_regime"] = landslide_regime
        updated_cells.append(updated)

    print("\nFire regime distribution:")
    for regime in ("EXTREME", "HIGH", "MODERATE", "LOW"):
        count = by_fire_regime.get(regime, 0)
        pct = (100.0 * count / len(updated_cells)) if updated_cells else 0.0
        print(f"  {regime:<12}: {count:5d} ({pct:.1f}%)")

    double_threats = [cell for cell in updated_cells if cell["double_threat"]]
    double_threats.sort(key=lambda cell: cell["fire_risk"] + cell["landslide_tfi"], reverse=True)

    print(f"\nDouble-threat cells (high landslide AND high fire): {len(double_threats)}")
    print("\nTop 10 double-threat locations:")
    print(f"{'Lat':>8} {'Lon':>9} {'FireRisk':>9} {'LsRisk':>8} {'FireReg':<10} {'LsReg'}")
    print("-" * 65)
    for cell in double_threats[:10]:
        print(
            f"{cell['lat']:>8.3f} {cell['lon']:>9.3f} "
            f"{cell['fire_risk']:>9.4f} {cell['landslide_tfi']:>8.4f} "
            f"{cell['fire_regime']:<10} {cell['landslide_regime']}"
        )

    output = {
        "pilot_area": tfi_data.get("pilot_area", "Western NC"),
        "terrain_source": tfi_path.name,
        "n_cells": len(updated_cells),
        "fire_regime_summary": by_fire_regime,
        "double_threat_cells": len(double_threats),
        "helene_connection": (
            "Cells near Helene failures carry elevated deadwood fuel load. "
            "The same steep southeast-facing terrain flagged by Holler Siren now also ranks highest for fire spread."
        ),
        "data_layers": [
            "slope",
            "aspect",
            "helene_debris",
            "forest_loss",
            "twi_inverse",
        ],
        "current_weather": current_wx,
        "active_fire_count": len(active_fires),
        "historical_fire_count": len(historical_fires),
        "computed": _now_iso(),
        "top_double_threats": [
            {
                "lat": cell["lat"],
                "lon": cell["lon"],
                "fire_risk": cell["fire_risk"],
                "landslide_tfi": cell["landslide_tfi"],
                "fire_regime": cell["fire_regime"],
                "landslide_regime": cell["landslide_regime"],
            }
            for cell in double_threats[:20]
        ],
        "cells": updated_cells,
    }

    out_path = OUTPUT_DIR / "fire_risk_overlay.json"
    out_path.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")

    print(f"\nSaved fire risk overlay to {out_path}")
    print(f"File size: {out_path.stat().st_size / 1e3:.0f} KB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
