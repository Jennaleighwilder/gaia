#!/usr/bin/env python3
from __future__ import annotations

import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


HOLLER_SIREN_LEARNED = ROOT / "data" / "holler_siren" / "tfi_learned_yancey_mitchell.json"
HOLLER_SIREN_CALIBRATED = ROOT / "data" / "holler_siren" / "tfi_calibrated_yancey_mitchell.json"
HOLLER_SIREN_BASE = ROOT / "data" / "holler_siren" / "tfi_yancey_mitchell.json"
RUNS_DIR = ROOT / "runs"

BEST_VALIDATED_AUC = 0.654
HELENE_FAILURE_COUNT = 378


def _load_holler_siren_data() -> tuple[dict, list[dict], Path]:
    if HOLLER_SIREN_CALIBRATED.exists():
        source = HOLLER_SIREN_CALIBRATED
    elif HOLLER_SIREN_LEARNED.exists():
        source = HOLLER_SIREN_LEARNED
    else:
        source = HOLLER_SIREN_BASE
    with source.open() as f:
        data = json.load(f)
    return data, data["cells"], source


def _best_threshold(cell: dict) -> float:
    for key in (
        "rain_threshold_calibrated",
        "rain_threshold_learned",
        "rain_threshold_v2",
        "rain_threshold_v1",
        "rain_threshold_mm_hr",
    ):
        value = cell.get(key)
        if value is not None:
            return float(value)
    return 20.0


def _best_tfi(cell: dict) -> float:
    for key in ("tfi_learned", "tfi_v2", "tfi_v1", "tfi"):
        value = cell.get(key)
        if value is not None:
            return float(value)
    return 0.5


def _best_regime(cell: dict) -> str:
    for key in ("regime_learned", "regime_v2", "regime_v1", "regime"):
        value = cell.get(key)
        if value:
            return str(value)
    return "UNKNOWN"


def holler_siren_alert(
    rainfall_mm_hr: float,
    bbox: tuple[float, float, float, float] | None = None,
    antecedent_sat_pct: float = 0.0,
    duration_hr: float = 6.0,
) -> dict:
    tfi_data, cells, source_path = _load_holler_siren_data()

    sat_factor = max(0.5, 1.0 - (antecedent_sat_pct / 100.0) * 0.5)
    effective_rain = rainfall_mm_hr / sat_factor

    search_cells = cells
    if bbox:
        lat_min, lon_min, lat_max, lon_max = bbox
        search_cells = [
            cell
            for cell in cells
            if lat_min <= cell["lat"] <= lat_max and lon_min <= cell["lon"] <= lon_max
        ]

    at_risk: list[dict] = []
    calib = tfi_data.get("calibration") or {}
    anchors = calib.get("anchors") or {}
    p75 = float(anchors.get("p75", 0.75))
    p85 = float(anchors.get("p85", 0.85))
    p95 = float(anchors.get("p95", 0.95))

    for cell in search_cells:
        threshold = _best_threshold(cell)
        if effective_rain < threshold:
            continue

        tfi = _best_tfi(cell)
        if tfi >= p95:
            regime = "CRITICAL"
        elif tfi >= p85:
            regime = "HIGH"
        elif tfi >= p75:
            regime = "ELEVATED"
        else:
            regime = _best_regime(cell)
        margin = effective_rain - threshold
        at_risk.append(
            {
                "lat": cell["lat"],
                "lon": cell["lon"],
                "tfi": round(tfi, 3),
                "regime": regime,
                "rain_threshold": round(threshold, 1),
                "effective_rain": round(effective_rain, 1),
                "margin_over_threshold": round(margin, 1),
                "slope_mean": cell.get("slope_mean", 0),
                "pct_se_facing": cell.get("pct_se_facing", 0),
                "road_dist_km": cell.get("road_dist_km"),
            }
        )

    at_risk.sort(key=lambda row: (row["margin_over_threshold"], row["tfi"]), reverse=True)

    n_top5 = sum(1 for row in at_risk if row["tfi"] >= p95)
    n_top15 = sum(1 for row in at_risk if row["tfi"] >= p85)
    n_top30 = sum(1 for row in at_risk if row["tfi"] >= p75)
    if n_top5 >= 3 and effective_rain >= 25.0:
        alert_level = "CRITICAL"
    elif n_top15 >= 5 and effective_rain >= 20.0:
        alert_level = "HIGH"
    elif n_top30 >= 5 and effective_rain >= 15.0:
        alert_level = "ELEVATED"
    elif at_risk and effective_rain >= 10.0:
        alert_level = "WATCH"
    else:
        alert_level = "CLEAR"

    model_meta = tfi_data.get("model") or {}
    active_validation = model_meta.get("cv_auc") or BEST_VALIDATED_AUC

    return {
        "alert_level": alert_level,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "inputs": {
            "rainfall_mm_hr": rainfall_mm_hr,
            "antecedent_sat_pct": antecedent_sat_pct,
            "effective_rain_mm_hr": round(effective_rain, 1),
            "duration_hr": duration_hr,
            "bbox": bbox,
        },
        "summary": {
            "cells_at_risk": len(at_risk),
            "critical_cells": n_top5,
            "high_cells": n_top15,
            "elevated_cells": n_top30,
        },
        "top_hollows": at_risk[:20],
        "pilot_area": tfi_data.get("pilot_area", "Yancey + Mitchell NC"),
        "data_source": source_path.name,
        "validation": {
            "best_validated_auc": BEST_VALIDATED_AUC,
            "active_model_auc": round(float(active_validation), 3),
            "helene_failures": HELENE_FAILURE_COUNT,
        },
    }


def format_alert(result: dict) -> str:
    level = result["alert_level"]
    inp = result["inputs"]
    summ = result["summary"]

    lines = [
        "=" * 60,
        f"HOLLER SIREN - {level} TERRAIN FAILURE RISK",
        f"{result['pilot_area']}",
        f"{result['timestamp'][:19]} UTC",
        "=" * 60,
        f"Rainfall:  {inp['rainfall_mm_hr']} mm/hr forecast",
    ]

    if inp["antecedent_sat_pct"] > 0:
        lines.append(
            f"Soil:      {inp['antecedent_sat_pct']}% saturated "
            f"(effective: {inp['effective_rain_mm_hr']} mm/hr)"
        )

    lines += [
        "",
        f"AT-RISK TERRAIN CELLS: {summ['cells_at_risk']}",
        f"  CRITICAL: {summ['critical_cells']}",
        f"  HIGH:     {summ['high_cells']}",
        "",
        "TOP VULNERABLE LOCATIONS:",
        f"{'Lat':>8} {'Lon':>9} {'TFI':>6} {'Regime':<12} {'Rain(mm/hr)':>12} {'Margin':>8}",
        "-" * 60,
    ]

    for hollow in result["top_hollows"][:10]:
        lines.append(
            f"{hollow['lat']:>8.3f} {hollow['lon']:>9.3f} "
            f"{hollow['tfi']:>6.3f} {hollow['regime']:<12} "
            f"{hollow['rain_threshold']:>12.1f} {hollow['margin_over_threshold']:>+8.1f}"
        )

    lines += ["", "RECOMMENDED ACTION:"]
    if level == "CRITICAL":
        lines += [
            "  IMMEDIATE - Contact county OEM for pre-positioned welfare checks",
            "  Priority hollows above have rain thresholds already exceeded",
            "  Debris flow risk is high on steep southeast-facing slopes",
        ]
    elif level == "HIGH":
        lines += [
            "  ALERT - Issue shelter-in-place guidance for identified hollows",
            "  Monitor rainfall rate closely for threshold exceedance expansion",
        ]
    elif level == "ELEVATED":
        lines += [
            "  WATCH - Conditions approaching threshold in identified cells",
            "  Pre-position resources and monitor closely",
        ]
    else:
        lines.append("  No immediate terrain failure risk at current forecast.")

    lines += [
        "",
        "Holler Siren v1.0 | The Forgotten Code Research Institute",
        f"Best validation: AUC {BEST_VALIDATED_AUC:.3f} vs {HELENE_FAILURE_COUNT} Helene failures",
        "=" * 60,
    ]
    return "\n".join(lines)


def _print_scenario(title: str, result: dict) -> None:
    print(title)
    print(format_alert(result))
    print()


def main() -> int:
    tfi_data, cells, _ = _load_holler_siren_data()
    print(f"Holler Siren loaded: {len(cells)} terrain cells")
    print(f"Pilot area: {tfi_data.get('pilot_area', 'Yancey + Mitchell NC')}")
    print()
    print("=== HOLLER SIREN ALERT SCENARIOS ===\n")

    result_peak = holler_siren_alert(rainfall_mm_hr=50.0, antecedent_sat_pct=80.0, duration_hr=12.0)
    print("SCENARIO 0: Helene peak (50mm/hr, 80% soil saturation)")
    print(f"Alert level: {result_peak['alert_level']}")
    print(f"Cells at risk: {result_peak['summary']['cells_at_risk']}")
    print()

    result1 = holler_siren_alert(rainfall_mm_hr=30.0, antecedent_sat_pct=80.0, duration_hr=12.0)
    _print_scenario("SCENARIO 1: Helene average (30mm/hr, 80% soil saturation)", result1)

    result2 = holler_siren_alert(rainfall_mm_hr=15.0, antecedent_sat_pct=30.0, duration_hr=6.0)
    print("SCENARIO 2: Moderate rain (15mm/hr, 30% soil saturation)")
    print(f"Alert level: {result2['alert_level']}")
    print(f"Cells at risk: {result2['summary']['cells_at_risk']}")
    print()

    result3 = holler_siren_alert(rainfall_mm_hr=5.0, antecedent_sat_pct=20.0, duration_hr=6.0)
    print("SCENARIO 3: Light rain (5mm/hr, 20% soil saturation)")
    print(f"Alert level: {result3['alert_level']}")
    print(f"Cells at risk: {result3['summary']['cells_at_risk']}")
    print()

    RUNS_DIR.mkdir(exist_ok=True)
    with (RUNS_DIR / "holler_siren_scenarios.json").open("w") as f:
        json.dump(
            {
                "helene_peak": result_peak,
                "helene_like": result1,
                "moderate": result2,
                "light": result3,
            },
            f,
            indent=2,
        )
    print(f"Saved scenarios to {RUNS_DIR / 'holler_siren_scenarios.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
