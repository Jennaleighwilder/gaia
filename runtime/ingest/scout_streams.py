"""
Sub-monthly 'scout' signals (daily AO, Gulf SST trend, Z500 proxy, MJO propagation, seasonality).
Z500 uses AO-derived proxy until real 500mb fields are wired. Gulf uses ERSSTv5 regional
monthly (MJOGulfClient) with month-to-month trend as a weekly-scale stand-in.
"""

from __future__ import annotations

import json
import urllib.request
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
CACHE_DIR = ROOT / "data" / "cache" / "scouts"
CACHE_DIR.mkdir(parents=True, exist_ok=True)


def _parse_iso(d: str) -> date:
    y, m, dd = d.split("-")
    return date(int(y), int(m), int(dd))


def _month_before(y: int, m: int) -> tuple[int, int]:
    if m == 1:
        return y - 1, 12
    return y, m - 1


class ScoutStreams:
    def __init__(self, *, use_network: bool = True) -> None:
        self.use_network = use_network

    # ── SCOUT 1: Daily AO ───────────────────────────────────────────────
    def get_daily_ao_series(self) -> list[tuple[str, float]]:
        cache = CACHE_DIR / "daily_ao.json"
        if cache.exists():
            age_days = (datetime.now() - datetime.fromtimestamp(cache.stat().st_mtime)).days
            if age_days < 1 or not self.use_network:
                try:
                    raw = json.loads(cache.read_text())
                    return [(str(a[0]), float(a[1])) for a in raw]
                except (json.JSONDecodeError, TypeError, ValueError, IndexError):
                    pass

        if not self.use_network:
            return []

        url = (
            "https://www.cpc.ncep.noaa.gov/products/precip/CWlink/daily_ao_index/"
            "daily.ao.index.b500.current.ascii"
        )
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "GAIA/1.0 (research)"})
            with urllib.request.urlopen(req, timeout=25) as r:
                data = r.read().decode("utf-8", errors="replace")
            records: list[tuple[str, float]] = []
            for line in data.strip().split("\n"):
                parts = line.split()
                if len(parts) >= 4:
                    try:
                        year, month, day = int(parts[0]), int(parts[1]), int(parts[2])
                        ao_val = float(parts[3])
                        date_str = f"{year}-{month:02d}-{day:02d}"
                        records.append((date_str, ao_val))
                    except (ValueError, IndexError):
                        continue
            cache.write_text(json.dumps(records))
            return records
        except Exception:
            if cache.exists():
                try:
                    raw = json.loads(cache.read_text())
                    return [(str(a[0]), float(a[1])) for a in raw]
                except (json.JSONDecodeError, TypeError, ValueError, IndexError):
                    pass
            return []

    def _monthly_ao_fallback(self, d: datetime) -> float:
        from scripts.historical_tess import _full_ao_through

        hist = _full_ao_through((d.year, d.month))
        return float(hist[-1]) if hist else 0.0

    def get_ao_plunge(self, d: datetime, window_days: int = 14) -> dict[str, Any]:
        series = self.get_daily_ao_series()
        date_str = d.strftime("%Y-%m-%d")
        if not series:
            ao_m = self._monthly_ao_fallback(d)
            return {
                "ao_daily": round(ao_m, 3),
                "ao_7day_mean": round(ao_m, 3),
                "ao_14day_mean": round(ao_m, 3),
                "ao_trend": 0.0,
                "ao_plunge_detected": False,
                "source": "monthly_fallback",
            }

        dates = [r[0] for r in series]
        vals = [r[1] for r in series]
        target = d.date() if isinstance(d, datetime) else d

        try:
            idx = dates.index(date_str)
        except ValueError:
            parsed = [_parse_iso(s) for s in dates]
            if not parsed:
                ao_m = self._monthly_ao_fallback(d)
                return {
                    "ao_daily": round(ao_m, 3),
                    "ao_7day_mean": round(ao_m, 3),
                    "ao_14day_mean": round(ao_m, 3),
                    "ao_trend": 0.0,
                    "ao_plunge_detected": False,
                    "source": "monthly_fallback",
                }
            idx = int(
                np.argmin([abs((parsed[i] - target).days) for i in range(len(parsed))])
            )
            if abs((parsed[idx] - target).days) > 45:
                ao_m = self._monthly_ao_fallback(d)
                return {
                    "ao_daily": round(ao_m, 3),
                    "ao_7day_mean": round(ao_m, 3),
                    "ao_14day_mean": round(ao_m, 3),
                    "ao_trend": 0.0,
                    "ao_plunge_detected": False,
                    "source": "monthly_fallback",
                }

        start = max(0, idx - window_days)
        window_vals = vals[start : idx + 1]
        if len(window_vals) < 2:
            ao_now = vals[idx] if idx < len(vals) else 0.0
            return {
                "ao_daily": round(ao_now, 3),
                "ao_7day_mean": round(ao_now, 3),
                "ao_14day_mean": round(ao_now, 3),
                "ao_trend": 0.0,
                "ao_plunge_detected": False,
                "source": "daily_ao",
            }

        ao_now = vals[idx]
        ao_start = window_vals[0]
        trend = ao_now - ao_start
        return {
            "ao_daily": round(ao_now, 3),
            "ao_7day_mean": round(float(np.mean(vals[max(0, idx - 6) : idx + 1])), 3),
            "ao_14day_mean": round(float(np.mean(window_vals)), 3),
            "ao_trend": round(float(trend), 3),
            "ao_plunge_detected": bool(trend < -1.5),
            "source": "daily_ao",
        }

    # ── SCOUT 2: Gulf SST (monthly ERSST + month-over-month trend) ─────
    def get_gulf_sst(self, d: datetime) -> dict[str, Any]:
        from runtime.ingest.mjo_gulf_client import MJOGulfClient

        client = MJOGulfClient()
        y, m = d.year, d.month
        yp, mp = _month_before(y, m)
        sst = client.get_gulf_sst_anomaly(y, m, use_network=self.use_network)
        sst_prev = client.get_gulf_sst_anomaly(yp, mp, use_network=self.use_network)
        trend = float(sst) - float(sst_prev)
        warm_pulse = bool(sst > 0.8 and trend > 0.05)
        return {
            "gulf_sst_anomaly": round(float(sst), 3),
            "gulf_sst_trend": round(trend, 3),
            "gulf_warm_pulse": warm_pulse,
            "source": "ersst_monthly_trend",
        }

    # ── SCOUT 3: Z500 proxy (AO) ────────────────────────────────────────
    def get_z500_anomaly(self, d: datetime) -> dict[str, Any]:
        cache = CACHE_DIR / f"z500_{d.year}{d.month:02d}.json"
        if cache.exists() and not self.use_network:
            try:
                return json.loads(cache.read_text())
            except json.JSONDecodeError:
                pass

        ao_data = self.get_ao_plunge(d)
        ao_val = float(ao_data.get("ao_14day_mean", ao_data.get("ao_daily", 0)))
        z500_proxy = ao_val * -30.0
        trough = bool(z500_proxy < -20)
        result = {
            "z500_anomaly": round(z500_proxy, 1),
            "trough_deepening": bool(trough and float(ao_data.get("ao_trend", 0)) < -0.5),
            "jet_amplification": round(abs(z500_proxy) / 30.0, 3),
            "source": "ao_proxy",
        }
        try:
            cache.write_text(json.dumps(result))
        except OSError:
            pass
        return result

    # ── SCOUT 4: MJO propagation (daily RMM) ────────────────────────────
    def get_mjo_propagation(self, d: datetime) -> dict[str, Any]:
        from runtime.ingest.mjo_gulf_client import MJOGulfClient

        client = MJOGulfClient()
        cur = client.get_mjo_for_date(d.year, d.month, d.day, use_network=self.use_network)
        prev_d = d - timedelta(days=14)
        prev = client.get_mjo_for_date(
            prev_d.year, prev_d.month, prev_d.day, use_network=self.use_network
        )
        cp = int(cur.get("phase", 0) or 0)
        pp = int(prev.get("phase", 0) or 0)
        ca = float(cur.get("amplitude", 0) or 0)
        pa = float(prev.get("amplitude", 0) or 0)
        favorable_phases = {5, 6, 7}
        favorable = bool(cp in favorable_phases and ca > 1.0)
        approaching = False
        if not favorable and cp and pp:
            if pp in {3, 4} and cp in {4, 5, 6}:
                approaching = True
            if pp == 8 and cp in {1, 2}:
                approaching = False
        return {
            "mjo_phase": cp,
            "mjo_amplitude": round(ca, 3),
            "mjo_favorable": favorable,
            "mjo_approaching_favorable": approaching,
            "mjo_strengthening": bool(ca > pa + 0.3),
            "mjo_phase_14d_ago": pp,
        }

    # ── SCOUT 5: Seasonal loading ───────────────────────────────────────
    def get_seasonal_loading(self, d: datetime) -> dict[str, Any]:
        month = d.month
        day_of_year = d.timetuple().tm_yday
        in_primary = 74 <= day_of_year <= 151
        in_secondary = day_of_year >= 319
        in_season = in_primary or in_secondary
        in_peak = 91 <= day_of_year <= 135
        gulf_gradient_season = month in (3, 4)
        if in_peak:
            season_score = 0.9
        elif in_primary:
            season_score = 0.7
        elif in_secondary:
            season_score = 0.6
        else:
            season_score = 0.1
        return {
            "in_outbreak_season": in_season,
            "in_peak_season": in_peak,
            "gulf_gradient_season": gulf_gradient_season,
            "season_score": season_score,
            "day_of_year": day_of_year,
        }

    def get_all_scouts(self, d: datetime) -> dict[str, Any]:
        ao = self.get_ao_plunge(d)
        gulf = self.get_gulf_sst(d)
        z500 = self.get_z500_anomaly(d)
        mjo = self.get_mjo_propagation(d)
        seasonal = self.get_seasonal_loading(d)

        signals: list[str] = []
        score = 0.0
        if ao.get("ao_plunge_detected"):
            signals.append("AO_PLUNGE")
            score += 0.25
        elif float(ao.get("ao_daily", 0)) < -1.0:
            signals.append("AO_NEGATIVE")
            score += 0.12

        if gulf.get("gulf_warm_pulse"):
            signals.append("GULF_WARM_PULSE")
            score += 0.20
        elif float(gulf.get("gulf_sst_anomaly", 0)) > 0.3:
            score += 0.08

        if z500.get("trough_deepening"):
            signals.append("TROUGH_DEEPENING")
            score += 0.25
        elif float(z500.get("z500_anomaly", 0)) < -15:
            score += 0.10

        if mjo.get("mjo_favorable"):
            signals.append("MJO_FAVORABLE")
            score += 0.15
        elif mjo.get("mjo_approaching_favorable"):
            signals.append("MJO_APPROACHING")
            score += 0.08

        seasonal_mult = 0.5 + float(seasonal["season_score"]) * 0.5
        score = score * seasonal_mult
        if seasonal["in_peak_season"]:
            signals.append("PEAK_SEASON")

        level = "WARNING" if score > 0.60 else "WATCH" if score > 0.35 else "CLEAR"
        return {
            "scouts": {"ao": ao, "gulf": gulf, "z500": z500, "mjo": mjo, "seasonal": seasonal},
            "scout_signals_firing": len(signals),
            "scout_composite_score": round(score, 3),
            "scout_alert_level": level,
            "scout_key_signals": signals,
            "features": {
                "ao_daily": float(ao.get("ao_daily", 0)),
                "ao_trend_14d": float(ao.get("ao_trend", 0)),
                "ao_plunge": 1.0 if ao.get("ao_plunge_detected") else 0.0,
                "scout_gulf_ssta": float(gulf.get("gulf_sst_anomaly", 0)),
                "gulf_sst_trend": float(gulf.get("gulf_sst_trend", 0)),
                "gulf_warm_pulse": 1.0 if gulf.get("gulf_warm_pulse") else 0.0,
                "z500_proxy": float(z500.get("z500_anomaly", 0)),
                "trough_deepening": 1.0 if z500.get("trough_deepening") else 0.0,
                "scout_mjo_amp": float(mjo.get("mjo_amplitude", 0)),
                "scout_mjo_fav": 1.0 if mjo.get("mjo_favorable") else 0.0,
                "scout_mjo_approach": 1.0 if mjo.get("mjo_approaching_favorable") else 0.0,
                "scout_season_score": float(seasonal["season_score"]),
                "scout_in_peak": 1.0 if seasonal["in_peak_season"] else 0.0,
            },
        }
