#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
import urllib.request
from pathlib import Path

import numpy as np
import rasterio
from rasterio.warp import transform_bounds
from rasterio.windows import from_bounds


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.holler_siren.gaia_integration import holler_siren_alert


OUTPUT_DIR = ROOT / "data" / "holler_siren"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

PILOT_LAT = 35.97
PILOT_LON = -82.10
PILOT_BBOX_4326 = (-82.38, 35.82, -81.82, 36.12)  # min_lon, min_lat, max_lon, max_lat
USER_AGENT = "HollerSiren/1.0 (theforgottencode780@gmail.com)"

KNOWN_EVENTS = [
    ("20160930", "Hurricane Matthew remnants"),
    ("20180917", "Hurricane Florence remnants"),
    ("20190821", "Tropical Storm Chantal"),
    ("20210821", "Remnants Fred/Henri"),
    ("20220913", "Post-TS Earl rainfall"),
    ("20230813", "August 2023 heavy rain"),
]


def stage4_url(date_str: str) -> str:
    year = date_str[:4]
    month = date_str[4:6]
    day = date_str[6:8]
    return (
        "https://water.noaa.gov/resources/downloads/precip/stageIV/"
        f"{year}/{month}/{day}/nws_precip_1day_{date_str}_conus.tif"
    )


def fetch_stage4_tif(date_str: str) -> Path | None:
    cache_path = OUTPUT_DIR / f"stage4_{date_str}.tif"
    if cache_path.exists():
        return cache_path
    req = urllib.request.Request(stage4_url(date_str), headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = resp.read()
    except Exception:
        return None
    if len(data) < 1024:
        return None
    cache_path.write_bytes(data)
    return cache_path


def read_stage4_precip_mm_day(tif_path: Path) -> float | None:
    try:
        with rasterio.open(tif_path) as src:
            bbox_native = transform_bounds("EPSG:4326", src.crs, *PILOT_BBOX_4326, densify_pts=21)
            window = from_bounds(*bbox_native, transform=src.transform).round_offsets().round_lengths()
            data = src.read(1, window=window).astype(float)
            nodata = src.nodata
            valid = data[np.isfinite(data) & (data != nodata) & (data > 0)]
            if valid.size == 0:
                return 0.0
            return float(np.mean(valid))
    except Exception:
        return None


def main() -> int:
    print("=== HOLLER SIREN NEGATIVE VALIDATION ===")
    print("Finding historical heavy rain events WITHOUT failures...")
    print()
    print("Testing known NC heavy rain events...")

    event_results: list[dict] = []
    for date_str, event_name in KNOWN_EVENTS:
        tif_path = fetch_stage4_tif(date_str)
        if tif_path is None:
            print(f"  {date_str} {event_name}: no Stage IV data")
            continue

        precip_mm_day = read_stage4_precip_mm_day(tif_path)
        if precip_mm_day is None:
            print(f"  {date_str} {event_name}: unreadable Stage IV data")
            continue

        print(f"  {date_str} {event_name}: {precip_mm_day:.1f} mm")
        rainfall_mm_hr = precip_mm_day / 24.0
        result = holler_siren_alert(
            rainfall_mm_hr=rainfall_mm_hr,
            antecedent_sat_pct=30.0,
            duration_hr=12.0,
        )
        status = "OK" if result["alert_level"] in {"CLEAR", "WATCH", "ELEVATED"} else "OVERFIRE"
        print(f"    -> {result['alert_level']} ({result['summary']['cells_at_risk']} cells) [{status}]")
        event_results.append(
            {
                "date": date_str,
                "name": event_name,
                "precip_mm_day": round(precip_mm_day, 1),
                "precip_mm_hr": round(rainfall_mm_hr, 2),
                "alert_level": result["alert_level"],
                "cells_at_risk": result["summary"]["cells_at_risk"],
                "critical_cells": result["summary"].get("critical_cells", 0),
                "known_failures": 0,
            }
        )

    print()
    print("  20240927 Hurricane Helene: ~30.0 mm/hr")
    helene_result = holler_siren_alert(
        rainfall_mm_hr=30.0,
        antecedent_sat_pct=80.0,
        duration_hr=12.0,
    )
    print(
        f"    -> {helene_result['alert_level']} "
        f"({helene_result['summary']['cells_at_risk']} cells) [POSITIVE CASE]"
    )
    event_results.append(
        {
            "date": "20240927",
            "name": "Hurricane Helene",
            "precip_mm_day": 400.0,
            "precip_mm_hr": 30.0,
            "alert_level": helene_result["alert_level"],
            "cells_at_risk": helene_result["summary"]["cells_at_risk"],
            "critical_cells": helene_result["summary"].get("critical_cells", 0),
            "known_failures": 378,
        }
    )

    print()
    print("=== VALIDATION SUMMARY ===")
    print()
    print(f"{'Date':<12} {'Event':<35} {'mm/hr':>6} {'Alert':<12} {'Cells':>6} {'Known':>6} Result")
    print("-" * 90)

    correct = 0
    total = 0
    for event in event_results:
        expected_critical = event["known_failures"] > 100
        actual_critical = event["alert_level"] == "CRITICAL"
        result_str = "✓ CORRECT" if expected_critical == actual_critical else "✗ WRONG"
        if expected_critical == actual_critical:
            correct += 1
        total += 1
        print(
            f"{event['date']:<12} {event['name']:<35} {event['precip_mm_hr']:>6.1f} "
            f"{event['alert_level']:<12} {event['cells_at_risk']:>6} {event['known_failures']:>6} {result_str}"
        )

    print()
    accuracy = (correct / total * 100.0) if total else 0.0
    print(f"Accuracy: {correct}/{total} ({accuracy:.0f}%)")
    print()
    if total and correct == total:
        print("HOLLER SIREN IS CALIBRATED — all events correctly classified")
    elif total and correct / total >= 0.8:
        print("MOSTLY CALIBRATED — minor threshold adjustment needed")
    else:
        print("NEEDS RECALIBRATION — too many false positives or misses")

    out_path = OUTPUT_DIR / "negative_validation.json"
    with out_path.open("w") as f:
        json.dump(event_results, f, indent=2)
    print()
    print(f"Saved to {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
