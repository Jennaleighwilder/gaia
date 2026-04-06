#!/usr/bin/env python3
"""
Compute TODAY's live TESS score from real-time climate indices.

Fetches current values of AO, PNA, MEI, PDO, SST from NOAA/CPC,
runs UVRK-1 on the trailing window, and reports the multi-layer
convergence score.

Output: JSON to stdout (default). With ``--cron``, writes runs/live_tess.json
and prints a one-line summary (for scheduled runs / log files).
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


def parse_all_monthly_rows(text: str) -> list[tuple[int, int, float]]:
    rows: list[tuple[int, int, float]] = []
    for line in text.strip().split("\n"):
        parts = line.split()
        if len(parts) >= 3:
            try:
                y, m, v = int(parts[0]), int(parts[1]), float(parts[2])
                if 1950 <= y <= 2035 and 1 <= m <= 12:
                    rows.append((y, m, v))
            except (ValueError, IndexError):
                pass
    rows.sort()
    return rows


def series_through(rows: list[tuple[int, int, float]], ym: tuple[int, int]) -> list[float]:
    return [v for y, m, v in rows if (y, m) <= ym]


def parse_all_mei_rows(text: str) -> list[tuple[int, int, float]]:
    rows: list[tuple[int, int, float]] = []
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
    rows.sort()
    return rows


def parse_pdo_flat_through(text: str, ym: tuple[int, int]) -> list[float]:
    flat: list[float] = []
    for line in text.strip().split("\n"):
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
                if v < 90 and (year, m) <= ym:
                    flat.append(v)
            except (ValueError, IndexError):
                pass
    return flat


def parse_all_sst_anom_rows(text: str) -> list[tuple[int, int, float]]:
    rows: list[tuple[int, int, float]] = []
    for line in text.strip().split("\n"):
        parts = line.split()
        if len(parts) < 8:
            continue
        try:
            y, m = int(parts[0]), int(parts[1])
            if parts[0].upper().startswith("YR"):
                continue
            rows.append((y, m, float(parts[7])))
        except (ValueError, IndexError):
            pass
    rows.sort()
    return rows


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


def compute_tess_score(
    as_of: datetime, *, neutral: bool = False, use_network: bool = False
) -> float:
    """
    Historical TESS for a calendar date using monthly indices through that month
    (offline files under data/global_indices/). For scrambled-index checks, pass
    neutral=True. Live/dashboard fetches set use_network=True for MJO/Gulf ERDDAP.
    """
    from scripts.historical_tess import compute_tess_score as _historical

    return _historical(as_of, neutral=neutral, use_network=use_network)


def main():
    cron_mode = "--cron" in sys.argv
    now = datetime.now(timezone.utc)
    ym = (now.year, now.month)
    result: dict = {
        "timestamp": now.isoformat(),
        "date": now.strftime("%Y-%m-%d"),
        "layers": {},
        "tess_score": 0.0,
        "signals": [],
        "errors": [],
    }

    ao_ser: list[float] = []
    pna_ser: list[float] = []
    mei_ser: list[float] = []
    pdo_ser: list[float] = []
    sst_ser: list[float] = []
    ao_current = pna_current = mei_current = pdo_current = nino34a_current = None

    try:
        ao_text = fetch_text(
            "https://www.cpc.ncep.noaa.gov/products/precip/CWlink/daily_ao_index/monthly.ao.index.b50.current.ascii"
        )
        ao_all = parse_all_monthly_rows(ao_text)
        ao_ser = series_through(ao_all, ym)
        if ao_ser:
            ao_current = ao_ser[-1]
    except Exception as e:
        result["errors"].append(f"AO: {e}")

    try:
        pna_text = fetch_text(
            "https://www.cpc.ncep.noaa.gov/products/precip/CWlink/pna/norm.pna.monthly.b5001.current.ascii"
        )
        pna_all = parse_all_monthly_rows(pna_text)
        pna_ser = series_through(pna_all, ym)
        if pna_ser:
            pna_current = pna_ser[-1]
    except Exception as e:
        result["errors"].append(f"PNA: {e}")

    try:
        mei_text = fetch_text("https://psl.noaa.gov/enso/mei/data/meiv2.data")
        mei_all = parse_all_mei_rows(mei_text)
        mei_ser = series_through(mei_all, ym)
        if mei_ser:
            mei_current = mei_ser[-1]
    except Exception as e:
        result["errors"].append(f"MEI: {e}")

    try:
        pdo_text = fetch_text(
            "https://www.ncei.noaa.gov/pub/data/cmb/ersst/v5/index/ersst.v5.pdo.dat"
        )
        pdo_ser = parse_pdo_flat_through(pdo_text, ym)
        if pdo_ser:
            pdo_current = pdo_ser[-1]
    except Exception as e:
        result["errors"].append(f"PDO: {e}")

    try:
        sst_text = fetch_text("https://www.cpc.ncep.noaa.gov/data/indices/sstoi.indices")
        sst_all = parse_all_sst_anom_rows(sst_text)
        sst_ser = series_through(sst_all, ym)
        if sst_ser:
            nino34a_current = sst_ser[-1]
    except Exception as e:
        result["errors"].append(f"SST: {e}")

    from scripts.tess_phase_anomaly import PhaseAnomalyScorer
    from scripts.historical_tess import assemble_tess_from_parts
    from scripts.tess_conditional_probability import lookup_conditional_for_tess, platt_outbreak_probability
    from runtime.ingest.mjo_gulf_client import MJOGulfClient

    idx_hist = {
        "ao": ao_ser,
        "pna": pna_ser,
        "mei": mei_ser,
        "pdo": pdo_ser,
    }
    ph = PhaseAnomalyScorer().score_month(now, idx_hist)
    client = MJOGulfClient()
    load = client.get_loading_score(
        now.year, now.month, use_network=True, nino34_proxy=nino34a_current
    )
    sst_tail = sst_ser[-18:] if len(sst_ser) >= 3 else sst_ser
    core = assemble_tess_from_parts(ph, load, sst_tail, mei_ser, ao_ser)

    tess = core["tess_score"]
    result.update(core)
    result["tess_version"] = 2
    result["tess_is_forecast_probability"] = False
    result["outbreak_probability_platt"] = platt_outbreak_probability(tess)
    result["forecast_note"] = (
        "TESS v2 is a unitless composite, not P(outbreak). "
        "outbreak_probability_platt uses in-sample Platt scaling from data/tess_skill_calibration.json "
        "(cross-validate before publication)."
    )
    cond = lookup_conditional_for_tess(tess)
    result["conditional_probability"] = cond.get("conditional_probability")
    result["lift_vs_climatology"] = cond.get("lift_vs_climatology")
    result["risk_statement"] = cond.get("risk_statement")
    result["calibration_threshold_used"] = cond.get("threshold_used")
    result["outbreak_base_rate"] = cond.get("base_rate")

    if mei_current is not None and mei_current < -1.0:
        result["signals"].append("LA_NINA_STRONG")
    elif mei_current is not None and mei_current < -0.5:
        result["signals"].append("LA_NINA")
    if load.get("mjo_favorable"):
        result["signals"].append("MJO_FAVORABLE_567")
    if load.get("gulf_sst_anomaly", 0) > 0.5:
        result["signals"].append("GULF_SST_WARM")

    result["layers"]["origin"] = {
        "score": core["layer_origin"],
        "phase_anomaly": ph["phase_anomaly_score"],
        "mei": round(mei_current, 2) if mei_current is not None else None,
        "pdo": round(pdo_current, 2) if pdo_current is not None else None,
    }
    result["layers"]["transport"] = {
        "score": core["layer_transport"],
        "ao": round(ao_current, 2) if ao_current is not None else None,
        "pna": round(pna_current, 2) if pna_current is not None else None,
    }
    result["layers"]["loading"] = {
        "score": core["layer_loading"],
        "nino34_anom": round(nino34a_current, 2) if nino34a_current is not None else None,
        "mjo_phase": load["mjo_phase"],
        "mjo_amplitude": load["mjo_amplitude"],
        "gulf_sst_anomaly": load["gulf_sst_anomaly"],
    }

    result["layers_firing"] = core["layers_firing"]

    if tess >= 0.7:
        result["risk_level"] = "ELEVATED"
    elif tess >= 0.4:
        result["risk_level"] = "MODERATE"
    else:
        result["risk_level"] = "LOW"

    cache_path = ROOT / "runs" / "live_tess.json"
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(json.dumps(result, indent=2) + "\n")

    if cron_mode:
        err_n = len(result.get("errors") or [])
        platt = result.get("outbreak_probability_platt")
        platt_s = f"{platt:.4f}" if isinstance(platt, (int, float)) else "n/a"
        print(
            f"[GAIA TESS] ts={result['timestamp']} score={result.get('tess_score')} "
            f"risk={result.get('risk_level')} layers_firing={result.get('layers_firing')} "
            f"platt={platt_s} errors={err_n}",
            flush=True,
        )
    else:
        print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
