"""
Channel context — computes ASOS-derived and external channels for each observation.

Channels:
- overnight_cooling_rate: °F/hr temp drop sunset→sunrise (thermal)
- t_td_convergence_rate: °F/hr that T and Td are approaching (moisture)
- daytime_heating_rate: °F/hr temp rise after sunrise (instability)
- gps_pw_mm / precipitable_water_in: total column moisture (moisture)
- surface_ozone_ppb: tropopause fold indicator (environmental)
- thunder_count_nearby: multi-station thunder proxy (harmonic)

New borderline-severe discriminators:
- pressure_acceleration: second derivative of pressure (hPa/hr²)
- t_td_crossover_velocity: rate of T-Td spread change (°F/hr)
- wind_dir_variance: std of wind direction over last 3 obs (degrees)
- pressure_temperature_divergence_index: |dT|/(|dP|+0.1) over 2hr
- vis_collapse_rate: visibility drop per hour (miles/hr)
- sky_cover_trend: numeric change in sky cover over 2 obs (CLR=0..OVC=4)
- gust_factor_trend: change in gust/sustained ratio over 2 hrs
- cross_station_gradient: max pressure diff between stations (hPa)
"""

from __future__ import annotations

import math
from datetime import datetime, timezone, timedelta
from typing import Optional

try:
    from astral import LocationInfo
    from astral.sun import sun
    HAS_ASTRAL = True
except ImportError:
    HAS_ASTRAL = False

# East Tennessee centroid
EAST_TN_LAT = 35.96
EAST_TN_LON = -83.99


def _parse_ts(ts: str) -> datetime:
    return datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone(timezone.utc)


def _sun_times(date_str: str) -> tuple[Optional[datetime], Optional[datetime]]:
    """Return (sunset_prev_evening_utc, sunrise_utc) for date in East TN. Overnight = sunset prior day to sunrise this day."""
    try:
        dt = datetime.strptime(str(date_str)[:10], "%Y-%m-%d")
    except ValueError:
        return None, None
    if not HAS_ASTRAL:
        # Fallback: overnight = 23:30 UTC prior day to 10:30 UTC this day
        sunset = (dt - timedelta(days=1)).replace(hour=23, minute=30, second=0, tzinfo=timezone.utc)
        sunrise = dt.replace(hour=10, minute=30, second=0, tzinfo=timezone.utc)
        return sunset, sunrise
    try:
        loc = LocationInfo("East TN", "US", "America/New_York", EAST_TN_LAT, EAST_TN_LON)
        s_prev = sun(loc.observer, date=dt - timedelta(days=1))
        s_today = sun(loc.observer, date=dt)
        sunset = s_prev["sunset"].astimezone(timezone.utc)
        sunrise = s_today["sunrise"].astimezone(timezone.utc)
        return sunset, sunrise
    except (ValueError, KeyError):
        return None, None


def overnight_cooling_rate_fph(observations: list[dict], current_obs: dict) -> Optional[float]:
    """
    °F per hour of temperature drop between sunset and sunrise.
    Rapid cooling = clear sky = dry upper air. Slow cooling = clouds = moisture trapped.
    """
    if len(observations) < 2:
        return None
    date_str = current_obs.get("timestamp", "")[:10]
    sunset, sunrise = _sun_times(date_str)
    if sunset is None or sunrise is None:
        return None
    temps = []
    for o in observations:
        ts = _parse_ts(o.get("timestamp", ""))
        t = o.get("temperature_f")
        if t is not None and sunset <= ts <= sunrise:
            temps.append((ts, t))
    if len(temps) < 2:
        return None
    temps.sort(key=lambda x: x[0])
    t0, temp0 = temps[0]
    t1, temp1 = temps[-1]
    hours = (t1 - t0).total_seconds() / 3600.0
    if hours <= 0:
        return None
    drop = temp0 - temp1  # positive if cooling
    return round(drop / hours, 2)


def t_td_convergence_rate_per_hr(observations: list[dict], current_obs: dict) -> Optional[float]:
    """
    Rate (°F/hr) at which T-Td (dewpoint depression) is decreasing.
    Negative = T and Td converging = approaching saturation.
    """
    if len(observations) < 2:
        return None
    idx = next((i for i, o in enumerate(observations) if o.get("timestamp") == current_obs.get("timestamp")), -1)
    if idx < 1:
        return None
    curr = observations[idx]
    prev = observations[idx - 1]
    t_curr = curr.get("temperature_f")
    td_curr = curr.get("dewpoint_f")
    t_prev = prev.get("temperature_f")
    td_prev = prev.get("dewpoint_f")
    if None in (t_curr, td_curr, t_prev, td_prev):
        return None
    dep_curr = t_curr - td_curr
    dep_prev = t_prev - td_prev
    try:
        ts_curr = _parse_ts(curr["timestamp"])
        ts_prev = _parse_ts(prev["timestamp"])
    except (KeyError, ValueError):
        return None
    hours = (ts_curr - ts_prev).total_seconds() / 3600.0
    if hours <= 0:
        return None
    delta = dep_curr - dep_prev  # negative = converging
    return round(-delta / hours, 2)  # positive = convergence rate


def daytime_heating_rate_fph(observations: list[dict], current_obs: dict) -> Optional[float]:
    """
    °F per hour of temperature rise after sunrise.
    Fast heating = strong surface forcing = cap break timing.
    """
    if len(observations) < 2:
        return None
    date_str = current_obs.get("timestamp", "")[:10]
    _, sunrise = _sun_times(date_str)
    if sunrise is None:
        return None
    temps = []
    for o in observations:
        ts = _parse_ts(o.get("timestamp", ""))
        t = o.get("temperature_f")
        if t is not None and ts >= sunrise:
            temps.append((ts, t))
    if len(temps) < 2:
        return None
    temps.sort(key=lambda x: x[0])
    t0, temp0 = temps[0]
    t1, temp1 = temps[-1]
    hours = (t1 - t0).total_seconds() / 3600.0
    if hours <= 0:
        return None
    rise = temp1 - temp0
    return round(rise / hours, 2)


def thunder_count_nearby(observations: list[dict], current_obs: dict, hours: int = 3) -> int:
    """
    Count of obs with thunder (TS in METAR) in the last N hours.
    Multi-station proxy: each station's TS counts.
    """
    try:
        current_ts = _parse_ts(current_obs.get("timestamp", ""))
    except (KeyError, ValueError):
        return 0
    cutoff = current_ts - timedelta(hours=hours)
    count = 0
    for o in observations:
        try:
            ts = _parse_ts(o.get("timestamp", ""))
        except (KeyError, ValueError):
            continue
        if ts < cutoff or ts > current_ts:
            continue
        metar = (o.get("metar") or "").upper()
        if " TS" in f" {metar} " or metar.startswith("TS"):
            count += 1
    return count


# Sky condition to numeric (CLR=0, FEW=1, SCT=2, BKN=3, OVC=4)
SKY_COVER_MAP = {"CLR": 0, "SKC": 0, "FEW": 1, "SCT": 2, "BKN": 3, "OVC": 4}


def _sky_numeric(sky: str | None) -> float:
    if not sky:
        return 0.0
    return float(SKY_COVER_MAP.get((sky or "").upper().strip(), 0))


def pressure_trend_hpa_hr(observations: list[dict], current_obs: dict) -> Optional[float]:
    """Pressure change rate in hPa per hour. First derivative."""
    if len(observations) < 2:
        return None
    idx = next((i for i, o in enumerate(observations) if o.get("timestamp") == current_obs.get("timestamp")), -1)
    if idx < 1:
        return None
    curr = observations[idx]
    prev = observations[idx - 1]
    p_curr = curr.get("pressure_mb")
    p_prev = prev.get("pressure_mb")
    if p_curr is None or p_prev is None:
        return None
    try:
        ts_curr = _parse_ts(curr["timestamp"])
        ts_prev = _parse_ts(prev["timestamp"])
    except (KeyError, ValueError):
        return None
    hours = (ts_curr - ts_prev).total_seconds() / 3600.0
    if hours <= 0:
        return None
    # Negative = pressure dropping
    return round((p_curr - p_prev) / hours, 4)


def pressure_acceleration(observations: list[dict], current_obs: dict) -> Optional[float]:
    """
    Second derivative of pressure: how fast the pressure DROP is accelerating.
    p_accel = (p_trend_now - p_trend_1hr_ago) / 1.0
    A storm going -0.1 to -0.3 to -0.8 hPa/hr is accelerating.
    """
    if len(observations) < 3:
        return None
    idx = next((i for i, o in enumerate(observations) if o.get("timestamp") == current_obs.get("timestamp")), -1)
    if idx < 2:
        return None
    curr = observations[idx]
    prev_1hr = observations[idx - 1]
    prev_2hr = observations[idx - 2]
    p_curr = curr.get("pressure_mb")
    p_prev1 = prev_1hr.get("pressure_mb")
    p_prev2 = prev_2hr.get("pressure_mb")
    if None in (p_curr, p_prev1, p_prev2):
        return None
    try:
        ts_curr = _parse_ts(curr["timestamp"])
        ts_prev1 = _parse_ts(prev_1hr["timestamp"])
        ts_prev2 = _parse_ts(prev_2hr["timestamp"])
    except (KeyError, ValueError):
        return None
    h1 = (ts_curr - ts_prev1).total_seconds() / 3600.0
    h2 = (ts_prev1 - ts_prev2).total_seconds() / 3600.0
    if h1 <= 0 or h2 <= 0:
        return None
    trend_now = (p_curr - p_prev1) / h1
    trend_1hr_ago = (p_prev1 - p_prev2) / h2
    accel = (trend_now - trend_1hr_ago) / 1.0
    return round(accel, 4)


def t_td_crossover_velocity(observations: list[dict], current_obs: dict) -> Optional[float]:
    """
    Rate of change of T-Td spread in °F per hour.
    A spread collapsing 15F→8F in 2hr moves faster than 15F→11F.
    """
    if len(observations) < 2:
        return None
    idx = next((i for i, o in enumerate(observations) if o.get("timestamp") == current_obs.get("timestamp")), -1)
    if idx < 1:
        return None
    curr, prev = observations[idx], observations[idx - 1]
    t_curr = curr.get("temperature_f")
    td_curr = curr.get("dewpoint_f")
    t_prev = prev.get("temperature_f")
    td_prev = prev.get("dewpoint_f")
    if None in (t_curr, td_curr, t_prev, td_prev):
        return None
    spread_curr = t_curr - td_curr
    spread_prev = t_prev - td_prev
    try:
        ts_curr = _parse_ts(curr["timestamp"])
        ts_prev = _parse_ts(prev["timestamp"])
    except (KeyError, ValueError):
        return None
    hours = (ts_curr - ts_prev).total_seconds() / 3600.0
    if hours <= 0:
        return None
    return round((spread_curr - spread_prev) / hours, 4)


def wind_dir_variance(observations: list[dict], current_obs: dict) -> Optional[float]:
    """
    Std deviation of wind direction over last 3 observations.
    High variance (>45°) = storm approaching, erratic backing/veering.
    Low variance (<15°) = steady state, calm day.
    Uses circular statistics.
    """
    idx = next((i for i, o in enumerate(observations) if o.get("timestamp") == current_obs.get("timestamp")), -1)
    if idx < 0:
        return None
    recent = observations[max(0, idx - 2) : idx + 1]
    dirs = [o.get("wind_direction_deg") for o in recent if o.get("wind_direction_deg") is not None]
    if len(dirs) < 2:
        return None
    # Convert to unit vectors, compute resultant length R, then circular std
    rads = [math.radians(d) for d in dirs]
    cx = sum(math.cos(r) for r in rads) / len(rads)
    cy = sum(math.sin(r) for r in rads) / len(rads)
    R = math.sqrt(cx * cx + cy * cy)
    if R <= 0:
        return 90.0
    circ_var = 1 - R
    circ_std_rad = math.sqrt(-2 * math.log(R))
    circ_std_deg = math.degrees(circ_std_rad)
    return round(circ_std_deg, 2)


def pressure_temperature_divergence_index(observations: list[dict], current_obs: dict) -> Optional[float]:
    """
    PTI = |temp_change_2hr| / (|pressure_change_2hr| + 0.1)
    High PTI = strong frontal signal (temp dropping fast relative to pressure).
    """
    if len(observations) < 3:
        return None
    idx = next((i for i, o in enumerate(observations) if o.get("timestamp") == current_obs.get("timestamp")), -1)
    if idx < 2:
        return None
    curr = observations[idx]
    prev_2 = observations[idx - 2]
    t_curr = curr.get("temperature_f")
    t_prev = prev_2.get("temperature_f")
    p_curr = curr.get("pressure_mb")
    p_prev = prev_2.get("pressure_mb")
    if None in (t_curr, t_prev, p_curr, p_prev):
        return None
    dT = abs(t_curr - t_prev)
    dP = abs(p_curr - p_prev)
    pti = dT / (dP + 0.1)
    return round(pti, 4)


def vis_collapse_rate(observations: list[dict], current_obs: dict) -> Optional[float]:
    """
    Visibility drop per hour. (vis_1hr_ago - vis_now) / 1.0
    If vis dropped >3 miles in 1hr: strong storm signal.
    """
    if len(observations) < 2:
        return None
    idx = next((i for i, o in enumerate(observations) if o.get("timestamp") == current_obs.get("timestamp")), -1)
    if idx < 1:
        return None
    curr = observations[idx]
    prev = observations[idx - 1]
    vis_now = curr.get("visibility_mi")
    vis_prev = prev.get("visibility_mi")
    if vis_now is None or vis_prev is None:
        return None
    try:
        ts_curr = _parse_ts(curr["timestamp"])
        ts_prev = _parse_ts(prev["timestamp"])
    except (KeyError, ValueError):
        return None
    hours = (ts_curr - ts_prev).total_seconds() / 3600.0
    if hours <= 0:
        return None
    return round((float(vis_prev) - float(vis_now)) / hours, 2)


def sky_cover_trend(observations: list[dict], current_obs: dict) -> Optional[float]:
    """
    Numeric change in sky cover over last 2 observations.
    CLR=0, FEW=1, SCT=2, BKN=3, OVC=4.
    Rapid increase = convection building.
    """
    if len(observations) < 2:
        return None
    idx = next((i for i, o in enumerate(observations) if o.get("timestamp") == current_obs.get("timestamp")), -1)
    if idx < 1:
        return None
    curr = observations[idx]
    prev = observations[idx - 1]
    sky_curr = _sky_numeric(curr.get("sky_condition"))
    sky_prev = _sky_numeric(prev.get("sky_condition"))
    try:
        ts_curr = _parse_ts(curr["timestamp"])
        ts_prev = _parse_ts(prev["timestamp"])
    except (KeyError, ValueError):
        return None
    hours = (ts_curr - ts_prev).total_seconds() / 3600.0
    if hours <= 0:
        return None
    delta = sky_curr - sky_prev
    return round(delta / hours, 2)


def gust_factor_trend(observations: list[dict], current_obs: dict) -> Optional[float]:
    """
    Change in gust_factor (gust/sustained) over 2 hours.
    Rising gust factor = turbulence increasing = storm organizing.
    """
    if len(observations) < 3:
        return None
    idx = next((i for i, o in enumerate(observations) if o.get("timestamp") == current_obs.get("timestamp")), -1)
    if idx < 2:
        return None
    factors = []
    for o in observations[idx - 2 : idx + 1]:
        gust = o.get("wind_gust_mph")
        sust = o.get("wind_speed_mph") or 0
        if gust is not None and sust is not None and float(sust) > 0:
            factors.append(float(gust) / float(sust))
        elif gust is not None and sust is not None:
            factors.append(1.0)
    if len(factors) < 2:
        return None
    try:
        ts_curr = _parse_ts(observations[idx]["timestamp"])
        ts_prev = _parse_ts(observations[idx - 2]["timestamp"])
    except (KeyError, ValueError):
        return None
    hours = (ts_curr - ts_prev).total_seconds() / 3600.0
    if hours <= 0:
        return None
    trend = (factors[-1] - factors[0]) / hours
    return round(trend, 4)


def cross_station_gradient(station_observations_at_now: list[dict]) -> Optional[float]:
    """
    Max pressure difference between monitored stations at same timestamp.
    Large gradient (>3 hPa) = strong synoptic forcing.
    """
    if not station_observations_at_now or len(station_observations_at_now) < 2:
        return None
    pressures = [
        (o.get("station_id"), float(o.get("pressure_mb")))
        for o in station_observations_at_now
        if o.get("pressure_mb") is not None
    ]
    if len(pressures) < 2:
        return None
    max_diff = 0.0
    for i, (_, p1) in enumerate(pressures):
        for (_, p2) in pressures[i + 1 :]:
            max_diff = max(max_diff, abs(p1 - p2))
    return round(max_diff, 2)


def enrich_observation(
    obs: dict,
    observations: list[dict],
    date_str: str,
    station_id: str,
    gps_pw_fn=None,
    gps_pw_score_fn=None,
    ozone_fn=None,
    station_observations_at_now: list[dict] | None = None,
) -> dict:
    """
    Add channel context values to an observation dict.
    gps_pw_fn(date_str, station_id) -> precipitable_water_in or None (legacy)
    gps_pw_score_fn(date_str, station_id) -> gps_pw 0-1 score or None (fixture)
    ozone_fn(date_str, station_id) -> surface_ozone_ppb or None
    station_observations_at_now: optional list of current obs from all stations (for cross_station_gradient)
    """
    out = dict(obs)
    out["overnight_cooling_rate_fph"] = overnight_cooling_rate_fph(observations, obs)
    out["t_td_convergence_rate_per_hr"] = t_td_convergence_rate_per_hr(observations, obs)
    out["daytime_heating_rate_fph"] = daytime_heating_rate_fph(observations, obs)
    out["thunder_count_nearby"] = thunder_count_nearby(observations, obs)

    # Numeric pressure trend for siren (hPa/hr, negative = falling)
    ptr = pressure_trend_hpa_hr(observations, obs)
    if ptr is not None:
        out["pressure_trend_hpa_hr"] = ptr
    # New borderline-severe discriminator channels
    p_acc = pressure_acceleration(observations, obs)
    if p_acc is not None:
        out["pressure_acceleration"] = p_acc
    t_td_vel = t_td_crossover_velocity(observations, obs)
    if t_td_vel is not None:
        out["t_td_crossover_velocity"] = t_td_vel
    wdv = wind_dir_variance(observations, obs)
    if wdv is not None:
        out["wind_dir_variance"] = wdv
    pti = pressure_temperature_divergence_index(observations, obs)
    if pti is not None:
        out["pressure_temperature_divergence_index"] = pti
    vis_coll = vis_collapse_rate(observations, obs)
    if vis_coll is not None:
        out["vis_collapse_rate"] = vis_coll
    sky_tr = sky_cover_trend(observations, obs)
    if sky_tr is not None:
        out["sky_cover_trend"] = sky_tr
    gf_tr = gust_factor_trend(observations, obs)
    if gf_tr is not None:
        out["gust_factor_trend"] = gf_tr
    if station_observations_at_now:
        grad = cross_station_gradient(station_observations_at_now)
        if grad is not None:
            out["cross_station_gradient"] = grad

    if gps_pw_fn:
        pw = gps_pw_fn(date_str, station_id)
        if pw is not None:
            out["precipitable_water_in"] = pw
    if gps_pw_score_fn:
        score = gps_pw_score_fn(date_str, station_id)
        if score is not None:
            out["gps_pw"] = score
    if ozone_fn:
        oz = ozone_fn(date_str, station_id)
        if oz is not None:
            out["surface_ozone_ppb"] = oz
    return out
