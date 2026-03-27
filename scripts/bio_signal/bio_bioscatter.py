#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.bio_signal.common import (
    DATA_DIR,
    MORNING_SCAN_DIR,
    analyze_dualpol_scan,
    ensure_morning_scans,
    parse_scan_datetime,
    save_json,
    sunrise_utc,
)


RESULT_PATH = DATA_DIR / "bioscatter_morning.json"
DATES = ["2021-12-07", "2021-12-10", "2021-12-14"]


def summarize_date(date_str: str, paths: list[Path]) -> dict:
    scan_rows: list[dict] = []
    sunrise = sunrise_utc(datetime.strptime(date_str, "%Y-%m-%d"))
    for path in paths:
        row = analyze_dualpol_scan(path, kind="bird")
        if row is None:
            continue
        stamp = parse_scan_datetime(path.name)
        delta_min = None
        if stamp is not None:
            delta_min = round(((stamp.hour + stamp.minute / 60.0 + stamp.second / 3600.0) - sunrise) * 60.0, 1)
        row["minutes_from_sunrise"] = delta_min
        scan_rows.append(row)

    scan_rows.sort(key=lambda item: item["scan_time"])
    if not scan_rows:
        return {
            "scan_count": 0,
            "avg_bio_fraction": None,
            "avg_bio_gates": None,
            "max_bio_fraction": None,
            "scans": [],
        }

    fractions = [row["fraction"] for row in scan_rows]
    gates = [row["feature_gates"] for row in scan_rows]
    return {
        "scan_count": len(scan_rows),
        "avg_bio_fraction": round(sum(fractions) / len(fractions), 4),
        "avg_bio_gates": round(sum(gates) / len(gates), 1),
        "max_bio_fraction": round(max(fractions), 4),
        "scans": scan_rows,
    }


def main() -> int:
    print("=== NEXRAD BIOSCATTER ROOST RING ===")
    print("Looking for morning roost-ring / bioscatter anomalies at KPAH...")
    print()

    morning: dict[str, dict] = {}
    for date_str in DATES:
        paths = ensure_morning_scans(date_str)
        info = summarize_date(date_str, paths)
        morning[date_str] = {
            "sunrise_utc_decimal": round(sunrise_utc(datetime.strptime(date_str, "%Y-%m-%d")), 3),
            "paths": [str(path) for path in paths],
            **info,
        }
        sunrise_hours = sunrise_utc(datetime.strptime(date_str, "%Y-%m-%d"))
        sr_hour = int(sunrise_hours)
        sr_min = int((sunrise_hours % 1) * 60)
        print(f"  {date_str}: {info['scan_count']} morning scans (sunrise ~{sr_hour:02d}:{sr_min:02d} UTC)")
        if info["avg_bio_fraction"] is not None:
            print(
                f"    avg_bio_fraction={info['avg_bio_fraction']:.4f} "
                f"avg_bio_gates={info['avg_bio_gates']:.1f}"
            )
            for scan in info["scans"][:3]:
                print(
                    f"    {scan['file']} @ {scan['scan_time'][11:16]} UTC "
                    f"({scan['minutes_from_sunrise']:+.0f} min): "
                    f"bio_fraction={scan['fraction']:.4f}"
                )

    quiet_rows = [morning[date] for date in ("2021-12-07", "2021-12-14") if morning.get(date, {}).get("avg_bio_fraction") is not None]
    quiet_mean_fraction = round(sum(row["avg_bio_fraction"] for row in quiet_rows) / len(quiet_rows), 4) if quiet_rows else None
    quiet_mean_gates = round(sum(row["avg_bio_gates"] for row in quiet_rows) / len(quiet_rows), 1) if quiet_rows else None
    outbreak = morning.get("2021-12-10", {})

    roost_assessment = "insufficient comparison data"
    if quiet_mean_fraction is not None and outbreak.get("avg_bio_fraction") is not None:
        frac_ratio = outbreak["avg_bio_fraction"] / max(quiet_mean_fraction, 1e-6)
        gate_ratio = outbreak["avg_bio_gates"] / max(quiet_mean_gates or 1.0, 1e-6)
        if frac_ratio < 0.4 or gate_ratio < 0.4:
            roost_assessment = "suppressed_or_absent"
        elif frac_ratio < 0.7 or gate_ratio < 0.7:
            roost_assessment = "weakened"
        else:
            roost_assessment = "normal_or_stronger"
    else:
        frac_ratio = None
        gate_ratio = None

    payload = {
        "source": "KPAH morning dual-pol bioscatter",
        "scan_cache_dir": str(MORNING_SCAN_DIR),
        "dates": morning,
        "quiet_mean_fraction": quiet_mean_fraction,
        "quiet_mean_gates": quiet_mean_gates,
        "outbreak_fraction_vs_quiet_ratio": round(frac_ratio, 3) if frac_ratio is not None else None,
        "outbreak_gates_vs_quiet_ratio": round(gate_ratio, 3) if gate_ratio is not None else None,
        "roost_assessment": roost_assessment,
    }
    save_json(RESULT_PATH, payload)
    print()
    print(f"Roost assessment: {roost_assessment}")
    print(f"Saved to {RESULT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
