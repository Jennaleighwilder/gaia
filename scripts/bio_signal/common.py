#!/usr/bin/env python3
from __future__ import annotations

import json
import math
import re
import shutil
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import boto3
import numpy as np
from botocore import UNSIGNED
from botocore.client import Config

try:
    import pyart
except ImportError:  # pragma: no cover
    pyart = None


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DATA_DIR = ROOT / "data" / "bio_signal"
DATA_DIR.mkdir(parents=True, exist_ok=True)
RUNS_DIR = ROOT / "runs"
RUNS_DIR.mkdir(parents=True, exist_ok=True)
LOCAL_NEXRAD_DIR = ROOT / "tests" / "fixtures" / "nexrad_quadstate"
MORNING_SCAN_DIR = DATA_DIR / "nexrad_kpah_morning"
MORNING_SCAN_DIR.mkdir(parents=True, exist_ok=True)

KPAH_LAT = 37.068
KPAH_LON = -88.772
UNIDATA_BUCKET = "unidata-nexrad-level2"
USER_AGENT = "GAIA-Research/1.0 (theforgottencode780@gmail.com)"


def load_json(path: Path) -> dict:
    with path.open() as f:
        return json.load(f)


def save_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as f:
        json.dump(payload, f, indent=2)


def fetch_json(url: str) -> dict:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())


def sunrise_utc(date: datetime, lat: float = KPAH_LAT, lon: float = KPAH_LON) -> float:
    """Approximate sunrise UTC decimal hours for KPAH."""
    doy = date.timetuple().tm_yday
    decl = math.radians(23.45 * math.sin(math.radians(360.0 / 365.0 * (doy - 81))))
    lat_r = math.radians(lat)
    cos_ha = max(-1.0, min(1.0, -math.tan(lat_r) * math.tan(decl)))
    hour_angle = math.degrees(math.acos(cos_ha))
    sunrise_lst = 12.0 - hour_angle / 15.0
    utc_offset = 5 if 3 <= date.month <= 11 else 6
    return (sunrise_lst + utc_offset) % 24.0


def parse_scan_datetime(name: str) -> datetime | None:
    match = re.search(r"KPAH(\d{8})_(\d{6})", name)
    if not match:
        return None
    return datetime.strptime("".join(match.groups()), "%Y%m%d%H%M%S").replace(tzinfo=timezone.utc)


def scan_decimal_hour(scan_time: datetime) -> float:
    return scan_time.hour + scan_time.minute / 60.0 + scan_time.second / 3600.0


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
    for name in names:
        if name in radar.fields:
            return radar.fields[name]["data"]
    return None


def anonymous_s3_client():
    return boto3.client("s3", config=Config(signature_version=UNSIGNED), region_name="us-east-1")


def list_unidata_keys(prefix: str) -> list[str]:
    s3 = anonymous_s3_client()
    paginator = s3.get_paginator("list_objects_v2")
    keys: list[str] = []
    for page in paginator.paginate(Bucket=UNIDATA_BUCKET, Prefix=prefix):
        keys.extend(
            obj["Key"]
            for obj in page.get("Contents", [])
            if not obj["Key"].endswith("_MDM")
        )
    return keys


def select_morning_keys(date_str: str, keys: list[str], hours_window: float = 2.0, max_scans: int = 14) -> list[str]:
    date = datetime.strptime(date_str, "%Y-%m-%d")
    sunrise = sunrise_utc(date)
    ranked: list[tuple[float, datetime, str]] = []
    for key in keys:
        scan_time = parse_scan_datetime(Path(key).name)
        if scan_time is None:
            continue
        delta = abs(scan_decimal_hour(scan_time) - sunrise)
        if delta <= hours_window:
            ranked.append((delta, scan_time, key))
    ranked.sort(key=lambda item: (item[0], item[1]))
    return [item[2] for item in ranked[:max_scans]]


def download_unidata_keys(keys: list[str], target_dir: Path = MORNING_SCAN_DIR) -> list[Path]:
    s3 = anonymous_s3_client()
    target_dir.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    for key in keys:
        out_path = target_dir / Path(key).name
        if not out_path.exists():
            s3.download_file(UNIDATA_BUCKET, key, str(out_path))
        paths.append(out_path)
    return paths


def local_scans_for_date(date_str: str) -> list[Path]:
    return sorted(LOCAL_NEXRAD_DIR.glob(f"KPAH{date_str.replace('-', '')}_*_V06*"))


def filter_morning_paths(paths: list[Path], date_str: str, hours_window: float = 2.0) -> list[Path]:
    date = datetime.strptime(date_str, "%Y-%m-%d")
    sunrise = sunrise_utc(date)
    keep: list[tuple[float, datetime, Path]] = []
    for path in paths:
        scan_time = parse_scan_datetime(path.name)
        if scan_time is None:
            continue
        delta = abs(scan_decimal_hour(scan_time) - sunrise)
        if delta <= hours_window:
            keep.append((delta, scan_time, path))
    keep.sort(key=lambda item: (item[0], item[1]))
    return [item[2] for item in keep]


def ensure_morning_scans(date_str: str) -> list[Path]:
    local_paths = filter_morning_paths(local_scans_for_date(date_str), date_str)
    if local_paths:
        return local_paths

    cached = filter_morning_paths(sorted(MORNING_SCAN_DIR.glob(f"KPAH{date_str.replace('-', '')}_*_V06*")), date_str)
    if cached:
        return cached

    prefix = f"{date_str[:4]}/{date_str[5:7]}/{date_str[8:10]}/KPAH/"
    keys = list_unidata_keys(prefix)
    morning_keys = select_morning_keys(date_str, keys)
    return filter_morning_paths(download_unidata_keys(morning_keys), date_str)


def analyze_dualpol_scan(path: Path, kind: str) -> dict | None:
    if pyart is None:  # pragma: no cover
        raise SystemExit("Requires Py-ART in GAIA .venv: pip install arm-pyart")

    radar = pyart.io.read_nexrad_archive(str(path), delay_field_loading=True)
    try:
        scan_time = _scan_time_utc(radar)
        refl = _field(radar, ["reflectivity"])
        cc = _field(radar, ["cross_correlation_ratio", "rhohv"])
        zdr = _field(radar, ["differential_reflectivity", "zdr"])
        vel = _field(radar, ["velocity"])
        if refl is None or cc is None or zdr is None:
            return None

        refl_arr = np.ma.filled(refl, np.nan)
        cc_arr = np.ma.filled(cc, np.nan)
        zdr_arr = np.ma.filled(zdr, np.nan)
        vel_arr = np.ma.filled(vel, np.nan) if vel is not None else np.full_like(refl_arr, np.nan)
        ranges_km = np.asarray(radar.range["data"], dtype=float) / 1000.0
        range_mask = (ranges_km >= 5.0) & (ranges_km <= 80.0)
        height = radar.gate_altitude["data"]

        valid = (
            np.isfinite(refl_arr)
            & np.isfinite(cc_arr)
            & np.isfinite(zdr_arr)
            & np.broadcast_to(range_mask, refl_arr.shape)
        )

        if kind == "bird":
            low_alt = height < 3000.0
            background = valid & low_alt & (refl_arr > 5.0) & (refl_arr < 25.0)
            mask = (
                background
                & (cc_arr >= 0.60)
                & (cc_arr <= 0.92)
                & (zdr_arr >= 0.5)
                & (zdr_arr <= 4.5)
                & (~np.isfinite(vel_arr) | (np.abs(vel_arr) <= 20.0))
            )
        elif kind == "insect":
            layer = (height >= 500.0) & (height <= 2500.0)
            background = valid & layer & (refl_arr >= 0.0) & (refl_arr <= 20.0)
            mask = (
                background
                & (cc_arr >= 0.70)
                & (cc_arr <= 0.98)
                & (zdr_arr >= 0.0)
                & (zdr_arr <= 1.6)
                & (~np.isfinite(vel_arr) | (np.abs(vel_arr) <= 25.0))
            )
        else:  # pragma: no cover
            raise ValueError(f"Unknown analysis kind: {kind}")

        feature_gates = int(np.sum(mask))
        background_gates = int(np.sum(background))
        fraction = float(feature_gates / max(background_gates, 1))
        return {
            "file": path.name,
            "scan_time": scan_time.isoformat(),
            "feature_gates": feature_gates,
            "background_gates": background_gates,
            "fraction": round(fraction, 4),
        }
    finally:
        del radar
