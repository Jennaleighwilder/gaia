"""
GAIA Upper Air Ingest Client

Phase 5 stops here:
- verified radiosonde pulls via Siphon/Wyoming
- computes severe-weather parameters with MetPy
- best-effort legacy RAP/RUC model sounding hook

The legacy NOAA RUC endpoint appears to be unstable/deprecated as of
2026-03-21, so model sounding requests fail gracefully and report the
underlying fetch error instead of crashing the ingest path.
"""

from __future__ import annotations

import json
import math
import ssl
import sys
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from io import StringIO
from pathlib import Path

import pandas as pd
from siphon.simplewebservice.wyoming import WyomingUpperAir

import metpy.calc as mpcalc
from metpy.units import units

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from runtime.bus import init_bus, publish_simple

REAL_SOUNDING_STATIONS = ["RNK", "BNA", "GSO"]
MODEL_SOUNDING_STATIONS = ["KTRI", "KTYS", "KGKT"]
LEGACY_RUC_BASES = [
    "https://rucsoundings.noaa.gov/get_raobs.cgi",
    "http://rucsoundings.noaa.gov/get_raobs.cgi",
]
REQUEST_HEADERS = {
    "User-Agent": "(GAIA Weather Engine, theforgottencode780@gmail.com)",
}


def _month_name(dt: datetime) -> str:
    return dt.strftime("%b")


def _safe_float(value) -> float | None:
    if value is None:
        return None
    try:
        if hasattr(value, "magnitude"):
            value = value.magnitude
        return float(value)
    except Exception:
        return None


def _quantity_or_none(value, unit=None) -> float | None:
    try:
        if value is None:
            return None
        if hasattr(value, "magnitude") and unit is not None:
            value = value.to(unit)
        if hasattr(value, "magnitude"):
            value = value.magnitude
        if isinstance(value, (list, tuple)) and not value:
            return None
        if hasattr(value, "ndim") and getattr(value, "ndim", 0) > 0:
            if len(value) == 0:
                return None
            value = value[0]
            if hasattr(value, "magnitude") and unit is not None:
                value = value.to(unit)
            if hasattr(value, "magnitude"):
                value = value.magnitude
        numeric = float(value)
        if math.isnan(numeric) or math.isinf(numeric):
            return None
        return numeric
    except Exception:
        return None


def _drop_missing_profile_rows(df: pd.DataFrame) -> pd.DataFrame:
    required = ["pressure", "height", "temperature", "dewpoint", "u_wind", "v_wind"]
    keep = [column for column in required if column in df.columns]
    cleaned = df.dropna(subset=keep).copy()
    if "pressure" in cleaned.columns:
        cleaned = cleaned.drop_duplicates(subset=["pressure"], keep="first")
        cleaned = cleaned.sort_values("pressure", ascending=False)
    return cleaned.reset_index(drop=True)


def _interpolate_height_for_pressure(pressures_hpa, heights_m, target_hpa: float) -> float | None:
    if target_hpa is None:
        return None
    try:
        p = list(pressures_hpa)
        z = list(heights_m)
        if len(p) < 2 or len(z) < 2:
            return None
        ordered = sorted(zip(p, z), key=lambda item: item[0])
        p_sorted = [item[0] for item in ordered]
        z_sorted = [item[1] for item in ordered]
        if target_hpa < p_sorted[0] or target_hpa > p_sorted[-1]:
            return None
        return float(pd.Series(z_sorted).interpolate().iloc[0] if False else __import__("numpy").interp(target_hpa, p_sorted, z_sorted))
    except Exception:
        return None


def _interpolate_temp_at_height(heights_agl_m, temperatures_c, target_height_m: float) -> float | None:
    try:
        ordered = sorted(zip(heights_agl_m, temperatures_c), key=lambda item: item[0])
        h_sorted = [item[0] for item in ordered]
        t_sorted = [item[1] for item in ordered]
        if len(h_sorted) < 2 or target_height_m < h_sorted[0] or target_height_m > h_sorted[-1]:
            return None
        return float(__import__("numpy").interp(target_height_m, h_sorted, t_sorted))
    except Exception:
        return None


def _lapse_rate_c_per_km(temp_lower_c: float | None, temp_upper_c: float | None, depth_m: float | None) -> float | None:
    if temp_lower_c is None or temp_upper_c is None or depth_m in (None, 0):
        return None
    return (temp_lower_c - temp_upper_c) / (depth_m / 1000.0)


def _freezing_level_agl_m(heights_agl_m, temperatures_c) -> float | None:
    if len(heights_agl_m) < 2:
        return None
    for idx in range(1, len(heights_agl_m)):
        t0 = temperatures_c[idx - 1]
        t1 = temperatures_c[idx]
        if t0 is None or t1 is None:
            continue
        if (t0 >= 0 >= t1) or (t0 <= 0 <= t1):
            h0 = heights_agl_m[idx - 1]
            h1 = heights_agl_m[idx]
            if t0 == t1:
                return float(h0)
            fraction = (0.0 - t0) / (t1 - t0)
            return float(h0 + fraction * (h1 - h0))
    return None


def _inversion_stats(heights_agl_m, temperatures_c) -> tuple[bool, float]:
    strongest = 0.0
    for idx in range(1, len(heights_agl_m)):
        h0 = heights_agl_m[idx - 1]
        h1 = heights_agl_m[idx]
        t0 = temperatures_c[idx - 1]
        t1 = temperatures_c[idx]
        if None in (h0, h1, t0, t1):
            continue
        if h1 <= h0:
            continue
        delta_t = t1 - t0
        if delta_t > strongest and h0 <= 3000.0:
            strongest = delta_t
    return strongest > 0.0, round(strongest, 3)


class UpperAirClient:
    def __init__(self):
        self.real_stations = list(REAL_SOUNDING_STATIONS)
        self.model_stations = list(MODEL_SOUNDING_STATIONS)

    def _candidate_synoptic_times(self, reference_time: datetime | None = None, count: int = 6) -> list[datetime]:
        ref = (reference_time or datetime.now(timezone.utc)).astimezone(timezone.utc)
        ref = ref.replace(minute=0, second=0, microsecond=0)
        latest_cycle_hour = 12 if ref.hour >= 12 else 0
        current_cycle = ref.replace(hour=latest_cycle_hour)
        times = []
        for idx in range(count):
            times.append(current_cycle - timedelta(hours=12 * idx))
        return times

    def _request_real_sounding(self, sounding_time: datetime, station: str) -> pd.DataFrame:
        df = WyomingUpperAir.request_data(sounding_time, station)
        return _drop_missing_profile_rows(df)

    def _legacy_ruc_urls(self, station: str, valid_time: datetime) -> list[str]:
        year = valid_time.year
        month = _month_name(valid_time)
        day = valid_time.day
        hour = valid_time.hour
        query = (
            f"data_source=Op40&latest=latest&start_year={year}&start_month_name={month}"
            f"&start_mday={day}&start_hour={hour}&n_hrs=1.0&fcst_len=shortest"
            f"&airport={station}&text=Ascii%20text%20(GSD%20format)"
        )
        return [f"{base}?{query}" for base in LEGACY_RUC_BASES]

    def _request_model_text(self, station: str, valid_time: datetime) -> str:
        errors = []
        context = ssl._create_unverified_context()
        for url in self._legacy_ruc_urls(station, valid_time):
            req = urllib.request.Request(url, headers=REQUEST_HEADERS)
            try:
                with urllib.request.urlopen(req, timeout=8, context=context) as resp:
                    return resp.read().decode("utf-8", errors="replace")
            except Exception as exc:
                errors.append(f"{url} -> {type(exc).__name__}: {exc}")
        raise RuntimeError("; ".join(errors) or "legacy RUC fetch failed")

    def _parse_legacy_ruc_text(self, raw_text: str) -> pd.DataFrame:
        rows = []
        for line in raw_text.splitlines():
            parts = line.strip().split()
            if len(parts) < 6:
                continue
            numbers = []
            for token in parts:
                try:
                    numbers.append(float(token))
                except ValueError:
                    continue
            if len(numbers) < 6:
                continue
            pressure = numbers[0]
            height = numbers[1]
            temp_c = numbers[2]
            dewpoint_c = numbers[3]
            wind_dir = numbers[4]
            wind_speed_kts = numbers[5]
            if not (50.0 <= pressure <= 1100.0 and -120.0 <= temp_c <= 60.0):
                continue
            rows.append(
                {
                    "pressure": pressure,
                    "height": height,
                    "temperature": temp_c,
                    "dewpoint": dewpoint_c,
                    "direction": wind_dir,
                    "speed": wind_speed_kts,
                }
            )
        if not rows:
            raise ValueError("could not parse any profile rows from legacy RAP sounding text")

        df = pd.DataFrame(rows)
        radians = df["direction"].astype(float).apply(math.radians)
        speed = df["speed"].astype(float)
        df["u_wind"] = -speed * radians.apply(math.sin)
        df["v_wind"] = -speed * radians.apply(math.cos)
        return _drop_missing_profile_rows(df)

    def compute_severe_parameters(self, sounding_df: pd.DataFrame) -> dict:
        profile = _drop_missing_profile_rows(sounding_df)
        if profile.empty:
            raise ValueError("sounding profile is empty after dropping missing rows")

        pressure = profile["pressure"].to_numpy() * units.hectopascal
        temperature = profile["temperature"].to_numpy() * units.degC
        dewpoint = profile["dewpoint"].to_numpy() * units.degC
        u_wind = profile["u_wind"].to_numpy() * units.knot
        v_wind = profile["v_wind"].to_numpy() * units.knot
        height = profile["height"].to_numpy() * units.meter

        surface_height = _quantity_or_none(height[0], units.meter) or 0.0
        heights_msl = [_quantity_or_none(value, units.meter) for value in height]
        heights_agl = [(value - surface_height) if value is not None else None for value in heights_msl]
        pressures_hpa = [_quantity_or_none(value, units.hectopascal) for value in pressure]
        temperatures_c = [_quantity_or_none(value, units.degC) for value in temperature]

        sbcape, sbcin = mpcalc.surface_based_cape_cin(pressure, temperature, dewpoint)
        mlcape, mlcin = mpcalc.mixed_layer_cape_cin(pressure, temperature, dewpoint)
        mucape, mucin = mpcalc.most_unstable_cape_cin(pressure, temperature, dewpoint)

        lcl_pressure, _lcl_temp = mpcalc.lcl(pressure[0], temperature[0], dewpoint[0])
        lfc_pressure, _lfc_temp = mpcalc.lfc(pressure, temperature, dewpoint)
        el_pressure, _el_temp = mpcalc.el(pressure, temperature, dewpoint)

        shear_0_1 = mpcalc.wind_speed(
            *mpcalc.bulk_shear(pressure, u_wind, v_wind, height=height, depth=1000 * units.meter)
        ).to(units.knot)
        shear_0_3 = mpcalc.wind_speed(
            *mpcalc.bulk_shear(pressure, u_wind, v_wind, height=height, depth=3000 * units.meter)
        ).to(units.knot)
        shear_0_6 = mpcalc.wind_speed(
            *mpcalc.bulk_shear(pressure, u_wind, v_wind, height=height, depth=6000 * units.meter)
        ).to(units.knot)

        srh_0_1_pos, srh_0_1_neg, srh_0_1_total = mpcalc.storm_relative_helicity(
            height, u_wind, v_wind, depth=1000 * units.meter
        )
        srh_0_3_pos, srh_0_3_neg, srh_0_3_total = mpcalc.storm_relative_helicity(
            height, u_wind, v_wind, depth=3000 * units.meter
        )

        lcl_height_agl = None
        lfc_height_agl = None
        el_height_agl = None
        if _quantity_or_none(lcl_pressure, units.hectopascal) is not None:
            lcl_msl = _interpolate_height_for_pressure(
                pressures_hpa, heights_msl, _quantity_or_none(lcl_pressure, units.hectopascal)
            )
            if lcl_msl is not None:
                lcl_height_agl = lcl_msl - surface_height
        if _quantity_or_none(lfc_pressure, units.hectopascal) is not None:
            lfc_msl = _interpolate_height_for_pressure(
                pressures_hpa, heights_msl, _quantity_or_none(lfc_pressure, units.hectopascal)
            )
            if lfc_msl is not None:
                lfc_height_agl = lfc_msl - surface_height
        if _quantity_or_none(el_pressure, units.hectopascal) is not None:
            el_msl = _interpolate_height_for_pressure(
                pressures_hpa, heights_msl, _quantity_or_none(el_pressure, units.hectopascal)
            )
            if el_msl is not None:
                el_height_agl = el_msl - surface_height

        t700 = _interpolate_temp_at_height(
            [_interpolate_height_for_pressure(pressures_hpa, heights_agl, p) for p in pressures_hpa],
            temperatures_c,
            _interpolate_height_for_pressure(pressures_hpa, heights_agl, 700.0) or 0.0,
        )
        t500 = _interpolate_temp_at_height(
            [_interpolate_height_for_pressure(pressures_hpa, heights_agl, p) for p in pressures_hpa],
            temperatures_c,
            _interpolate_height_for_pressure(pressures_hpa, heights_agl, 500.0) or 0.0,
        )
        z700_agl = _interpolate_height_for_pressure(pressures_hpa, heights_agl, 700.0)
        z500_agl = _interpolate_height_for_pressure(pressures_hpa, heights_agl, 500.0)
        t_sfc = temperatures_c[0] if temperatures_c else None
        t_3km = _interpolate_temp_at_height([h for h in heights_agl if h is not None], [t for t in temperatures_c if t is not None], 3000.0)
        lr_700_500 = _lapse_rate_c_per_km(t700, t500, (z500_agl - z700_agl) if None not in (z700_agl, z500_agl) else None)
        lr_sfc_3km = _lapse_rate_c_per_km(t_sfc, t_3km, 3000.0)

        pwat = mpcalc.precipitable_water(pressure, dewpoint)
        freezing_level = _freezing_level_agl_m([h for h in heights_agl if h is not None], [t for t in temperatures_c if t is not None])
        inversion_present, inversion_strength = _inversion_stats(
            [h for h in heights_agl if h is not None],
            [t for t in temperatures_c if t is not None],
        )

        effective_shear = _quantity_or_none(shear_0_6, units.knot)
        effective_srh = _quantity_or_none(srh_0_3_total, units("meter^2 / second^2"))
        stp = None
        scp = None
        if (
            _quantity_or_none(sbcape, units("joule / kilogram")) is not None
            and lcl_height_agl is not None
            and _quantity_or_none(srh_0_1_total, units("meter^2 / second^2")) is not None
            and effective_shear is not None
        ):
            try:
                stp = _quantity_or_none(
                    mpcalc.significant_tornado(
                        sbcape,
                        lcl_height_agl * units.meter,
                        srh_0_1_total,
                        shear_0_6,
                    )
                )
            except Exception:
                stp = None
        if (
            _quantity_or_none(mucape, units("joule / kilogram")) is not None
            and effective_srh is not None
            and effective_shear is not None
        ):
            try:
                scp = _quantity_or_none(
                    mpcalc.supercell_composite(
                        mucape,
                        srh_0_3_total,
                        shear_0_6,
                    )
                )
            except Exception:
                scp = None

        ehi_0_1km = None
        cape_val = _quantity_or_none(sbcape, units("joule / kilogram"))
        srh01_val = _quantity_or_none(srh_0_1_total, units("meter^2 / second^2"))
        if cape_val is not None and srh01_val is not None:
            ehi_0_1km = (cape_val * srh01_val) / 160000.0

        return {
            "sbcape_jkg": round(_quantity_or_none(sbcape, units("joule / kilogram")) or 0.0, 3),
            "mlcape_jkg": round(_quantity_or_none(mlcape, units("joule / kilogram")) or 0.0, 3),
            "mucape_jkg": round(_quantity_or_none(mucape, units("joule / kilogram")) or 0.0, 3),
            "sbcin_jkg": round(_quantity_or_none(sbcin, units("joule / kilogram")) or 0.0, 3),
            "mlcin_jkg": round(_quantity_or_none(mlcin, units("joule / kilogram")) or 0.0, 3),
            "bulk_shear_0_1km_kts": round(_quantity_or_none(shear_0_1, units.knot) or 0.0, 3),
            "bulk_shear_0_3km_kts": round(_quantity_or_none(shear_0_3, units.knot) or 0.0, 3),
            "bulk_shear_0_6km_kts": round(_quantity_or_none(shear_0_6, units.knot) or 0.0, 3),
            "effective_bulk_shear_kts": round(effective_shear or 0.0, 3),
            "srh_0_1km_m2s2": round(srh01_val or 0.0, 3),
            "srh_0_3km_m2s2": round(_quantity_or_none(srh_0_3_total, units("meter^2 / second^2")) or 0.0, 3),
            "effective_srh_m2s2": round(effective_srh or 0.0, 3),
            "significant_tornado_parameter": round(stp or 0.0, 4),
            "supercell_composite": round(scp or 0.0, 4),
            "energy_helicity_index_0_1km": round(ehi_0_1km or 0.0, 4),
            "lcl_height_agl_m": round(lcl_height_agl or 0.0, 3),
            "lfc_height_agl_m": round(lfc_height_agl or 0.0, 3),
            "el_height_agl_m": round(el_height_agl or 0.0, 3),
            "freezing_level_m": round(freezing_level or 0.0, 3),
            "precipitable_water_mm": round(_quantity_or_none(pwat, units.millimeter) or 0.0, 3),
            "precipitable_water_in": round(_quantity_or_none(pwat, units.inch) or 0.0, 3),
            "mid_level_lapse_rate_700_500": round(lr_700_500 or 0.0, 3),
            "low_level_lapse_rate_sfc_3km": round(lr_sfc_3km or 0.0, 3),
            "inversion_present": inversion_present,
            "inversion_strength_c": inversion_strength,
            "cap_strength_cin": round(abs(_quantity_or_none(sbcin, units("joule / kilogram")) or 0.0), 3),
            "profile_row_count": int(len(profile)),
        }

    def _publish_upper_air_event(self, source: str, payload: dict) -> None:
        init_bus()
        publish_simple(
            source=source,
            event_type="upper_air_observation",
            payload=payload,
            context={"station": payload.get("station"), "source": source},
            metrics={"instability": payload.get("parameters", {}).get("sbcape_jkg", 0.0)},
        )

    def get_real_sounding(self, station: str, sounding_time: datetime, publish: bool = False) -> dict:
        profile = self._request_real_sounding(sounding_time, station)
        parameters = self.compute_severe_parameters(profile)
        result = {
            "source": "wyoming_radiosonde",
            "station": station,
            "valid_time_utc": sounding_time.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
            "parameters": parameters,
            "profile_preview": profile.head(5).to_dict(orient="records"),
        }
        if publish:
            self._publish_upper_air_event("upper_air_client", result)
        return result

    def get_latest_real_sounding(self, publish: bool = True) -> dict:
        last_error = None
        for sounding_time in self._candidate_synoptic_times():
            for station in self.real_stations:
                try:
                    return self.get_real_sounding(station, sounding_time, publish=publish)
                except Exception as exc:
                    last_error = f"{station} {sounding_time.isoformat()} -> {type(exc).__name__}: {exc}"
        raise RuntimeError(last_error or "no radiosonde sounding available")

    def get_latest_model_sounding(self, station: str = "KTRI", publish: bool = False) -> dict:
        now = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
        try:
            raw_text = self._request_model_text(station, now)
            profile = self._parse_legacy_ruc_text(raw_text)
            parameters = self.compute_severe_parameters(profile)
            result = {
                "source": "legacy_ruc_model",
                "station": station,
                "valid_time_utc": now.isoformat().replace("+00:00", "Z"),
                "parameters": parameters,
                "profile_preview": profile.head(5).to_dict(orient="records"),
            }
            if publish:
                self._publish_upper_air_event("upper_air_client", result)
            return result
        except Exception as exc:
            return {
                "source": "legacy_ruc_model",
                "station": station,
                "valid_time_utc": now.isoformat().replace("+00:00", "Z"),
                "error": f"{type(exc).__name__}: {exc}",
            }


if __name__ == "__main__":
    client = UpperAirClient()
    print("GAIA Upper Air Client — live verification")
    print()
    real = client.get_latest_real_sounding(publish=False)
    print("Real sounding:")
    print(json.dumps(real, indent=2))
    print()
    model = client.get_latest_model_sounding("KTRI", publish=False)
    print("Model sounding:")
    print(json.dumps(model, indent=2))
