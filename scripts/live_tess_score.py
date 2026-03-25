#!/usr/bin/env python3
"""
Compute TODAY's live TESS score from real-time climate indices.

Fetches current values of AO, PNA, MEI, PDO, SST from NOAA/CPC,
runs UVRK-1 on the trailing window, and reports the multi-layer
convergence score.

Output: JSON to stdout (consumed by dashboard).
"""

from __future__ import annotations

import json
import math
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def fetch_text(url: str, timeout: int = 15) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "GAIA/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", errors="replace")


def parse_latest_monthly(text: str) -> list[tuple[int, int, float]]:
    """Parse 'YEAR MONTH VALUE' lines, return last 18 months."""
    rows = []
    for line in text.strip().split("\n"):
        parts = line.split()
        if len(parts) >= 3:
            try:
                y, m, v = int(parts[0]), int(parts[1]), float(parts[2])
                if 1950 <= y <= 2030 and 1 <= m <= 12:
                    rows.append((y, m, v))
            except (ValueError, IndexError):
                pass
    return rows[-18:]


def parse_mei_latest(text: str) -> list[tuple[int, int, float]]:
    """Parse MEI format: YEAR val1 val2 ... val12"""
    rows = []
    for line in text.strip().split("\n"):
        parts = line.split()
        if len(parts) < 2:
            continue
        try:
            year = int(parts[0])
        except ValueError:
            continue
        for m, vs in enumerate(parts[1:13], start=1):
            try:
                v = float(vs)
                if v > -900:
                    rows.append((year, m, v))
            except (ValueError, IndexError):
                pass
    return rows[-18:]


def parse_sst_indices(text: str) -> list[tuple[int, int, dict]]:
    """Parse CPC SST: YEAR MONTH nino12 anom nino3 anom nino34 anom ..."""
    rows = []
    for line in text.strip().split("\n"):
        parts = line.split()
        if len(parts) < 8:
            continue
        try:
            y, m = int(parts[0]), int(parts[1])
            row = {"nino34": float(parts[6]), "nino34_anom": float(parts[7])}
            rows.append((y, m, row))
        except (ValueError, IndexError):
            pass
    return rows[-18:]


def uvrk1_instability(values: list[float]) -> float:
    """UVRK-1 instability score for a time series [0..1]."""
    if len(values) < 3:
        return 0.0
    window = min(6, len(values))
    recent = values[-window:]
    mean = sum(recent) / len(recent)
    var = sum((v - mean) ** 2 for v in recent) / len(recent)
    current_vol = math.sqrt(max(0, var))

    baseline = values[-min(12, len(values)):]
    bmean = sum(baseline) / len(baseline)
    bvar = sum((v - bmean) ** 2 for v in baseline) / len(baseline)
    baseline_vol = math.sqrt(max(0.001, bvar))

    rank = min(max(sum(1 for v in baseline if abs(v) < abs(values[-1])) / len(baseline), 0.01), 0.99)
    if rank < 0.5:
        t = math.sqrt(-2 * math.log(rank))
    else:
        t = math.sqrt(-2 * math.log(1 - rank))
    c0, c1, c2 = 2.515517, 0.802853, 0.010328
    d1, d2, d3 = 1.432788, 0.189269, 0.001308
    probit = t - (c0 + c1 * t + c2 * t * t) / (1 + d1 * t + d2 * t * t + d3 * t * t * t)
    if rank < 0.5:
        probit = -probit

    predicted_vol = 0.92 * current_vol + 0.08 * 0.15 * abs(probit)
    ratio = predicted_vol / max(0.001, baseline_vol)
    extremity = abs(values[-1]) / max(0.001, baseline_vol)
    trend = abs(values[-1] - values[-3]) / max(0.001, baseline_vol) if len(values) >= 3 else 0

    return min(1.0, max(0.0, (ratio + extremity + trend) / 6.0))


def main():
    now = datetime.now(timezone.utc)
    result = {
        "timestamp": now.isoformat(),
        "date": now.strftime("%Y-%m-%d"),
        "layers": {},
        "tess_score": 0.0,
        "signals": [],
        "errors": [],
    }

    # --- Fetch current indices ---
    ao_vals, pna_vals, mei_vals, pdo_vals, sst_vals = [], [], [], [], []
    ao_current = pna_current = mei_current = pdo_current = nino34a_current = None

    try:
        ao_text = fetch_text("https://www.cpc.ncep.noaa.gov/products/precip/CWlink/daily_ao_index/monthly.ao.index.b50.current.ascii")
        ao_rows = parse_latest_monthly(ao_text)
        ao_vals = [v for _, _, v in ao_rows]
        if ao_rows:
            ao_current = ao_rows[-1][2]
    except Exception as e:
        result["errors"].append(f"AO: {e}")

    try:
        pna_text = fetch_text("https://www.cpc.ncep.noaa.gov/products/precip/CWlink/pna/norm.pna.monthly.b5001.current.ascii")
        pna_rows = parse_latest_monthly(pna_text)
        pna_vals = [v for _, _, v in pna_rows]
        if pna_rows:
            pna_current = pna_rows[-1][2]
    except Exception as e:
        result["errors"].append(f"PNA: {e}")

    try:
        mei_text = fetch_text("https://psl.noaa.gov/enso/mei/data/meiv2.data")
        mei_rows = parse_mei_latest(mei_text)
        mei_vals = [v for _, _, v in mei_rows]
        if mei_rows:
            mei_current = mei_rows[-1][2]
    except Exception as e:
        result["errors"].append(f"MEI: {e}")

    try:
        pdo_text = fetch_text("https://www.ncei.noaa.gov/pub/data/cmb/ersst/v5/index/ersst.v5.pdo.dat")
        pdo_rows = []
        for line in pdo_text.strip().split("\n"):
            parts = line.split()
            if len(parts) < 13:
                continue
            try:
                year = int(parts[0])
            except ValueError:
                continue
            for m, vs in enumerate(parts[1:13], start=1):
                try:
                    v = float(vs)
                    if v < 90:
                        pdo_rows.append(v)
                except (ValueError, IndexError):
                    pass
        pdo_vals = pdo_rows[-18:]
        if pdo_vals:
            pdo_current = pdo_vals[-1]
    except Exception as e:
        result["errors"].append(f"PDO: {e}")

    try:
        sst_text = fetch_text("https://www.cpc.ncep.noaa.gov/data/indices/sstoi.indices")
        sst_rows = parse_sst_indices(sst_text)
        sst_vals = [d["nino34_anom"] for _, _, d in sst_rows]
        if sst_rows:
            nino34a_current = sst_rows[-1][2]["nino34_anom"]
    except Exception as e:
        result["errors"].append(f"SST: {e}")

    # --- LAYER 1: ORIGIN ---
    origin_score = 0.0
    if mei_vals:
        origin_score = max(origin_score, uvrk1_instability(mei_vals))
        if mei_current is not None:
            if mei_current < -1.0:
                result["signals"].append("LA_NINA_STRONG")
                origin_score = max(origin_score, 0.8)
            elif mei_current < -0.5:
                result["signals"].append("LA_NINA")
                origin_score = max(origin_score, 0.5)
            elif mei_current > 1.0:
                result["signals"].append("EL_NINO_STRONG")
                origin_score = max(origin_score, 0.6)
            elif mei_current > 0.5:
                result["signals"].append("EL_NINO")
    if pdo_vals:
        pdo_score = uvrk1_instability(pdo_vals)
        if pdo_current is not None and pdo_current < -1.0:
            result["signals"].append("PDO_NEG_STRONG")
            pdo_score = max(pdo_score, 0.7)
        origin_score = max(origin_score, pdo_score)

    result["layers"]["origin"] = {
        "score": round(origin_score, 3),
        "mei": round(mei_current, 2) if mei_current is not None else None,
        "pdo": round(pdo_current, 2) if pdo_current is not None else None,
    }

    # --- LAYER 2: TRANSPORT ---
    transport_score = 0.0
    if ao_vals:
        ao_score = uvrk1_instability(ao_vals)
        if ao_current is not None:
            if ao_current < -1.0:
                result["signals"].append("AO_NEG_STRONG")
                ao_score = max(ao_score, 0.8)
            elif ao_current < -0.5:
                result["signals"].append("AO_NEGATIVE")
                ao_score = max(ao_score, 0.5)
        transport_score = max(transport_score, ao_score)
    if pna_vals:
        pna_score = uvrk1_instability(pna_vals)
        if pna_current is not None:
            if pna_current > 1.0:
                result["signals"].append("PNA_POS_STRONG")
                pna_score = max(pna_score, 0.7)
            elif pna_current > 0.5:
                result["signals"].append("PNA_POSITIVE")
                pna_score = max(pna_score, 0.5)
        transport_score = max(transport_score, pna_score)

    result["layers"]["transport"] = {
        "score": round(transport_score, 3),
        "ao": round(ao_current, 2) if ao_current is not None else None,
        "pna": round(pna_current, 2) if pna_current is not None else None,
    }

    # --- LAYER 3: LOADING ---
    loading_score = 0.0
    if sst_vals:
        sst_score = uvrk1_instability(sst_vals)
        if nino34a_current is not None and nino34a_current < -0.5:
            result["signals"].append("COOL_PACIFIC")
            loading_score = max(loading_score, 0.6)
        loading_score = max(loading_score, sst_score)
        month = now.month
        if mei_current is not None and mei_current < -0.5 and month in (3, 4, 5):
            result["signals"].append("LANINA_SPRING_GULF")
            loading_score = max(loading_score, 0.7)

    result["layers"]["loading"] = {
        "score": round(loading_score, 3),
        "nino34_anom": round(nino34a_current, 2) if nino34a_current is not None else None,
    }

    # --- TESS CONVERGENCE ---
    layers_firing = sum(1 for s in [origin_score, transport_score, loading_score] if s >= 0.5)
    tess = origin_score * 0.35 + transport_score * 0.35 + loading_score * 0.30
    if layers_firing >= 3:
        tess = min(1.0, tess * 1.3)
    elif layers_firing >= 2:
        tess = min(1.0, tess * 1.1)

    result["tess_score"] = round(tess, 3)
    result["layers_firing"] = layers_firing

    if tess >= 0.7:
        result["risk_level"] = "ELEVATED"
    elif tess >= 0.4:
        result["risk_level"] = "MODERATE"
    else:
        result["risk_level"] = "LOW"

    # Cache to disk for dashboard
    cache_path = ROOT / "runs" / "live_tess.json"
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(json.dumps(result, indent=2) + "\n")

    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
