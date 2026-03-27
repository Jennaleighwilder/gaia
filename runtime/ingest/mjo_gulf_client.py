"""
MJO (RMM1/RMM2) and Gulf-of-Mexico SSTa for the TESS loading layer.

Primary RMM source: Stony Brook RMM-r daily file (NOAA/BOM HTTP often blocks bots).
Gulf: NOAA ERSSTv5 ssta via ERDDAP (region mean), with disk cache + Niño proxy fallback.
"""

from __future__ import annotations

import json
import math
import re
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CACHE_DIR = ROOT / "data" / "cache"
RMM_URL_PRIMARY = "https://mjo.somas.stonybrook.edu/MJO/RMM-r/rmm1+2.txt"
RMM_URL_FALLBACK = "http://www.bom.gov.au/climate/mjo/graphics/rmm.74toRealtime.txt"

_MONTHS = (
    "JAN",
    "FEB",
    "MAR",
    "APR",
    "MAY",
    "JUN",
    "JUL",
    "AUG",
    "SEP",
    "OCT",
    "NOV",
    "DEC",
)


def _month_num(mon: str) -> int:
    return _MONTHS.index(mon.upper()) + 1


def _wh_phase(rmm1: float, rmm2: float) -> int:
    """Wheeler–Hendon-style octant (1–8) from RMM1/RMM2."""
    deg = math.degrees(math.atan2(rmm2, rmm1))
    if deg < 0:
        deg += 360.0
    p = int(((deg + 22.5) % 360) // 45) + 1
    return max(1, min(8, p))


class MJOGulfClient:
    def __init__(self, cache_dir: Path | None = None) -> None:
        self.cache_dir = cache_dir or CACHE_DIR
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._rmm_lines: list[str] | None = None
        self._gulf_cache: dict[str, float] = {}
        self._gulf_cache_path = self.cache_dir / "gulf_ssta_monthly.json"
        if self._gulf_cache_path.exists():
            try:
                self._gulf_cache = json.loads(self._gulf_cache_path.read_text())
            except json.JSONDecodeError:
                self._gulf_cache = {}

    def _load_rmm_text(self, use_network: bool) -> str:
        local = self.cache_dir / "mjo_rmm.txt"
        if local.exists() and local.stat().st_size > 1000:
            return local.read_text()
        if not use_network:
            return ""
        for url in (RMM_URL_PRIMARY, RMM_URL_FALLBACK):
            try:
                req = urllib.request.Request(
                    url,
                    headers={"User-Agent": "GAIA/1.0 (research; +https://github.com/)"},
                )
                with urllib.request.urlopen(req, timeout=45) as r:
                    text = r.read().decode("utf-8", errors="replace")
                if "rmm1" in text.lower() or "RMM" in text:
                    local.write_text(text)
                    return text
            except Exception:
                continue
        return local.read_text() if local.exists() else ""

    def _parse_rmm_daily(self, text: str) -> list[tuple[datetime, float, float]]:
        rows: list[tuple[datetime, float, float]] = []
        # Stony Brook: 00Z27APR2011   -0.197189    -0.455387
        pat_sb = re.compile(
            r"^\s*00Z\s*(\d{1,2})([A-Z]{3})(\d{4})\s+([-\d.]+)\s+([-\d.]+)\s*$",
            re.I,
        )
        for line in text.splitlines():
            line = line.strip()
            if not line or line.lower().startswith("date"):
                continue
            m = pat_sb.match(line)
            if m:
                d, mon, y, a, b = m.groups()
                try:
                    dt = datetime(int(y), _month_num(mon), int(d), tzinfo=timezone.utc)
                    rows.append((dt, float(a), float(b)))
                except (ValueError, IndexError):
                    pass
                continue
            # BOM-style: year month day rmm1 rmm2 phase (best-effort)
            parts = line.split()
            if len(parts) >= 5 and parts[0].isdigit():
                try:
                    yy, mm, dd = int(parts[0]), int(parts[1]), int(parts[2])
                    dt = datetime(yy, mm, min(dd, 28), tzinfo=timezone.utc)
                    rows.append((dt, float(parts[3]), float(parts[4])))
                except (ValueError, IndexError):
                    pass
        rows.sort(key=lambda t: t[0])
        return rows

    def get_mjo_for_date(self, year: int, month: int, day: int, *, use_network: bool = True) -> dict:
        """Single-day RMM (for case studies, e.g. 2011-04-27)."""
        text = self._load_rmm_text(use_network)
        if not text:
            return {"phase": 0, "amplitude": 0.0, "favorable": False, "source": "none"}
        daily = self._parse_rmm_daily(text)
        for d, r1, r2 in daily:
            if d.year == year and d.month == month and d.day == day:
                ph = _wh_phase(r1, r2)
                amp = math.sqrt(r1 * r1 + r2 * r2)
                return {
                    "phase": ph,
                    "amplitude": round(amp, 3),
                    "favorable": ph in (5, 6, 7) and amp > 1.0,
                    "source": "rmm_daily",
                }
        return {"phase": 0, "amplitude": 0.0, "favorable": False, "source": "no_data"}

    def get_mjo_for_month(self, year: int, month: int, *, use_network: bool = True) -> dict:
        text = self._load_rmm_text(use_network)
        if not text:
            return {"phase": 0, "amplitude": 0.0, "favorable": False, "source": "none"}
        daily = self._parse_rmm_daily(text)
        in_month = [(d, r1, r2) for d, r1, r2 in daily if d.year == year and d.month == month]
        if not in_month:
            return {"phase": 0, "amplitude": 0.0, "favorable": False, "source": "no_data"}

        rmm1s = [t[1] for t in in_month]
        rmm2s = [t[2] for t in in_month]
        r1 = sum(rmm1s) / len(rmm1s)
        r2 = sum(rmm2s) / len(rmm2s)
        phases = [_wh_phase(a, b) for a, b in zip(rmm1s, rmm2s)]
        phase = Counter(phases).most_common(1)[0][0]
        amplitude = math.sqrt(r1 * r1 + r2 * r2)
        favorable = phase in (5, 6, 7) and amplitude > 1.0
        return {
            "phase": phase,
            "amplitude": round(amplitude, 3),
            "favorable": favorable,
            "source": "rmm",
        }

    def _fetch_gulf_erddap(self, year: int, month: int) -> float | None:
        t = f"{year}-{month:02d}-15T12:00:00Z"
        url = (
            "https://coastwatch.pfeg.noaa.gov/erddap/griddap/nceiErsstv5.json?"
            f"ssta%5B({t})%5D%5B(0):1:(0)%5D%5B(18):1:(30)%5D%5B(260):1:(280)%5D"
        )
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "GAIA/1.0"})
            with urllib.request.urlopen(req, timeout=25) as r:
                payload = json.loads(r.read().decode("utf-8", errors="replace"))
            vals: list[float] = []
            for row in payload.get("table", {}).get("rows", []):
                if len(row) >= 5 and row[4] is not None:
                    try:
                        vals.append(float(row[4]))
                    except (TypeError, ValueError):
                        pass
            if not vals:
                return None
            return sum(vals) / len(vals)
        except Exception:
            return None

    def get_gulf_sst_anomaly(
        self, year: int, month: int, *, use_network: bool = True, nino34_proxy: float | None = None
    ) -> float:
        key = f"{year}-{month:02d}"
        if key in self._gulf_cache:
            return float(self._gulf_cache[key])
        g: float | None = None
        if use_network:
            g = self._fetch_gulf_erddap(year, month)
        if g is None and nino34_proxy is not None:
            # Warm Atlantic / Gulf often decouples from Niño; crude proxy only
            g = max(-1.5, min(1.5, -0.35 * nino34_proxy + 0.15))
        if g is None:
            g = 0.0
        self._gulf_cache[key] = g
        try:
            self._gulf_cache_path.write_text(json.dumps(self._gulf_cache, indent=0) + "\n")
        except OSError:
            pass
        return float(g)

    def get_loading_score(
        self,
        year: int,
        month: int,
        *,
        use_network: bool = True,
        nino34_proxy: float | None = None,
    ) -> dict:
        mjo = self.get_mjo_for_month(year, month, use_network=use_network)
        gulf_sst = self.get_gulf_sst_anomaly(
            year, month, use_network=use_network, nino34_proxy=nino34_proxy
        )

        score = 0.0
        if mjo["favorable"] and mjo["amplitude"] > 1.5:
            score += 0.40
        elif mjo["favorable"]:
            score += 0.25
        elif mjo["phase"] in (1, 2, 8) and mjo["amplitude"] > 1.0:
            score -= 0.10

        if gulf_sst > 1.0:
            score += 0.30
        elif gulf_sst > 0.5:
            score += 0.20
        elif gulf_sst < -0.5:
            score -= 0.10

        if month in (3, 4, 5):
            score += 0.15
        elif month in (11, 12):
            score += 0.10

        return {
            "mjo_phase": mjo["phase"],
            "mjo_amplitude": mjo["amplitude"],
            "mjo_favorable": mjo["favorable"],
            "gulf_sst_anomaly": round(gulf_sst, 3),
            "loading_score": round(min(1.0, max(0.0, score)), 3),
            "mjo_source": mjo.get("source", ""),
        }
