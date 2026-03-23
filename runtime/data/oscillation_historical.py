"""
Historical ENSO/oscillation lookup by date.

Uses NOAA MEI v2 (Multivariate ENSO Index) for date-aware oscillation scores.
MEI > 0.5 = El Nino (suppresses TN severe) -> 0.3
MEI < -0.5 = La Nina (enhances TN severe) -> 0.8
else = Neutral -> 0.5

Backtest uses this; real-time falls back to static oscillation_state.json.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

# MEI file: year in col 0, then 12 values for 2-month seasons:
# DJ JF FM MA AM MJ JJ JA AS SO ON ND
# For month M we use the season that contains M as the latter month.
# Jan->JF(1), Feb->FM(2), Mar->MA(3), Apr->AM(4), May->MJ(5), Jun->JJ(6),
# Jul->JA(7), Aug->AS(8), Sep->SO(9), Oct->ON(10), Nov->ND(11), Dec->DJ(12)
MONTH_TO_COL = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]  # 1-indexed month -> col index

_MEI_CACHE: dict[tuple[int, int], float] = {}
_MEI_LOADED = False


def _default_mei_path() -> Path:
    return Path(__file__).resolve().parent.parent.parent / "tests" / "fixtures" / "mei_enso_index.dat"


def _load_mei(mei_path: Optional[Path] = None) -> None:
    global _MEI_LOADED, _MEI_CACHE
    if _MEI_LOADED:
        return
    path = mei_path or _default_mei_path()
    if not path.exists():
        _MEI_LOADED = True
        return
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            parts = line.split()
            if len(parts) < 13:
                continue
            try:
                year = int(parts[0])
                for month in range(1, 13):
                    val = float(parts[month])
                    if val < -900:  # missing
                        continue
                    _MEI_CACHE[(year, month)] = val
            except (ValueError, IndexError):
                continue
    _MEI_LOADED = True


def get_mei(year: int, month: int, mei_path: Optional[Path] = None) -> Optional[float]:
    """Return MEI value for year/month, or None if not available."""
    _load_mei(mei_path)
    return _MEI_CACHE.get((year, month))


def get_enso_phase(year: int, month: int, mei_path: Optional[Path] = None) -> str:
    """Return 'el_nino' | 'la_nina' | 'neutral' for date."""
    mei = get_mei(year, month, mei_path)
    if mei is None:
        return "neutral"
    if mei > 0.5:
        return "el_nino"
    if mei < -0.5:
        return "la_nina"
    return "neutral"


def get_enso_score(year: int, month: int, mei_path: Optional[Path] = None) -> float:
    """
    Return oscillation score for date from MEI.
    el_nino: 0.3 (suppresses TN severe)
    neutral: 0.5
    la_nina: 0.8 (enhances TN severe)
    """
    phase = get_enso_phase(year, month, mei_path)
    return {"el_nino": 0.3, "neutral": 0.5, "la_nina": 0.8}.get(phase, 0.5)


def parse_date(timestamp_or_date: str) -> Optional[tuple[int, int]]:
    """Parse 'YYYY-MM-DD' or ISO timestamp to (year, month)."""
    if not timestamp_or_date:
        return None
    s = str(timestamp_or_date).strip()
    if "T" in s:
        s = s.split("T")[0]
    parts = s.split("-")
    if len(parts) >= 2:
        try:
            year = int(parts[0])
            month = int(parts[1])
            if 1 <= month <= 12 and 1979 <= year <= 2030:
                return (year, month)
        except (ValueError, IndexError):
            pass
    return None
