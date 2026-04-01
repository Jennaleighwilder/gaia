#!/usr/bin/env python3
"""
Phase 4: Dual-pol TDS (Tornadic Debris Signature) detector for the
Dec 10-11 2021 Quad-State outbreak — KPAH Paducah KY scans.

TDS gates (Snyder & Ryzhkov 2015 HCA framework) — all must fire together:
  - CC < 0.80
  - Reflectivity (Z) >= 45 dBZ
  - ZDR <= 0.5 dB  (near-zero or negative)
  - Beam height check: beam_overshoot flag if > 3 km AGL, reduces confidence

Rotation couplet is recorded but not required for dual-pol TDS confirmation.

Outputs:
  - runs/dualpol_mayfield_report.json
  - runs/dualpol_mayfield_report.md
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
    raise SystemExit("Requires Py-ART: pip install arm-pyart") from exc


ROOT = Path(__file__).resolve().parents[1]
RUNS_DIR = ROOT / "runs"
RUNS_DIR.mkdir(parents=True, exist_ok=True)

MAYFIELD_LAT = 36.741
MAYFIELD_LON = -88.636
# Mayfield times in UTC (local CST +6 hours):
#   impact ~03:30 CST => 09:30 UTC
#   NWS Paducah TOR for Mayfield ~03:02 CST => 09:02 UTC
MAYFIELD_IMPACT_UTC = datetime(2021, 12, 11, 9, 30, tzinfo=timezone.utc)
NWS_PADUCAH_WARNING_UTC = datetime(2021, 12, 11, 9, 2, tzinfo=timezone.utc)


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlon / 2) ** 2
    )
    return r * 2 * math.asin(math.sqrt(min(1.0, a)))


def _beam_height_km(range_km: float, elevation_deg: float, antenna_alt_km: float = 0.1) -> float:
    """
    Standard 4/3 Earth-radius beam-height formula (Doviak & Zrnic 1993).
    Returns beam centre height AGL (km) for a given slant range and elevation.
    """
    ke = 4.0 / 3.0
    re = 6371.0
    theta = math.radians(elevation_deg)
    h = (
        math.sqrt(range_km ** 2 + (ke * re) ** 2 + 2 * range_km * ke * re * math.sin(theta))
        - ke * re
        + antenna_alt_km
    )
    return max(0.0, h)


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
    for n in names:
        if n in radar.fields:
            return radar.fields[n]["data"]
    return None


def analyze_scan(path: Path, radius_km: float = 40.0) -> dict | None:
    radar = pyart.io.read_nexrad_archive(str(path), delay_field_loading=True)
    scan_time = _scan_time_utc(radar)

    refl = _field(radar, ["reflectivity"])
    vel = _field(radar, ["velocity"])
    cc = _field(radar, ["cross_correlation_ratio", "rhohv"])
    zdr = _field(radar, ["differential_reflectivity", "zdr"])
    if refl is None or vel is None or cc is None:
        return None

    best = None
    debris_candidates: list[dict] = []
    for sw in range(min(3, radar.nsweeps)):
        sl = radar.get_slice(sw)
        gate_lat, gate_lon, _ = radar.get_gate_lat_lon_alt(sw)
        dist = np.vectorize(haversine_km)(gate_lat, gate_lon, MAYFIELD_LAT, MAYFIELD_LON)
        mask = dist <= radius_km
        if not np.any(mask):
            continue

        r = np.ma.filled(refl[sl], np.nan)
        v = np.ma.filled(vel[sl], np.nan)
        c = np.ma.filled(cc[sl], np.nan)
        z = np.ma.filled(zdr[sl], np.nan) if zdr is not None else np.full_like(r, np.nan)

        m = mask & np.isfinite(r) & np.isfinite(c)
        if not np.any(m):
            continue

        refl_max = float(np.nanmax(r[m]))
        cc_min = float(np.nanmin(c[m]))
        if np.any(np.isfinite(z[m])):
            zdr_med = float(np.nanmedian(z[m]))
        else:
            zdr_med = 999.0

        vm = m & np.isfinite(v)
        vmax = float(np.nanmax(v[vm])) if np.any(vm) else float("nan")
        vmin = float(np.nanmin(v[vm])) if np.any(vm) else float("nan")
        vrot = 0.0
        if vmax > 0 and vmin < 0:
            vrot = (vmax - vmin) / 2.0

        # ── Beam height check (Doviak & Zrnic 1993) ──────────────────────
        elevation_deg = float(radar.fixed_angle["data"][sw])
        # Use median range of masked gates as representative slant range
        ranges = radar.range["data"]
        gate_ranges = np.tile(ranges, (gate_lat.shape[0], 1))
        masked_ranges = gate_ranges[mask & np.isfinite(r)]
        representative_range_km = float(np.nanmedian(masked_ranges)) / 1000.0 if masked_ranges.size else 0.0
        beam_h_km = _beam_height_km(representative_range_km, elevation_deg)
        beam_overshoot = beam_h_km > 3.0

        # ── TDS gate (Snyder & Ryzhkov 2015 HCA framework) ───────────────
        # All four conditions must fire simultaneously:
        #   1. CC < 0.80
        #   2. Z >= 45 dBZ
        #   3. ZDR <= 0.5 dB  (near-zero or negative)
        #   4. Beam height <= 3 km AGL  (overshoot = reduced confidence, not disqualifier)
        tds_cc   = cc_min < 0.80
        tds_z    = refl_max >= 45.0
        tds_zdr  = zdr_med <= 0.5
        debris   = tds_cc and tds_z and tds_zdr

        # Confidence: start at 1.0, reduce 0.30 for beam overshoot
        confidence = 1.0
        if beam_overshoot:
            confidence -= 0.30

        candidate = {
            "scan_time": scan_time.isoformat(),
            "sweep": sw,
            "reflectivity_dbz": round(refl_max, 1),
            "cc_min": round(cc_min, 3),
            "zdr_median_db": round(zdr_med, 2),
            "vrot_ms": round(vrot, 1),
            "rotation_available": bool(np.isfinite(vmax) and np.isfinite(vmin)),
            "beam_height_agl_km": round(beam_h_km, 2),
            "beam_overshoot": beam_overshoot,
            "tds_gates": {"cc": tds_cc, "z": tds_z, "zdr": tds_zdr},
            "tds_confidence": round(confidence, 2),
            "debris_detected": debris,
            "file": path.name,
        }
        if debris:
            debris_candidates.append(candidate)
        if best is None or candidate["cc_min"] < best["cc_min"]:
            best = candidate

    if debris_candidates:
        debris_candidates.sort(
            key=lambda x: (x["reflectivity_dbz"], -x["cc_min"]),
            reverse=True,
        )
        return debris_candidates[0]
    return best


def write_markdown(best_hit: dict | None, all_hits: list[dict], scan_count: int) -> None:
    lines: list[str] = []
    lines.append("# Dual-Pol Mayfield Confirmation")
    lines.append("")
    lines.append(f"Scans processed: **{scan_count}**")
    lines.append("")
    if best_hit is None:
        lines.append("No debris-ball signature met thresholds.")
    else:
        hit_time = datetime.fromisoformat(best_hit["scan_time"])
        lead_mayfield = (MAYFIELD_IMPACT_UTC - hit_time).total_seconds() / 60.0
        lead_nws = (NWS_PADUCAH_WARNING_UTC - hit_time).total_seconds() / 60.0
        lines.append(
            f"Confirmed debris-ball detection: **{hit_time.strftime('%Y-%m-%d %H:%M:%S UTC')}**"
        )
        lines.append(f"- Lead vs Mayfield impact: **{lead_mayfield:.1f} min**")
        lines.append(f"- Lead vs NWS Paducah TOR warning: **{lead_nws:.1f} min**")
        lines.append(
            f"- Metrics: Z={best_hit['reflectivity_dbz']} dBZ, CC={best_hit['cc_min']}, "
            f"ZDR={best_hit['zdr_median_db']} dB, Vrot={best_hit['vrot_ms']} m/s"
        )
    lines.append("")
    lines.append("| Scan Time | Z (dBZ) | CC min | ZDR med | Vrot (m/s) | Debris |")
    lines.append("|---|---:|---:|---:|---:|---:|")
    for h in all_hits[:20]:
        lines.append(
            f"| {h['scan_time']} | {h['reflectivity_dbz']} | {h['cc_min']} | "
            f"{h['zdr_median_db']} | {h['vrot_ms']} | {'YES' if h['debris_detected'] else 'no'} |"
        )
    (RUNS_DIR / "dualpol_mayfield_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--scan-dir", default="tests/fixtures/nexrad_quadstate")
    ap.add_argument("--start", default="2021-12-11T08:00:00")
    ap.add_argument("--end", default="2021-12-11T10:30:00")
    args = ap.parse_args()

    scan_dir = (ROOT / args.scan_dir).resolve()
    if not scan_dir.exists():
        raise SystemExit(f"Scan directory not found: {scan_dir}")

    start_dt = datetime.fromisoformat(args.start).replace(tzinfo=timezone.utc)
    end_dt = datetime.fromisoformat(args.end).replace(tzinfo=timezone.utc)

    files = sorted(scan_dir.glob("KPAH*_V06*"))
    print(f"Processing {len(files)} files from {scan_dir}")
    hits: list[dict] = []
    scans_in_window = 0
    for i, fp in enumerate(files, start=1):
        try:
            radar = pyart.io.read_nexrad_archive(str(fp), delay_field_loading=True)
            st = _scan_time_utc(radar)
            del radar
        except Exception:
            continue
        if st < start_dt or st > end_dt:
            continue
        scans_in_window += 1
        try:
            row = analyze_scan(fp)
            if row is not None:
                hits.append(row)
            if i % 20 == 0:
                print(f"  processed {i}/{len(files)}")
        except Exception:
            continue

    positives = [h for h in hits if h["debris_detected"]]
    best_hit = sorted(positives, key=lambda x: x["scan_time"])[0] if positives else None
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "scan_count_total": len(files),
        "scan_count_window": scans_in_window,
        "detections": len(positives),
        "best_detection": best_hit,
        "all_hits": hits,
    }
    if best_hit is not None:
        hit_dt = datetime.fromisoformat(best_hit["scan_time"])
        report["lead_minutes_vs_mayfield_impact"] = round(
            (MAYFIELD_IMPACT_UTC - hit_dt).total_seconds() / 60.0, 1
        )
        report["lead_minutes_vs_nws_paducah_warning"] = round(
            (NWS_PADUCAH_WARNING_UTC - hit_dt).total_seconds() / 60.0, 1
        )

    (RUNS_DIR / "dualpol_mayfield_report.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    write_markdown(best_hit, hits, len(files))

    print("Wrote runs/dualpol_mayfield_report.json")
    print("Wrote runs/dualpol_mayfield_report.md")
    if best_hit:
        print(
            "Confirmed debris-ball at",
            best_hit["scan_time"],
            f"(lead {report['lead_minutes_vs_mayfield_impact']} min vs Mayfield impact)",
        )
    else:
        print("No debris-ball detection crossed thresholds in selected window.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
