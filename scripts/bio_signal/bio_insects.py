#!/usr/bin/env python3
from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.bio_signal.common import (
    DATA_DIR,
    RUNS_DIR,
    analyze_dualpol_scan,
    ensure_morning_scans,
    load_json,
    save_json,
)


RESULT_PATH = DATA_DIR / "insect_layer.json"
DATES = ["2021-12-07", "2021-12-10", "2021-12-14"]


def summarize_date(paths: list[Path]) -> dict:
    scans: list[dict] = []
    for path in paths:
        row = analyze_dualpol_scan(path, kind="insect")
        if row is not None:
            scans.append(row)
    scans.sort(key=lambda item: item["scan_time"])
    if not scans:
        return {
            "scan_count": 0,
            "avg_insect_fraction": None,
            "avg_insect_gates": None,
            "scans": [],
        }
    fractions = [row["fraction"] for row in scans]
    gates = [row["feature_gates"] for row in scans]
    return {
        "scan_count": len(scans),
        "avg_insect_fraction": round(sum(fractions) / len(fractions), 4),
        "avg_insect_gates": round(sum(gates) / len(gates), 1),
        "scans": scans,
    }


def main() -> int:
    print("=== INSECT LAYER ANALYSIS ===")
    print("Looking for insect echo collapse before outbreak...")
    print()

    payload: dict[str, dict] = {"dates": {}}
    for date_str in DATES:
        summary = summarize_date(ensure_morning_scans(date_str))
        payload["dates"][date_str] = summary
        print(f"  {date_str}: {summary['scan_count']} scans")
        if summary["avg_insect_fraction"] is not None:
            print(
                f"    avg_insect_fraction={summary['avg_insect_fraction']:.4f} "
                f"avg_insect_gates={summary['avg_insect_gates']:.1f}"
            )

    quiet_rows = [payload["dates"][date] for date in ("2021-12-07", "2021-12-14") if payload["dates"][date]["avg_insect_fraction"] is not None]
    quiet_fraction = round(sum(row["avg_insect_fraction"] for row in quiet_rows) / len(quiet_rows), 4) if quiet_rows else None
    quiet_gates = round(sum(row["avg_insect_gates"] for row in quiet_rows) / len(quiet_rows), 1) if quiet_rows else None
    outbreak = payload["dates"]["2021-12-10"]

    if quiet_fraction is None or outbreak["avg_insect_fraction"] is None:
        assessment = "insufficient data"
        frac_ratio = None
    else:
        frac_ratio = outbreak["avg_insect_fraction"] / max(quiet_fraction, 1e-6)
        if quiet_fraction < 0.01 and (quiet_gates or 0.0) < 50.0:
            assessment = "no_usable_winter_insect_layer"
        elif frac_ratio < 0.7:
            assessment = "collapsed"
        else:
            assessment = "no_clear_collapse"

    payload.update(
        {
            "quiet_mean_insect_fraction": quiet_fraction,
            "quiet_mean_insect_gates": quiet_gates,
            "outbreak_fraction_vs_quiet_ratio": round(frac_ratio, 3) if frac_ratio is not None else None,
            "assessment": assessment,
        }
    )

    probe_path = RUNS_DIR / "bioscatter_probe_report.json"
    if probe_path.exists():
        payload["existing_probe_summary"] = load_json(probe_path).get("summary", {})

    save_json(RESULT_PATH, payload)
    print()
    print(f"Assessment: {assessment}")
    if probe_path.exists():
        print("Existing bioscatter probe summary loaded from runs/bioscatter_probe_report.json")
    print(f"Saved to {RESULT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
