"""
USGS real-time streamflow data for East TN.
Source: https://waterservices.usgs.gov/nwis/iv/
Updates every 15 minutes.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional
from urllib.request import Request, urlopen

# East TN USGS stream gauge IDs (curated for flash-flood relevance)
# French Broad, Pigeon, Holston, Clinch drainages
EAST_TN_GAUGE_IDS = [
    "03470500",  # French Broad R nr Knoxville (Knox)
    "03470210",  # French Broad R nr Kodak (Sevier)
    "03469000",  # French Broad R below Douglas Dam (Sevier)
    "03465500",  # Little Pigeon R at Sevierville (Sevier)
    "03461500",  # Pigeon R at Newport (Cocke)
    "03461000",  # Pigeon R at Hartford (Cocke)
    "03477000",  # South Fork Holston R at Bluff City (Sullivan)
    "03481500",  # Watauga R (Carter)
    "03527500",  # Clinch R at Clinton (Anderson)
]


def fetch_realtime(sites: list[str] | None = None, timeout: int = 20) -> dict:
    """
    Fetch latest instantaneous values for East TN gauges.
    Returns: { site_no: { "gage_height_ft": float, "discharge_cfs": float, "flood_stage_ft": float|null } }
    """
    import os

    if os.environ.get("GAIA_OFFLINE") == "1":
        return {}

    sites = sites or EAST_TN_GAUGE_IDS
    site_list = ",".join(sites[:20])  # API limit
    url = (
        "https://waterservices.usgs.gov/nwis/iv/"
        f"?format=json&sites={site_list}&parameterCd=00065,00060"
    )
    out = {}
    try:
        req = Request(url, headers={"User-Agent": "GAIA-Hydrological/1.0", "Accept": "application/json"})
        with urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read())
    except Exception:
        return out

    series = data.get("value", {}).get("timeSeries", [])
    for ts in series:
        site = ts.get("sourceInfo", {})
        site_no = (site.get("siteCode", [{}]) or [{}])[0].get("value")
        if not site_no:
            continue
        name = site.get("siteName", "")

        # Parse variable
        var = ts.get("variable", {})
        param = (var.get("variableCode", [{}]) or [{}])[0].get("value", "")
        # 00065 = gage height (ft), 00060 = discharge (cfs)

        values = ts.get("values", [{}])
        vals = (values or [{}])[0].get("value", [])
        if not vals:
            continue
        latest = vals[-1]
        v = float(latest.get("value", 0))

        out.setdefault(site_no, {"name": name, "gage_height_ft": None, "discharge_cfs": None})
        if "00065" in str(param):
            out[site_no]["gage_height_ft"] = round(v, 2)
        elif "00060" in str(param):
            out[site_no]["discharge_cfs"] = round(v, 0)

    return out


def load_flood_stages() -> dict[str, float]:
    """
    Flood stage (ft) by gauge. Populated from USGS station metadata or fixture.
    """
    path = Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "usgs_flood_stages.json"
    if path.exists():
        try:
            return json.loads(path.read_text())
        except Exception:
            pass
    # Defaults from USGS (common values for these rivers)
    return {
        "03470500": 22.0,  # French Broad Knoxville
        "03470210": 20.0,
        "03469000": 18.0,
        "03465500": 12.0,  # Little Pigeon Sevierville
        "03461500": 14.0,
        "03461000": 10.0,
        "03477000": 26.0,  # S Fork Holston Bluff City
        "03481500": 11.0,
        "03527500": 18.0,
    }
