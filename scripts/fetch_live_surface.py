#!/usr/bin/env python3
"""
Fetch latest surface (METAR-style) observations for all GAIA NOAA stations.

Uses api.weather.gov via runtime.ingest.noaa_client — same STATIONS as the
governor ingest and dashboard surface panel.

Output: runs/live_surface.json (dashboard consumption). Default: full JSON on stdout.
With ``--cron``, prints a one-line summary only (for scheduled runs / log files).
"""

from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from runtime.ingest.noaa_client import STATIONS, get_latest_observation, normalize_observation


def _fmt_num(v: float | None, digits: int = 2) -> str:
    if v is None:
        return "N/A"
    return f"{float(v):.{digits}f}"


def _row_for_station(station_id: str) -> dict | None:
    raw = get_latest_observation(station_id)
    if not raw:
        return None
    o = normalize_observation(raw)
    ts = o.get("timestamp") or ""
    time_str = ""
    if isinstance(ts, str) and ts:
        try:
            t = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            time_str = t.strftime("%Y-%m-%d %H:%M")
        except ValueError:
            time_str = ts[:16].replace("T", " ")
    precip_mm = o.get("precipitation_1h_mm")
    if precip_mm is not None:
        precip_in = float(precip_mm) * 0.0393701
        precip_s = f"{precip_in:.2f}"
    else:
        precip_s = "0.00"
    desc = (o.get("text_description") or "").strip() or "N/A"
    sky = desc.split(",")[0].strip()[:40]
    wind = o.get("wind_speed_mph")
    wind_mph = round(float(wind), 1) if wind is not None else 0.0
    return {
        "station": station_id,
        "time": time_str or "N/A",
        "temp_f": _fmt_num(o.get("temperature_f")),
        "dewpoint_f": _fmt_num(o.get("dewpoint_f")),
        "pressure_mb": _fmt_num(o.get("pressure_mb"), 2),
        "wind_mph": wind_mph,
        "visibility_mi": _fmt_num(o.get("visibility_mi")),
        "precip_1h": precip_s,
        "sky": sky,
        "metar": desc,
    }


def main() -> int:
    cron_mode = "--cron" in sys.argv
    now = datetime.now(timezone.utc)
    stations_out: list[dict] = []
    errors: list[str] = []

    for station_id in STATIONS:
        try:
            row = _row_for_station(station_id)
            if row:
                stations_out.append(row)
            else:
                errors.append(f"{station_id}: no observation")
        except Exception as e:
            errors.append(f"{station_id}: {e}")
        time.sleep(float(os.environ.get("GAIA_SURFACE_STATION_DELAY_SEC", "1.25")))

    payload = {
        "timestamp": now.isoformat(),
        "stations": stations_out,
        "errors": errors,
        "station_count": len(stations_out),
    }

    out_path = ROOT / "runs" / "live_surface.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    if cron_mode:
        ids = ",".join(s["station"] for s in stations_out)
        print(
            f"[GAIA SURFACE] ts={payload['timestamp']} station_count={len(stations_out)} "
            f"errors={len(errors)} stations={ids}",
            flush=True,
        )
    else:
        print(json.dumps(payload, indent=2))
        print(
            f"\nCached to: runs/live_surface.json ({len(stations_out)} stations)",
            file=sys.stderr,
        )
    return 0 if stations_out else 1


if __name__ == "__main__":
    sys.exit(main())
