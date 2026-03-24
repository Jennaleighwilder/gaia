"""
GAIA Sounding Client — fetches real upper-air radiosonde data.

Sources: University of Wyoming archive via Siphon.
Computes CAPE, CIN, SRH, LCL, bulk shear, STP, SCP using MetPy.

Twice-daily (00Z, 12Z). Results cached to disk.
"""

from __future__ import annotations

import json
import math
import warnings
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

warnings.filterwarnings("ignore")

ROOT = Path(__file__).resolve().parents[2]
CACHE_DIR = ROOT / "runs" / "soundings"

STATIONS = {
    "72327": {"name": "Nashville", "icao": "KBNA", "lat": 36.25, "lon": -86.57},
    "72230": {"name": "Birmingham", "icao": "KBMX", "lat": 33.18, "lon": -86.77},
    "72235": {"name": "Jackson MS", "icao": "KJAN", "lat": 32.32, "lon": -90.08},
    "72317": {"name": "Greensboro", "icao": "KGSO", "lat": 36.10, "lon": -79.95},
    "72340": {"name": "Little Rock", "icao": "KLZK", "lat": 34.83, "lon": -92.26},
    "72451": {"name": "Dodge City", "icao": "KDDC", "lat": 37.77, "lon": -99.97},
    "72440": {"name": "Springfield MO", "icao": "KSGF", "lat": 37.24, "lon": -93.40},
    "74560": {"name": "Lincoln IL", "icao": "KILX", "lat": 40.15, "lon": -89.34},
    "72249": {"name": "Shreveport", "icao": "KSHV", "lat": 32.45, "lon": -93.84},
    "72248": {"name": "Shelby MS", "icao": "KMEG", "lat": 33.81, "lon": -90.08},
    "72364": {"name": "Paducah", "icao": "KPAH", "lat": 37.07, "lon": -88.77},
}


def fetch_sounding(station_id: str, dt: datetime) -> dict[str, Any] | None:
    """Fetch and compute derived sounding parameters for one station/time."""
    try:
        from siphon.simplewebservice.wyoming import WyomingUpperAir
        import metpy.calc as mpcalc
        from metpy.units import units
    except ImportError:
        return None

    try:
        df = WyomingUpperAir.request_data(dt, station_id)
    except Exception:
        return None

    if df is None or len(df) < 10:
        return None

    p = df["pressure"].values * units.hPa
    T = df["temperature"].values * units.degC
    Td = df["dewpoint"].values * units.degC
    u = df["u_wind"].values * units("knot")
    v = df["v_wind"].values * units("knot")
    z = df["height"].values * units.meter

    result: dict[str, Any] = {
        "station_id": station_id,
        "station_name": STATIONS.get(station_id, {}).get("name", station_id),
        "time": dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "sfc_temp_c": round(T[0].magnitude, 1),
        "sfc_dewpoint_c": round(Td[0].magnitude, 1),
        "sfc_pressure_mb": round(p[0].magnitude, 1),
    }

    try:
        sbcape, sbcin = mpcalc.surface_based_cape_cin(p, T, Td)
        result["sbcape_jkg"] = round(float(sbcape.magnitude), 0)
        result["sbcin_jkg"] = round(float(sbcin.magnitude), 0)
    except Exception:
        result["sbcape_jkg"] = 0
        result["sbcin_jkg"] = 0

    try:
        mucape, mucin = mpcalc.most_unstable_cape_cin(p, T, Td)
        result["mucape_jkg"] = round(float(mucape.magnitude), 0)
    except Exception:
        result["mucape_jkg"] = 0

    try:
        srh_pos, srh_neg, srh_total = mpcalc.storm_relative_helicity(
            z, u, v, depth=3000 * units.meter
        )
        result["srh_0_3km_m2s2"] = round(float(srh_total.magnitude), 0)
    except Exception:
        result["srh_0_3km_m2s2"] = 0

    try:
        srh1_pos, srh1_neg, srh1_total = mpcalc.storm_relative_helicity(
            z, u, v, depth=1000 * units.meter
        )
        result["srh_0_1km_m2s2"] = round(float(srh1_total.magnitude), 0)
    except Exception:
        result["srh_0_1km_m2s2"] = 0

    try:
        lcl_p, lcl_t = mpcalc.lcl(p[0], T[0], Td[0])
        lcl_idx = abs(p - lcl_p).argmin()
        result["lcl_height_agl_m"] = round(float((z[lcl_idx] - z[0]).magnitude), 0)
    except Exception:
        result["lcl_height_agl_m"] = 3000

    try:
        u6 = mpcalc.bulk_shear(p, u, v, depth=6000 * units.meter)
        shear_mag = mpcalc.wind_speed(u6[0], u6[1])
        result["bulk_shear_0_6km_kts"] = round(float(shear_mag.to("knot").magnitude), 1)
    except Exception:
        result["bulk_shear_0_6km_kts"] = 0

    # Significant Tornado Parameter
    cape = result["sbcape_jkg"]
    srh = abs(result["srh_0_3km_m2s2"])
    lcl = result["lcl_height_agl_m"]
    shear = result["bulk_shear_0_6km_kts"]

    cape_term = min(cape / 1500.0, 2.0) if cape > 0 else 0
    srh_term = min(srh / 150.0, 2.0)
    lcl_term = max(0, (2000 - lcl) / 1000.0) if lcl < 2000 else 0
    shear_term = min(shear / 40.0, 1.5) if shear > 0 else 0
    stp = cape_term * srh_term * lcl_term * max(0.5, shear_term)
    result["significant_tornado_parameter"] = round(stp, 3)

    # Supercell Composite Parameter
    scp_shear = min(shear / 40.0, 1.5) if shear > 0 else 0
    scp = (cape / 1000.0) * (srh / 50.0) * scp_shear if cape > 0 and srh > 0 else 0
    result["supercell_composite"] = round(min(scp, 20.0), 3)

    # Energy-Helicity Index (0-1km SRH)
    srh1 = abs(result.get("srh_0_1km_m2s2", 0))
    ehi = (cape * srh1) / 160000.0 if cape > 0 and srh1 > 0 else 0
    result["energy_helicity_index_0_1km"] = round(ehi, 3)

    return result


def fetch_all_soundings(dt: datetime | None = None) -> dict:
    """Fetch soundings for all stations at the given time. Caches to disk."""
    if dt is None:
        now = datetime.now(timezone.utc)
        hour = 12 if now.hour >= 9 else 0
        dt = now.replace(hour=hour, minute=0, second=0, microsecond=0)

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_key = dt.strftime("%Y%m%d_%HZ")
    cache_file = CACHE_DIR / f"soundings_{cache_key}.json"

    if cache_file.exists():
        return json.loads(cache_file.read_text())

    soundings = []
    for sid in STATIONS:
        s = fetch_sounding(sid, dt)
        if s:
            soundings.append(s)

    output = {
        "time": dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "stations": soundings,
        "station_count": len(soundings),
    }

    # Compute regional max STP for dashboard
    stps = [s.get("significant_tornado_parameter", 0) for s in soundings]
    capes = [s.get("sbcape_jkg", 0) for s in soundings]
    srhs = [abs(s.get("srh_0_3km_m2s2", 0)) for s in soundings]
    output["regional_max_stp"] = max(stps) if stps else 0
    output["regional_max_cape"] = max(capes) if capes else 0
    output["regional_max_srh"] = max(srhs) if srhs else 0

    if output["regional_max_stp"] >= 3.0:
        output["sounding_risk"] = "EXTREME"
    elif output["regional_max_stp"] >= 1.0:
        output["sounding_risk"] = "SIGNIFICANT"
    elif output["regional_max_stp"] >= 0.5:
        output["sounding_risk"] = "MODERATE"
    elif output["regional_max_cape"] >= 1500:
        output["sounding_risk"] = "ELEVATED"
    else:
        output["sounding_risk"] = "LOW"

    cache_file.write_text(json.dumps(output, indent=2) + "\n")
    # Also write as latest for dashboard
    (CACHE_DIR.parent / "live_soundings.json").write_text(json.dumps(output, indent=2) + "\n")

    return output


def format_table(data: dict) -> str:
    """Pretty-print sounding table."""
    lines = []
    lines.append(f"Upper-Air Soundings: {data['time']}")
    lines.append(f"Stations: {data['station_count']} | Risk: {data.get('sounding_risk', '?')}")
    lines.append(f"Regional max — STP: {data['regional_max_stp']:.2f} | CAPE: {data['regional_max_cape']:.0f} J/kg | SRH: {data['regional_max_srh']:.0f} m²/s²")
    lines.append("")
    hdr = f"{'Station':16s} | {'SBCAPE':>7s} | {'MUCAPE':>7s} | {'SRH 3km':>7s} | {'STP':>6s} | {'LCL':>5s} | {'Shear':>5s} | {'T':>5s} | {'Td':>5s}"
    lines.append(hdr)
    lines.append("-" * len(hdr))
    for s in sorted(data["stations"], key=lambda x: -x.get("significant_tornado_parameter", 0)):
        name = s.get("station_name", s["station_id"])[:16]
        lines.append(
            f"{name:16s} | {s['sbcape_jkg']:>7.0f} | {s['mucape_jkg']:>7.0f} | "
            f"{s['srh_0_3km_m2s2']:>7.0f} | {s['significant_tornado_parameter']:>6.2f} | "
            f"{s['lcl_height_agl_m']:>5.0f} | {s['bulk_shear_0_6km_kts']:>5.1f} | "
            f"{s['sfc_temp_c']:>5.1f} | {s['sfc_dewpoint_c']:>5.1f}"
        )
    return "\n".join(lines)


if __name__ == "__main__":
    import sys
    dt = None
    if len(sys.argv) > 1:
        dt = datetime.fromisoformat(sys.argv[1]).replace(tzinfo=timezone.utc)
    data = fetch_all_soundings(dt)
    print(format_table(data))
