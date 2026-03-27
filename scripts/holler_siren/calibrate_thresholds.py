#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


INPUT_PATH = ROOT / "data" / "holler_siren" / "tfi_learned_yancey_mitchell.json"
OUTPUT_PATH = ROOT / "data" / "holler_siren" / "tfi_calibrated_yancey_mitchell.json"


def calibrated_threshold(tfi: float, p75: float, p85: float, p90: float, p95: float) -> float:
    if tfi >= p95:
        return 10.0
    if tfi >= p90:
        return 15.0
    if tfi >= p85:
        return 20.0
    if tfi >= p75:
        return 25.0
    return 35.0


def alert_calibrated(cells: list[dict], rainfall_mm_hr: float, antecedent_sat_pct: float, p75: float, p85: float, p95: float):
    sat_factor = max(0.5, 1.0 - (antecedent_sat_pct / 100.0) * 0.5)
    effective = rainfall_mm_hr / sat_factor
    at_risk = [cell for cell in cells if effective >= cell["rain_threshold_calibrated"]]
    at_risk.sort(key=lambda cell: cell.get("tfi_learned", cell.get("tfi", 0.0)), reverse=True)

    n_top5 = sum(1 for cell in at_risk if cell.get("tfi_learned", cell.get("tfi", 0.0)) >= p95)
    n_top15 = sum(1 for cell in at_risk if cell.get("tfi_learned", cell.get("tfi", 0.0)) >= p85)
    n_top30 = sum(1 for cell in at_risk if cell.get("tfi_learned", cell.get("tfi", 0.0)) >= p75)

    if n_top5 >= 3 and effective >= 25.0:
        level = "CRITICAL"
    elif n_top15 >= 5 and effective >= 20.0:
        level = "HIGH"
    elif n_top30 >= 5 and effective >= 15.0:
        level = "ELEVATED"
    elif at_risk and effective >= 10.0:
        level = "WATCH"
    else:
        level = "CLEAR"
    return level, len(at_risk), n_top5, n_top15, n_top30


def main() -> int:
    with INPUT_PATH.open() as f:
        data = json.load(f)
    cells = data["cells"]

    tfis = np.array([cell.get("tfi_learned", cell.get("tfi", 0.5)) for cell in cells], dtype=float)
    p75 = float(np.percentile(tfis, 75))
    p85 = float(np.percentile(tfis, 85))
    p90 = float(np.percentile(tfis, 90))
    p95 = float(np.percentile(tfis, 95))

    print("TFI percentile anchors:")
    print(f"  75th pct: {p75:.4f}")
    print(f"  85th pct: {p85:.4f}")
    print(f"  90th pct: {p90:.4f}")
    print(f"  95th pct: {p95:.4f}")
    print()

    updated = []
    for cell in cells:
        tfi = float(cell.get("tfi_learned", cell.get("tfi", 0.5)))
        threshold = calibrated_threshold(tfi, p75, p85, p90, p95)
        updated_cell = cell.copy()
        updated_cell["rain_threshold_calibrated"] = threshold
        updated.append(updated_cell)

    thresholds = [cell["rain_threshold_calibrated"] for cell in updated]
    print("Calibrated threshold distribution:")
    threshold_distribution: dict[str, dict[str, float]] = {}
    for val in [10, 15, 20, 25, 35]:
        count = sum(1 for threshold in thresholds if threshold == val)
        pct = count / len(thresholds) * 100.0
        print(f"  {val:5.0f} mm/hr: {count:5d} cells ({pct:.1f}%)")
        threshold_distribution[str(val)] = {"cells": count, "pct": round(pct, 2)}

    print()
    print("=== CALIBRATED ALERT SCENARIOS ===")
    scenarios = [
        (50.0, 80.0, "Helene peak (50mm/hr, 80% sat)"),
        (30.0, 80.0, "Helene average (30mm/hr, 80% sat)"),
        (25.0, 50.0, "Severe event (25mm/hr, 50% sat)"),
        (15.0, 30.0, "Moderate (15mm/hr, 30% sat)"),
        (10.0, 20.0, "Light (10mm/hr, 20% sat)"),
        (5.0, 0.0, "Drizzle (5mm/hr)"),
    ]
    scenario_results = {}
    for rain, sat, label in scenarios:
        level, n_risk, n_top5, n_top15, n_top30 = alert_calibrated(updated, rain, sat, p75, p85, p95)
        print(f"  {label:<40}: {level:<10} {n_risk:5d} cells (top5%={n_top5}, top15%={n_top15})")
        scenario_results[label] = {
            "rainfall_mm_hr": rain,
            "antecedent_sat_pct": sat,
            "alert_level": level,
            "cells_at_risk": n_risk,
            "top_5pct_cells": n_top5,
            "top_15pct_cells": n_top15,
            "top_30pct_cells": n_top30,
        }

    data["cells"] = updated
    data["calibration"] = {
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
            "Helene peak intensity ~50mm/hr. "
            "NC mountain severe rain 25-35mm/hr. "
            "Slope failures typically need 25mm/hr sustained 3hr+."
        ),
        "scenario_results": scenario_results,
        "threshold_distribution": threshold_distribution,
    }

    with OUTPUT_PATH.open("w") as f:
        json.dump(data, f)
    print(f"\nSaved calibrated TFI to {OUTPUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
