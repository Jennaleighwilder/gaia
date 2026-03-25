"""
Historical TESS: phase-anomaly climate layers + MJO/Gulf loading (Fix 1–2).

Uses data/global_indices/* plus optional network for MJO RMM cache and Gulf ERDDAP.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
IDX = ROOT / "data" / "global_indices"


def _full_ao_through(ym: tuple[int, int]) -> list[float]:
    rows: list[tuple[int, int, float]] = []
    path = IDX / "ao_monthly.dat"
    if not path.exists():
        return []
    for line in path.read_text().splitlines():
        parts = line.split()
        if len(parts) >= 3:
            try:
                y, m, v = int(parts[0]), int(parts[1]), float(parts[2])
                if (y, m) <= ym:
                    rows.append((y, m, v))
            except (ValueError, IndexError):
                pass
    rows.sort()
    return [v for _, _, v in rows]


def _full_pna_through(ym: tuple[int, int]) -> list[float]:
    rows: list[tuple[int, int, float]] = []
    path = IDX / "pna_monthly.dat"
    if not path.exists():
        return []
    for line in path.read_text().splitlines():
        parts = line.split()
        if len(parts) >= 3:
            try:
                y, m, v = int(parts[0]), int(parts[1]), float(parts[2])
                if (y, m) <= ym:
                    rows.append((y, m, v))
            except (ValueError, IndexError):
                pass
    rows.sort()
    return [v for _, _, v in rows]


def _full_mei_through(ym: tuple[int, int]) -> list[float]:
    rows: list[tuple[int, int, float]] = []
    path = IDX / "mei_v2.dat"
    if not path.exists():
        return []
    for line in path.read_text().splitlines():
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
                if v > -900 and (year, m) <= ym:
                    rows.append((year, m, v))
            except (ValueError, IndexError):
                pass
    rows.sort()
    return [v for _, _, v in rows]


def _full_pdo_through(ym: tuple[int, int]) -> list[float]:
    flat: list[float] = []
    path = IDX / "pdo.dat"
    if not path.exists():
        return []
    for line in path.read_text().splitlines():
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


def _load_nino34_through(ym: tuple[int, int]) -> tuple[list[float], float | None]:
    rows: list[tuple[int, int, float]] = []
    path = IDX / "sst_indices.dat"
    if not path.exists():
        return [], None
    for line in path.read_text().splitlines():
        parts = line.split()
        if len(parts) < 8:
            continue
        try:
            y, m = int(parts[0]), int(parts[1])
            anom = float(parts[7])
            if (y, m) <= ym:
                rows.append((y, m, anom))
        except (ValueError, IndexError):
            continue
    rows.sort()
    tail = rows[-18:]
    vals = [v for _, _, v in tail]
    cur = tail[-1][2] if tail else None
    return vals, cur


def _uvrk1(values: list[float]) -> float:
    from scripts.live_tess_score import uvrk1_instability

    return uvrk1_instability(values)


def assemble_tess_from_parts(
    ph: dict[str, Any],
    load: dict[str, Any],
    sst_vals: list[float],
    mei_tail: list[float] | None = None,
    ao_tail: list[float] | None = None,
) -> dict[str, Any]:
    """Shared live + historical assembly (phase + UVRK blend, MJO/Gulf loading, SST residual)."""
    origin = float(ph["origin_phase_score"])
    if mei_tail and len(mei_tail) >= 3:
        origin = min(1.0, 0.48 * origin + 0.52 * _uvrk1(mei_tail[-18:]))
    transport = float(ph["transport_phase_score"])
    if ao_tail and len(ao_tail) >= 3:
        transport = min(1.0, 0.48 * transport + 0.52 * _uvrk1(ao_tail[-18:]))
    loading = float(load["loading_score"])
    if sst_vals:
        loading = min(1.0, loading + _uvrk1(sst_vals) * 0.12)

    layers_firing = sum(1 for s in (origin, transport, loading) if s >= 0.5)
    tess = origin * 0.35 + transport * 0.35 + loading * 0.30
    if layers_firing >= 3:
        tess = min(1.0, tess * 1.25)
    elif layers_firing >= 2:
        tess = min(1.0, tess * 1.08)

    tess = round(float(tess), 3)
    return {
        "tess_score": tess,
        "phase_anomaly_score": ph["phase_anomaly_score"],
        "origin_phase_score": ph["origin_phase_score"],
        "transport_phase_score": ph["transport_phase_score"],
        "combined_anomaly_z": ph["combined_anomaly"],
        "anomalies": ph["anomalies"],
        "mjo_phase": load["mjo_phase"],
        "mjo_amplitude": load["mjo_amplitude"],
        "mjo_favorable": load["mjo_favorable"],
        "gulf_sst_anomaly": load["gulf_sst_anomaly"],
        "loading_score": load["loading_score"],
        "layer_origin": round(origin, 3),
        "layer_transport": round(transport, 3),
        "layer_loading": round(loading, 3),
        "layers_firing": layers_firing,
    }


def compute_tess_full(
    as_of: datetime,
    *,
    neutral: bool = False,
    use_network: bool = False,
    include_scouts: bool = False,
) -> dict[str, Any]:
    """
    Full TESS breakdown for historical months (offline indices + MJO/Gulf loading).
    """
    ym = (as_of.year, as_of.month)
    ao_f = _full_ao_through(ym)
    pna_f = _full_pna_through(ym)
    mei_f = _full_mei_through(ym)
    pdo_f = _full_pdo_through(ym)
    sst_vals, nino_cur = _load_nino34_through(ym)

    if not neutral and not any([ao_f, pna_f, mei_f, pdo_f, sst_vals]):
        raise FileNotFoundError(
            f"No index data under {IDX}. Populate data/global_indices/ for historical TESS."
        )

    if neutral:
        return {
            "tess_score": 0.05,
            "phase_anomaly_score": 0.0,
            "origin_phase_score": 0.0,
            "transport_phase_score": 0.0,
            "mjo_phase": 0,
            "mjo_amplitude": 0.0,
            "mjo_favorable": False,
            "gulf_sst_anomaly": 0.0,
            "loading_score": 0.0,
            "layer_origin": 0.0,
            "layer_transport": 0.0,
            "layer_loading": 0.0,
            "layers_firing": 0,
            "anomalies": {},
        }

    from scripts.tess_phase_anomaly import PhaseAnomalyScorer

    scorer = PhaseAnomalyScorer()
    idx_hist = {"ao": ao_f, "pna": pna_f, "mei": mei_f, "pdo": pdo_f}
    ph = scorer.score_month(as_of, idx_hist)

    from runtime.ingest.mjo_gulf_client import MJOGulfClient

    client = MJOGulfClient()
    load = client.get_loading_score(
        as_of.year,
        as_of.month,
        use_network=use_network,
        nino34_proxy=nino_cur,
    )
    out = assemble_tess_from_parts(ph, load, sst_vals, mei_f, ao_f)
    if include_scouts:
        try:
            from runtime.ingest.scout_streams import ScoutStreams

            s = ScoutStreams(use_network=use_network).get_all_scouts(as_of)
            out["scout_composite_score"] = s["scout_composite_score"]
            out["scout_alert_level"] = s["scout_alert_level"]
            out["scout_key_signals"] = s["scout_key_signals"]
            out["scout_features"] = s["features"]
        except Exception:
            out["scout_composite_score"] = 0.0
            out["scout_alert_level"] = "CLEAR"
            out["scout_key_signals"] = []
            out["scout_features"] = {}
    return out


def compute_tess_score(as_of: datetime, *, neutral: bool = False, use_network: bool = False) -> float:
    return float(
        compute_tess_full(as_of, neutral=neutral, use_network=use_network)["tess_score"]
    )


# --- Legacy 18-month tail accessors (used by older callers / tests) ---

def _load_ao_through(ym: tuple[int, int]) -> tuple[list[float], float | None]:
    full = _full_ao_through(ym)
    tail = full[-18:]
    return tail, tail[-1] if tail else None


def _load_pna_through(ym: tuple[int, int]) -> tuple[list[float], float | None]:
    full = _full_pna_through(ym)
    tail = full[-18:]
    return tail, tail[-1] if tail else None


def _load_mei_through(ym: tuple[int, int]) -> tuple[list[float], float | None]:
    full = _full_mei_through(ym)
    tail = full[-18:]
    return tail, tail[-1] if tail else None


def _load_pdo_through(ym: tuple[int, int]) -> tuple[list[float], float | None]:
    full = _full_pdo_through(ym)
    tail = full[-18:]
    return tail, tail[-1] if tail else None
