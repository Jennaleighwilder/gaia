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
HOLLER_SIREN_V4 = ROOT / "data" / "holler_siren" / "tfi_v4_yancey_mitchell.json"
HOLLER_SIREN_V5_WESTERN = ROOT / "data" / "holler_siren" / "tfi_v5_western_nc.json"
HOLLER_SIREN_V5 = ROOT / "data" / "holler_siren" / "tfi_v5_yancey_mitchell.json"
HOLLER_SIREN_BASE = ROOT / "data" / "holler_siren" / "tfi_yancey_mitchell.json"
RUNS_DIR = ROOT / "runs"
DEFAULT_PILOT_BBOX = (35.82, -82.38, 36.12, -81.82)

BEST_VALIDATED_AUC = 0.654
HELENE_FAILURE_COUNT = 378


def _load_holler_siren_data() -> tuple[dict, list[dict], Path]:
    if HOLLER_SIREN_V5_WESTERN.exists():
        source = HOLLER_SIREN_V5_WESTERN
    elif HOLLER_SIREN_V5.exists():
        source = HOLLER_SIREN_V5
    elif HOLLER_SIREN_V4.exists():
        source = HOLLER_SIREN_V4
    elif HOLLER_SIREN_CALIBRATED.exists():
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
        "rain_threshold_v5",
        "rain_threshold_v4",
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


def holler_siren_alert(
    rainfall_mm_hr: float,
    bbox: tuple[float, float, float, float] | None = None,
    antecedent_sat_pct: float = 0.0,
    duration_hr: float = 6.0,
) -> dict:
    tfi_data, cells, source_path = _load_holler_siren_data()
    helene_failures = int(tfi_data.get("helene_count", HELENE_FAILURE_COUNT))

    if bbox is None and source_path == HOLLER_SIREN_V5_WESTERN:
        bbox = DEFAULT_PILOT_BBOX

    search_cells = cells
    if bbox:
        lat_min, lon_min, lat_max, lon_max = bbox
        search_cells = [
            cell
            for cell in cells
            if lat_min <= cell["lat"] <= lat_max and lon_min <= cell["lon"] <= lon_max
        ]

    at_risk: list[dict] = []
    calib = tfi_data.get("calibration_v5") or tfi_data.get("calibration") or {}
    anchors = calib.get("anchors") or {}
    p_elev = float(anchors.get("p25_like", anchors.get("p75", 0.75)))
    p_high = float(anchors.get("p20_like", anchors.get("p85", 0.85)))
    p_crit = float(anchors.get("p15_like", anchors.get("p95", 0.95)))
    p_extreme = float(anchors.get("p10_like", anchors.get("p99", 0.99)))

    for cell in search_cells:
        threshold = _best_threshold(cell)
        if threshold <= 25.0:
            sat_reduction = min(0.4, (antecedent_sat_pct / 100.0) * 0.4)
            adjusted_threshold = threshold * (1.0 - sat_reduction)
        else:
            sat_reduction = 0.0
            adjusted_threshold = threshold
        if rainfall_mm_hr < adjusted_threshold:
            continue

        tfi = _best_tfi(cell)
        if tfi >= p_extreme:
            regime = "CRITICAL"
        elif tfi >= p_high:
            regime = "HIGH"
        elif tfi >= p_elev:
            regime = "ELEVATED"
        else:
            regime = _best_regime(cell)
        margin = rainfall_mm_hr - adjusted_threshold
        at_risk.append(
            {
                "lat": cell["lat"],
                "lon": cell["lon"],
                "tfi": round(tfi, 3),
                "regime": regime,
                "rain_threshold": round(adjusted_threshold, 1),
                "baseline_rain_threshold": round(threshold, 1),
                "threshold_reduction_pct": round(sat_reduction * 100.0, 1),
                "effective_rain": round(rainfall_mm_hr, 1),
                "margin_over_threshold": round(margin, 1),
                "slope_mean": cell.get("slope_mean", 0),
                "pct_se_facing": cell.get("pct_se_facing", 0),
                "road_dist_km": cell.get("road_dist_km"),
                "soil_hydgrp": cell.get("soil_hydgrp"),
                "geology_type": cell.get("geology_type"),
            }
        )

    at_risk.sort(key=lambda row: (row["margin_over_threshold"], row["tfi"]), reverse=True)

    n_top1 = sum(1 for row in at_risk if row["tfi"] >= p_extreme)
    n_top5 = sum(1 for row in at_risk if row["tfi"] >= p_high)
    n_top10 = sum(1 for row in at_risk if row["tfi"] >= p_elev)
    if n_top1 >= 5 and rainfall_mm_hr >= 25.0:
        alert_level = "CRITICAL"
    elif n_top5 >= 10 and rainfall_mm_hr >= 20.0:
        alert_level = "HIGH"
    elif len(at_risk) >= 20:
        alert_level = "ELEVATED"
    elif at_risk:
        alert_level = "WATCH"
    else:
        alert_level = "CLEAR"

    model_meta = tfi_data.get("model_v5") or tfi_data.get("model_v4") or tfi_data.get("model") or {}
    active_validation = float(model_meta.get("cv_auc") or BEST_VALIDATED_AUC)
    final_validation = model_meta.get("final_auc")
    best_validated_auc = max(
        BEST_VALIDATED_AUC,
        active_validation,
        float(final_validation) if final_validation is not None else BEST_VALIDATED_AUC,
    )

    return {
        "alert_level": alert_level,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "inputs": {
            "rainfall_mm_hr": rainfall_mm_hr,
            "antecedent_sat_pct": antecedent_sat_pct,
            "duration_hr": duration_hr,
            "bbox": bbox,
        },
        "summary": {
            "cells_at_risk": len(at_risk),
            "critical_cells": n_top1,
            "high_cells": n_top5,
            "elevated_cells": n_top10,
        },
        "top_hollows": at_risk[:20],
        "pilot_area": tfi_data.get("pilot_area", "Yancey + Mitchell NC"),
        "data_source": source_path.name,
        "validation": {
            "best_validated_auc": round(float(best_validated_auc), 3),
            "active_model_auc": round(float(active_validation), 3),
            "helene_failures": helene_failures,
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
            "(threshold reduction applied only to top-risk terrain)"
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
        f"Best validation: AUC {result['validation']['best_validated_auc']:.3f} vs {result['validation']['helene_failures']} Helene failures",
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
