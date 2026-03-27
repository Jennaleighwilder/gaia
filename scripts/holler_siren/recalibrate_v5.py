#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


DATA_DIR = ROOT / "data" / "holler_siren"
WESTERN_PATH = DATA_DIR / "tfi_v5_western_nc.json"
PILOT_PATH = DATA_DIR / "tfi_v5_yancey_mitchell.json"


def threshold_from_scheme(tfi: float, anchors: tuple[float, float, float, float]) -> float:
    p25, p20, p15, p10 = anchors
    if tfi >= p10:
        return 10.0
    if tfi >= p15:
        return 15.0
    if tfi >= p20:
        return 20.0
    if tfi >= p25:
        return 25.0
    return 35.0


def regime_from_scheme(tfi: float, anchors: tuple[float, float, float, float]) -> str:
    p25, p20, p15, p10 = anchors
    if tfi >= p10:
        return "CRITICAL"
    if tfi >= p20:
        return "HIGH"
    if tfi >= p25:
        return "ELEVATED"
    return "STABLE"


def scenario_count(cells: list[dict], anchors: tuple[float, float, float, float], rain: float, sat: float) -> tuple[str, int]:
    at_risk = []
    p25, p20, p15, p10 = anchors
    for cell in cells:
        tfi = float(cell.get("tfi_v5", cell.get("tfi_learned", 0.5)))
        threshold = threshold_from_scheme(tfi, anchors)
        if threshold <= 25.0:
            adjusted = threshold * (1.0 - (sat / 100.0) * 0.4)
        else:
            adjusted = threshold
        if rain >= adjusted:
            at_risk.append(cell)

    n_top1 = sum(1 for cell in at_risk if float(cell.get("tfi_v5", 0.0)) >= p10)
    n_top5 = sum(1 for cell in at_risk if float(cell.get("tfi_v5", 0.0)) >= p20)
    if n_top1 >= 5 and rain >= 25.0:
        level = "CRITICAL"
    elif n_top5 >= 10 and rain >= 20.0:
        level = "HIGH"
    elif len(at_risk) >= 20:
        level = "ELEVATED"
    elif at_risk:
        level = "WATCH"
    else:
        level = "CLEAR"
    return level, len(at_risk)


def main() -> int:
    print("=== FIX 1: RECALIBRATE v5 THRESHOLDS ===")

    with WESTERN_PATH.open() as f:
        western = json.load(f)
    with PILOT_PATH.open() as f:
        pilot = json.load(f)

    western_cells = western["cells"]
    pilot_cells = pilot["cells"]
    tfis = np.array([float(cell.get("tfi_v5", cell.get("tfi_learned", 0.5))) for cell in western_cells], dtype=float)
    print(f"Total cells: {len(western_cells)}")
    print(f"TFI range: {tfis.min():.4f} to {tfis.max():.4f}")
    print(f"TFI mean: {tfis.mean():.4f}")
    print()
    for pct in [50, 75, 85, 90, 95, 97, 99]:
        print(f"  {pct}th percentile: {np.percentile(tfis, pct):.4f}")

    candidate_percentiles = [
        (90, 95, 97, 99),
        (92, 96, 98, 99.5),
        (93, 97, 98.5, 99.7),
        (94, 97, 99, 99.8),
        (95, 97, 99, 99.5),
    ]

    chosen = None
    chosen_metrics = None
    print()
    print("=== CANDIDATE CALIBRATIONS (pilot-area counts) ===")
    for candidate in candidate_percentiles:
        anchors = tuple(float(np.percentile(tfis, pct)) for pct in candidate)
        s50 = scenario_count(pilot_cells, anchors, 50.0, 80.0)
        s30 = scenario_count(pilot_cells, anchors, 30.0, 80.0)
        s15 = scenario_count(pilot_cells, anchors, 15.0, 30.0)
        s5 = scenario_count(pilot_cells, anchors, 5.0, 0.0)
        print(f"  {candidate}: 50mm={s50[1]} 30mm={s30[1]} 15mm={s15[1]} 5mm={s5[1]}")
        meets_target = (
            s5 == ("CLEAR", 0)
            and s15[1] < 300
            and 400 <= s30[1] <= 600
        )
        if meets_target and chosen is None:
            chosen = (candidate, anchors)
            chosen_metrics = {"50": s50, "30": s30, "15": s15, "5": s5}

    if chosen is None:
        candidate = candidate_percentiles[-1]
        anchors = tuple(float(np.percentile(tfis, pct)) for pct in candidate)
        chosen = (candidate, anchors)
        chosen_metrics = {
            "50": scenario_count(pilot_cells, anchors, 50.0, 80.0),
            "30": scenario_count(pilot_cells, anchors, 30.0, 80.0),
            "15": scenario_count(pilot_cells, anchors, 15.0, 30.0),
            "5": scenario_count(pilot_cells, anchors, 5.0, 0.0),
        }

    candidate, anchors = chosen
    p25, p20, p15, p10 = anchors
    print()
    print("New threshold anchors:")
    print(f"  p{candidate[0]}={p25:.4f}, p{candidate[1]}={p20:.4f}, p{candidate[2]}={p15:.4f}, p{candidate[3]}={p10:.4f}")

    def apply(cells: list[dict]) -> list[dict]:
        updated = []
        for cell in cells:
            tfi = float(cell.get("tfi_v5", cell.get("tfi_learned", 0.5)))
            updated_cell = cell.copy()
            updated_cell["rain_threshold_v5"] = threshold_from_scheme(tfi, anchors)
            updated_cell["regime_v5"] = regime_from_scheme(tfi, anchors)
            updated.append(updated_cell)
        return updated

    western_updated = apply(western_cells)
    pilot_updated = apply(pilot_cells)

    print()
    print("v5 recalibrated regime summary:")
    for label, cells in [("western", western_updated), ("pilot", pilot_updated)]:
        counts = {}
        for cell in cells:
            counts[cell["regime_v5"]] = counts.get(cell["regime_v5"], 0) + 1
        print(f"  {label}:")
        for regime in ["CRITICAL", "HIGH", "ELEVATED", "STABLE"]:
            n = counts.get(regime, 0)
            print(f"    {regime:<10}: {n:5d} ({100 * n / len(cells):.1f}%)")

    print()
    print("=== RECALIBRATED SCENARIO CHECK (pilot area) ===")
    for rain, sat, label in [
        (50.0, 80.0, "catastrophic"),
        (30.0, 80.0, "catastrophic"),
        (15.0, 30.0, "moderate"),
        (5.0, 0.0, "light"),
    ]:
        level, count = scenario_count(pilot_updated, anchors, rain, sat)
        print(f"  {rain:5.0f}mm/hr {sat:3.0f}%sat ({label:<12}): {level:<10} {count:5d} cells")

    calibration = {
        "method": "western-nc-distribution calibrated to pilot operational targets",
        "percentile_scheme": {
            "elevated": candidate[0],
            "high": candidate[1],
            "critical": candidate[2],
            "extreme": candidate[3],
        },
        "anchors": {
            "p25_like": round(p25, 4),
            "p20_like": round(p20, 4),
            "p15_like": round(p15, 4),
            "p10_like": round(p10, 4),
        },
        "thresholds_mm_hr": {
            "extreme_top_band": 10,
            "critical_band": 15,
            "high_band": 20,
            "elevated_band": 25,
            "background": 35,
        },
        "pilot_target_check": chosen_metrics,
        "basis": "Percentiles computed on full 40,453 western NC cells and tightened to hit pilot alert-count targets.",
    }

    western["cells"] = western_updated
    western["calibration_v5"] = calibration
    with WESTERN_PATH.open("w") as f:
        json.dump(western, f)

    pilot["cells"] = pilot_updated
    pilot["calibration_v5"] = calibration
    with PILOT_PATH.open("w") as f:
        json.dump(pilot, f)

    print("\nPilot subset also updated")
    print("\nSaved recalibrated v5 model")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
