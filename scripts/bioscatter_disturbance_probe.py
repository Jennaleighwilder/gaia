#!/usr/bin/env python3
"""
Phase 5: Biological echo / bioscatter disturbance probe.

Uses dual-pol NEXRAD scans to estimate a low-level biological-echo index:
  - modest reflectivity
  - high cross-correlation coefficient
  - positive ZDR
  - weak radial velocity / low storm contamination

This is a first-pass "nature signal" experiment, not yet an operational engine.
It asks whether the biological echo field collapses or is displaced as a severe
storm environment takes over.
"""

from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

try:
    import pyart
except ImportError as exc:  # pragma: no cover
    raise SystemExit("Requires Py-ART in GAIA .venv: pip install arm-pyart") from exc


ROOT = Path(__file__).resolve().parents[1]
RUNS_DIR = ROOT / "runs"
RUNS_DIR.mkdir(parents=True, exist_ok=True)

DEFAULT_SCAN_DIR = ROOT / "tests" / "fixtures" / "nexrad_quadstate"
RANGE_MIN_KM = 30.0
RANGE_MAX_KM = 120.0
LOW_SWEEPS = 3


def _scan_time_utc(radar) -> datetime:
    raw = pyart.util.datetime_utils.datetimes_from_radar(radar)[0]
    return datetime(
        raw.year,
        raw.month,
        raw.day,
        raw.hour,
        raw.minute,
        raw.second,
        tzinfo=timezone.utc,
    )


def _field(radar, names: list[str]):
    for name in names:
        if name in radar.fields:
            return radar.fields[name]["data"]
    return None


def analyze_scan(path: Path) -> dict | None:
    radar = pyart.io.read_nexrad_archive(str(path), delay_field_loading=True)
    try:
        scan_time = _scan_time_utc(radar)
        refl = _field(radar, ["reflectivity"])
        cc = _field(radar, ["cross_correlation_ratio", "rhohv"])
        zdr = _field(radar, ["differential_reflectivity", "zdr"])
        vel = _field(radar, ["velocity"])
        if refl is None or cc is None or zdr is None:
            return None

        bio_gate_count = 0
        precip_gate_count = 0
        clutter_gate_count = 0
        bio_strength_values: list[float] = []
        bio_refl_values: list[float] = []
        bio_zdr_values: list[float] = []
        bio_cc_values: list[float] = []

        for sw in range(min(LOW_SWEEPS, radar.nsweeps)):
            sl = radar.get_slice(sw)
            refl_arr = np.ma.filled(refl[sl], np.nan)
            cc_arr = np.ma.filled(cc[sl], np.nan)
            zdr_arr = np.ma.filled(zdr[sl], np.nan)
            vel_arr = np.ma.filled(vel[sl], np.nan) if vel is not None else np.full_like(refl_arr, np.nan)
            ranges_km = np.asarray(radar.range["data"], dtype=float) / 1000.0
            range_mask = (ranges_km >= RANGE_MIN_KM) & (ranges_km <= RANGE_MAX_KM)
            if not np.any(range_mask):
                continue

            refl_cut = refl_arr[:, range_mask]
            cc_cut = cc_arr[:, range_mask]
            zdr_cut = zdr_arr[:, range_mask]
            vel_cut = vel_arr[:, range_mask]
            finite = np.isfinite(refl_cut) & np.isfinite(cc_cut) & np.isfinite(zdr_cut)

            # Heuristic biological echo mask:
            # low-to-moderate reflectivity, coherent scatterers, positive ZDR,
            # and not strong storm radial velocity.
            bio_mask = (
                finite
                & (refl_cut >= 5.0)
                & (refl_cut <= 20.0)
                & (cc_cut >= 0.94)
                & (cc_cut <= 0.995)
                & (zdr_cut >= 0.8)
                & (zdr_cut <= 5.5)
                & (~np.isfinite(vel_cut) | (np.abs(vel_cut) <= 12.0))
            )
            precip_mask = finite & (refl_cut >= 35.0) & (cc_cut >= 0.85)
            clutter_mask = finite & (refl_cut >= 5.0) & (cc_cut < 0.80)

            bio_gate_count += int(np.sum(bio_mask))
            precip_gate_count += int(np.sum(precip_mask))
            clutter_gate_count += int(np.sum(clutter_mask))

            if np.any(bio_mask):
                refl_vals = refl_cut[bio_mask]
                cc_vals = cc_cut[bio_mask]
                zdr_vals = zdr_cut[bio_mask]
                # Higher when echoes are both strong enough and biologically shaped.
                strength = (refl_vals - 5.0) * np.clip(zdr_vals, 0.0, 5.0) * np.clip(cc_vals - 0.9, 0.0, 0.2)
                bio_strength_values.extend(np.asarray(strength, dtype=float).tolist())
                bio_refl_values.extend(np.asarray(refl_vals, dtype=float).tolist())
                bio_zdr_values.extend(np.asarray(zdr_vals, dtype=float).tolist())
                bio_cc_values.extend(np.asarray(cc_vals, dtype=float).tolist())

        bio_index = float(np.mean(bio_strength_values)) if bio_strength_values else 0.0
        return {
            "scan_time": scan_time.isoformat(),
            "file": path.name,
            "bio_gate_count": bio_gate_count,
            "precip_gate_count": precip_gate_count,
            "clutter_gate_count": clutter_gate_count,
            "bio_index": round(bio_index, 3),
            "bio_refl_mean": round(float(np.mean(bio_refl_values)), 3) if bio_refl_values else 0.0,
            "bio_zdr_mean": round(float(np.mean(bio_zdr_values)), 3) if bio_zdr_values else 0.0,
            "bio_cc_mean": round(float(np.mean(bio_cc_values)), 3) if bio_cc_values else 0.0,
        }
    finally:
        del radar


def summarize_series(rows: list[dict]) -> dict:
    if not rows:
        return {}
    baseline_rows = rows[: min(10, len(rows))]
    baseline_gate_mean = float(np.mean([row["bio_gate_count"] for row in baseline_rows]))
    baseline_index_mean = float(np.mean([row["bio_index"] for row in baseline_rows]))
    peak_precip = max(rows, key=lambda row: row["precip_gate_count"])
    min_bio = min(rows, key=lambda row: row["bio_gate_count"])
    collapse_row = None
    for row in rows:
        if baseline_gate_mean > 0 and row["bio_gate_count"] <= 0.4 * baseline_gate_mean and row["precip_gate_count"] >= 100:
            collapse_row = row
            break
    return {
        "baseline_bio_gate_mean": round(baseline_gate_mean, 2),
        "baseline_bio_index_mean": round(baseline_index_mean, 3),
        "peak_precip_scan": peak_precip,
        "min_bio_scan": min_bio,
        "bioscatter_collapse_scan": collapse_row,
    }


def write_markdown(rows: list[dict], summary: dict) -> None:
    lines: list[str] = []
    lines.append("# Bioscatter Disturbance Probe")
    lines.append("")
    lines.append("First-pass biological echo experiment using dual-pol NEXRAD.")
    lines.append("")
    if summary:
        lines.append(f"- Baseline bio gates: **{summary.get('baseline_bio_gate_mean', 0)}**")
        lines.append(f"- Baseline bio index: **{summary.get('baseline_bio_index_mean', 0)}**")
        collapse = summary.get("bioscatter_collapse_scan")
        if collapse:
            lines.append(f"- First bioscatter collapse: **{collapse['scan_time']}**")
        peak_precip = summary.get("peak_precip_scan")
        if peak_precip:
            lines.append(f"- Peak precip contamination: **{peak_precip['scan_time']}**")
    lines.append("")
    lines.append("| Scan Time | Bio Gates | Bio Index | Precip Gates | Bio Refl | Bio ZDR | Bio CC |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|")
    for row in rows[:40]:
        lines.append(
            f"| {row['scan_time']} | {row['bio_gate_count']} | {row['bio_index']} | "
            f"{row['precip_gate_count']} | {row['bio_refl_mean']} | {row['bio_zdr_mean']} | {row['bio_cc_mean']} |"
        )
    (RUNS_DIR / "bioscatter_probe_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--scan-dir", default=str(DEFAULT_SCAN_DIR))
    ap.add_argument("--pattern", default="KPAH*_V06*")
    ap.add_argument("--start", default=None, help="Optional ISO UTC start")
    ap.add_argument("--end", default=None, help="Optional ISO UTC end")
    args = ap.parse_args()

    scan_dir = Path(args.scan_dir).resolve()
    if not scan_dir.exists():
        raise SystemExit(f"Scan directory not found: {scan_dir}")

    start_dt = datetime.fromisoformat(args.start).replace(tzinfo=timezone.utc) if args.start else None
    end_dt = datetime.fromisoformat(args.end).replace(tzinfo=timezone.utc) if args.end else None

    rows: list[dict] = []
    files = sorted(scan_dir.glob(args.pattern))
    print(f"Processing {len(files)} scans from {scan_dir}")
    for idx, path in enumerate(files, start=1):
        try:
            row = analyze_scan(path)
        except Exception:
            continue
        if row is None:
            continue
        stamp = datetime.fromisoformat(row["scan_time"])
        if start_dt and stamp < start_dt:
            continue
        if end_dt and stamp > end_dt:
            continue
        rows.append(row)
        if idx % 25 == 0:
            print(f"  processed {idx}/{len(files)}")

    summary = summarize_series(rows)
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "scan_count": len(rows),
        "rows": rows,
        "summary": summary,
    }
    (RUNS_DIR / "bioscatter_probe_report.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    write_markdown(rows, summary)
    print("Wrote runs/bioscatter_probe_report.json")
    print("Wrote runs/bioscatter_probe_report.md")
    if summary.get("bioscatter_collapse_scan"):
        print("Bioscatter collapse detected at", summary["bioscatter_collapse_scan"]["scan_time"])
    else:
        print("No clear bioscatter collapse trigger crossed the heuristic threshold.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
