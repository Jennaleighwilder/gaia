"""
GAIA Governor — atmospheric decision router.

Phase 2 wiring:
- fans observations to all scoring engines
- computes convergence and saddle state
- renders CLEAR / WATCH / WARNING / EMERGENCY
- logs decisions to the bus
- optionally asks MAAT to seal the prediction packet
"""

from __future__ import annotations

import hashlib
import logging
import json
import os
import time
from dataclasses import dataclass
from typing import Any, Dict, List

try:
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware
except ImportError:  # pragma: no cover
    FastAPI = None  # type: ignore
    CORSMiddleware = None  # type: ignore

from runtime.bus import init_bus, publish_simple, replay_with_seq
from runtime.engines.celestial_engine import CelestialEngine
from runtime.engines.hydrological_engine import HydrologicalEngine
from runtime.engines.harmonic_engine import HarmonicEngine
from runtime.engines.chimera_engine import ChimeraCoreEngine
from runtime.engines.composite_engine import CompositeEngine
from runtime.engines.common import parse_timestamp
from runtime.data.seasonal_context import get_seasonal_profile
from runtime.engines.correlation_score import engine_correlation
from runtime.engines.correlation_miner import CorrelationMiner
from runtime.engines.environmental_engine import EnvironmentalEngine
from runtime.engines.historical_engine import HistoricalEngine
from runtime.engines.infrastructure_engine import InfrastructureEngine
from runtime.engines.instability_engine import InstabilityEngine
from runtime.engines.moisture_engine import MoistureEngine
from runtime.engines.oscillation_engine import OscillationEngine
from runtime.engines.pressure_engine import PressureEngine
from runtime.engines.radar_engine import RadarEngine
from runtime.engines.regime_engine import RegimeEngine
from runtime.engines.lightning_engine import LightningEngine
from runtime.engines.terrain_engine import TerrainEngine
from runtime.engines.soil_engine import SoilEngine
from runtime.engines.goes_engine import GoesEngine
from runtime.engines.flash_flood_engine import FlashFloodEngine
from runtime.engines.wildfire_engine import WildfireEngine
from runtime.engines.hail_engine import HailEngine
from runtime.engines.saddle_engine import SaddleEngine
from runtime.engines.sensor_mesh_engine import SensorMeshEngine
from runtime.engines.shear_engine import ShearEngine
from runtime.engines.siren_engine import SirenEngine, gaia_obs_to_siren_obs
from runtime.engines.sirens import ALL_SIRENS
from runtime.engines.sirens.base_siren import BaseSiren
from runtime.engines.thermal_engine import ThermalEngine
from runtime.engines.uvrk_engine import UVRKAtmosphericEngine
from runtime.governor.autonomic_state import AutonomicLayer
from runtime.governor.duration_predictor import DurationPredictor
from runtime.governor.pid_controller import compute_pid_modifier, record_event as record_pid_event
from runtime.governor.threshold_adapter import get_current_thresholds, record_decision
from runtime.ingest.noaa_client import STATIONS
from runtime.data.tri_facilities import get_facilities_in_radius, has_class1_within_radius
from runtime.memory.event_memory import EventMemory

logger = logging.getLogger(__name__)

try:
    from runtime.services.maat_service import MaatService
except Exception:  # pragma: no cover
    MaatService = None  # type: ignore


GAIA_THRESHOLDS = {
    "watch_threshold": 0.6,
    "warning_convergence": 3,
    "warning_score": 0.6,
    "emergency_convergence": 5,
    "emergency_score": 0.8,
    "saddle_escalation": True,
    "saddle_promotion_min": 0.35,
    "siren_damper_threshold": 0.2,
}

CONTEXT_ONLY_ENGINES = {"oscillation", "environmental", "infrastructure", "celestial", "harmonic", "hydrological"}

ENGINE_ORDER = [
    "radar",
    "goes",
    "lightning",
    "terrain",
    "soil",
    "flash_flood",
    "wildfire",
    "hail",
    "pressure",
    "thermal",
    "moisture",
    "shear",
    "instability",
    "siren",
    "historical_analog",
    "composite",
    "uvrk",
    "regime",
    "saddle",
    "infrastructure",
    "environmental",
    "hydrological",
    "oscillation",
    "celestial",
    "harmonic",
    "sensor_mesh",
    "correlation_miner",
    "chimera",
]

ALARM_ENGINES = [
    "radar",
    "pressure",
    "thermal",
    "moisture",
    "shear",
    "instability",
    "historical_analog",
    "composite",
    "uvrk",
    "regime",
]

class _StubApp:
    def add_middleware(self, *args, **kwargs):
        return None

    def on_event(self, *args, **kwargs):
        def decorator(fn):
            return fn
        return decorator

    def get(self, *args, **kwargs):
        def decorator(fn):
            return fn
        return decorator

    def post(self, *args, **kwargs):
        def decorator(fn):
            return fn
        return decorator


app = FastAPI(title="GAIA Governor", version="0.2.0") if FastAPI is not None else _StubApp()
if FastAPI is not None and CORSMiddleware is not None:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

START_TS = time.time()
AUTONOMIC = AutonomicLayer()
RADAR_ENGINE = RadarEngine()
GOES_ENGINE = GoesEngine()
LIGHTNING_ENGINE = LightningEngine()
TERRAIN_ENGINE = TerrainEngine()
SOIL_ENGINE = SoilEngine()
FLASH_FLOOD_ENGINE = FlashFloodEngine()
WILDFIRE_ENGINE = WildfireEngine()
HAIL_ENGINE = HailEngine()
PRESSURE_ENGINE = PressureEngine()
THERMAL_ENGINE = ThermalEngine()
MOISTURE_ENGINE = MoistureEngine()
SHEAR_ENGINE = ShearEngine()
INSTABILITY_ENGINE = InstabilityEngine()
SIREN_ENGINE = SirenEngine(config={"sound_baseline_speed": 350.0})
SADDLE_ENGINE = SaddleEngine()
HISTORICAL_ENGINE = HistoricalEngine()
COMPOSITE_ENGINE = CompositeEngine()
UVRK_ENGINE = UVRKAtmosphericEngine()
REGIME_ENGINES: Dict[str, RegimeEngine] = {}
INFRASTRUCTURE_ENGINE = InfrastructureEngine()
ENVIRONMENTAL_ENGINE = EnvironmentalEngine()
HYDROLOGICAL_ENGINE = HydrologicalEngine()
OSCILLATION_ENGINE = OscillationEngine()
CELESTIAL_ENGINE = CelestialEngine()
HARMONIC_ENGINE = HarmonicEngine()
SENSOR_MESH_ENGINE = SensorMeshEngine(STATIONS)
CORRELATION_MINER = CorrelationMiner()
CHIMERA_ENGINE = ChimeraCoreEngine(output_dir=os.path.expanduser("~/gaia/runtime/state"), quiet=True)
MAAT_ENGINE = None if os.environ.get("GAIA_DISABLE_EVIDENCE") else (MaatService() if MaatService is not None else None)
EVENT_MEMORY = EventMemory(os.path.expanduser("~/gaia/data/memory/event_memory.jsonl"))
REGION_DAY_SUMMARIES: Dict[str, Dict[str, dict]] = {}
DURATION_PREDICTOR = DurationPredictor()

LAST_STATUS: Dict[str, Any] = {
    "decision": "CLEAR",
    "convergence_count": 0,
    "engine_scores": {name: None for name in ENGINE_ORDER},
}


@dataclass
class SimpleEvent:
    event_id: str
    event_type: str
    payload: dict
    context: dict
    metrics: dict


def _blank_engine_scores() -> Dict[str, Any]:
    return {name: None for name in ENGINE_ORDER}


def reset_runtime_state() -> None:
    global AUTONOMIC
    global PRESSURE_ENGINE
    global THERMAL_ENGINE
    global MOISTURE_ENGINE
    global SHEAR_ENGINE
    global INSTABILITY_ENGINE
    global SIREN_ENGINE
    global SADDLE_ENGINE
    global HISTORICAL_ENGINE
    global COMPOSITE_ENGINE
    global UVRK_ENGINE
    global REGIME_ENGINES
    global INFRASTRUCTURE_ENGINE
    global ENVIRONMENTAL_ENGINE
    global HYDROLOGICAL_ENGINE
    global OSCILLATION_ENGINE
    global CELESTIAL_ENGINE
    global HARMONIC_ENGINE
    global SENSOR_MESH_ENGINE
    global CORRELATION_MINER
    global CHIMERA_ENGINE
    global MAAT_ENGINE
    global EVENT_MEMORY
    global REGION_DAY_SUMMARIES

    AUTONOMIC = AutonomicLayer()
    PRESSURE_ENGINE = PressureEngine()
    THERMAL_ENGINE = ThermalEngine()
    MOISTURE_ENGINE = MoistureEngine()
    SHEAR_ENGINE = ShearEngine()
    INSTABILITY_ENGINE = InstabilityEngine()
    SIREN_ENGINE = SirenEngine(config={"sound_baseline_speed": 350.0})
    SADDLE_ENGINE = SaddleEngine()
    HISTORICAL_ENGINE = HistoricalEngine()
    COMPOSITE_ENGINE = CompositeEngine()
    UVRK_ENGINE = UVRKAtmosphericEngine()
    REGIME_ENGINES = {}
    INFRASTRUCTURE_ENGINE = InfrastructureEngine()
    ENVIRONMENTAL_ENGINE = EnvironmentalEngine()
    HYDROLOGICAL_ENGINE = HydrologicalEngine()
    OSCILLATION_ENGINE = OscillationEngine()
    CELESTIAL_ENGINE = CelestialEngine()
    HARMONIC_ENGINE = HarmonicEngine()
    SENSOR_MESH_ENGINE = SensorMeshEngine(STATIONS)
    CORRELATION_MINER = CorrelationMiner()
    CHIMERA_ENGINE = ChimeraCoreEngine(output_dir=os.path.expanduser("~/gaia/runtime/state"), quiet=True)
    MAAT_ENGINE = None if os.environ.get("GAIA_DISABLE_EVIDENCE") else (MaatService() if MaatService is not None else None)
    EVENT_MEMORY = EventMemory(os.path.expanduser("~/gaia/data/memory/event_memory.jsonl"))
    REGION_DAY_SUMMARIES = {}
    for s in ALL_SIRENS:
        s.reset()
    LAST_STATUS.update(
        {
            "decision": "CLEAR",
            "convergence_count": 0,
            "engine_scores": {name: None for name in ENGINE_ORDER},
            "region": None,
            "timestamp": None,
        }
    )


def _canonical_hash(payload: dict) -> str:
    data = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(data.encode()).hexdigest()


def _promote(decision: str) -> str:
    order = ["CLEAR", "WATCH", "WARNING", "EMERGENCY"]
    idx = min(order.index(decision) + 1, len(order) - 1)
    return order[idx]


def _downgrade_one(decision: str) -> str:
    order = ["CLEAR", "WATCH", "WARNING", "EMERGENCY"]
    idx = max(order.index(decision) - 1, 0)
    return order[idx]


def _station_observations(region: str, timestamp: str, payload: dict) -> List[dict]:
    stations = payload.get("station_observations")
    if stations:
        return stations
    observations = payload.get("observations", {})
    return [{"station_id": "REGION", "region": region, "timestamp": timestamp, **observations}]


def _bus_event_history(limit: int = 250) -> list[dict]:
    total = max(0, limit)
    history = []
    for _seq, event in replay_with_seq(from_seq=max(0, init_bus() and 0), limit=total):
        history.append(
            {
                "event_type": event.event_type,
                "source": event.source,
                "decision": (event.payload or {}).get("decision"),
            }
        )
    return history[-limit:]


def _dominant_wind_direction(observations: List[dict]) -> float | None:
    values = [obs.get("wind_direction_deg") for obs in observations if obs.get("wind_direction_deg") is not None]
    if not values:
        return None
    radians = [__import__("math").radians(value) for value in values]
    sin_sum = sum(__import__("math").sin(value) for value in radians)
    cos_sum = sum(__import__("math").cos(value) for value in radians)
    if sin_sum == 0 and cos_sum == 0:
        return float(values[0])
    angle = __import__("math").degrees(__import__("math").atan2(sin_sum, cos_sum))
    return round((angle + 360.0) % 360.0, 2)


def _mean_observation(observations: List[dict], field: str) -> float | None:
    values = [obs.get(field) for obs in observations if obs.get(field) is not None]
    if not values:
        return None
    return round(sum(values) / len(values), 4)


def _update_regime_engine(region: str, timestamp: str, station_observations: List[dict], payload: dict) -> dict:
    day_key = timestamp[:10]
    REGION_DAY_SUMMARIES.setdefault(region, {})
    engine = REGIME_ENGINES.setdefault(region, RegimeEngine())

    for summary in payload.get("daily_summaries", []) or []:
        date_key = summary.get("date")
        if date_key:
            REGION_DAY_SUMMARIES[region][date_key] = summary

    REGION_DAY_SUMMARIES[region][day_key] = {
        "date": day_key,
        "mean_pressure": _mean_observation(station_observations, "pressure_mb"),
        "mean_temp": _mean_observation(station_observations, "temperature_f"),
        "dominant_wind_dir": _dominant_wind_direction(station_observations),
        "precip_total": round(sum((obs.get("precip_1h_in") or 0.0) for obs in station_observations), 4),
        "temp_range": payload.get("daily_temp_range")
        or (
            round(
                max(obs.get("temperature_f") for obs in station_observations if obs.get("temperature_f") is not None)
                - min(obs.get("temperature_f") for obs in station_observations if obs.get("temperature_f") is not None),
                4,
            )
            if len([obs for obs in station_observations if obs.get("temperature_f") is not None]) >= 2
            else None
        ),
    }
    engine.daily_summaries = [
        REGION_DAY_SUMMARIES[region][key]
        for key in sorted(REGION_DAY_SUMMARIES[region].keys())[-engine.max_days:]
    ]
    return engine.detect_transition()


def _score_observation_engines(region: str, timestamp: str, station_observations: List[dict], payload: dict) -> tuple[dict, dict]:
    scores = _blank_engine_scores()
    engine_details: dict[str, dict] = {}
    upper_air = payload.get("upper_air") or None

    for obs in station_observations:
        sid = obs.get("station_id", region)
        UVRK_ENGINE.ingest(obs)
        PRESSURE_ENGINE.ingest(
            sid,
            obs.get("timestamp", timestamp),
            pressure_mb=obs.get("pressure_mb"),
            visibility_mi=obs.get("visibility_mi"),
            wind_direction_deg=obs.get("wind_direction_deg"),
        )
        THERMAL_ENGINE.ingest(
            sid,
            obs.get("timestamp", timestamp),
            temperature_f=obs.get("temperature_f"),
            dewpoint_f=obs.get("dewpoint_f"),
            humidity_pct=obs.get("humidity_pct"),
        )
        MOISTURE_ENGINE.ingest(
            sid,
            obs.get("timestamp", timestamp),
            dewpoint_f=obs.get("dewpoint_f"),
            humidity_pct=obs.get("humidity_pct"),
        )
        SHEAR_ENGINE.ingest(
            sid,
            obs.get("timestamp", timestamp),
            wind_speed_mph=obs.get("wind_speed_mph"),
            wind_gust_mph=obs.get("wind_gust_mph"),
            wind_direction_deg=obs.get("wind_direction_deg"),
        )
        INSTABILITY_ENGINE.ingest(
            sid,
            obs.get("timestamp", timestamp),
            cape_jkg=obs.get("cape_jkg"),
            cin_jkg=obs.get("cin_jkg"),
            text_description=obs.get("text_description"),
        )
        HISTORICAL_ENGINE.ingest(sid, obs.get("timestamp", timestamp), pressure_mb=obs.get("pressure_mb"))
        INFRASTRUCTURE_ENGINE.ingest(
            sid,
            obs.get("timestamp", timestamp),
            temperature_f=obs.get("temperature_f"),
            dewpoint_f=obs.get("dewpoint_f"),
            pressure_mb=obs.get("pressure_mb"),
            wind_speed_mph=obs.get("wind_speed_mph"),
        )
        SENSOR_MESH_ENGINE.ingest(sid, obs.get("timestamp", timestamp))

    trigger_events = []
    pressure_results = []
    thermal_results = []
    moisture_results = []
    shear_results = []
    historical_results = []
    instability_results = []
    siren_results = []

    for obs in station_observations:
        sid = obs.get("station_id", region)
        network = [o for o in station_observations if o.get("station_id") != sid]
        pressure_result = PRESSURE_ENGINE.score(
            sid,
            obs.get("pressure_mb"),
            pressure_trend=obs.get("pressure_trend"),
            network_pressures=[o.get("pressure_mb") for o in network if o.get("pressure_mb") is not None],
            visibility_mi=obs.get("visibility_mi"),
            wind_direction_deg=obs.get("wind_direction_deg"),
        )
        pressure_results.append(pressure_result)
        if pressure_result["score"] >= GAIA_THRESHOLDS["watch_threshold"]:
            trigger_events.append("pressure_alert")

        thermal_results.append(
            THERMAL_ENGINE.score(
                sid,
                timestamp=obs.get("timestamp", timestamp),
                temperature_f=obs.get("temperature_f"),
                dewpoint_f=obs.get("dewpoint_f"),
                humidity_pct=obs.get("humidity_pct"),
                overnight_low_f=obs.get("overnight_low_f"),
                daily_high_f=obs.get("daily_high_f"),
                daily_low_f=obs.get("daily_low_f"),
                overnight_cooling_rate_fph=obs.get("overnight_cooling_rate_fph"),
                inversion_strength_f=obs.get("inversion_strength_f"),
                text_description=obs.get("text_description"),
                network_observations=network,
            )
        )
        moisture_results.append(
            MOISTURE_ENGINE.score(
                sid,
                dewpoint_f=obs.get("dewpoint_f"),
                humidity_pct=obs.get("humidity_pct"),
                precipitable_water_in=obs.get("precipitable_water_in"),
                t_td_convergence_rate_per_hr=obs.get("t_td_convergence_rate_per_hr"),
                prior_dewpoint_f=obs.get("prior_dewpoint_f"),
                wind_direction_deg=obs.get("wind_direction_deg"),
                network_observations=network,
            )
        )
        shear_result = SHEAR_ENGINE.score(
            sid,
            timestamp=obs.get("timestamp", timestamp),
            wind_speed_mph=obs.get("wind_speed_mph"),
            wind_gust_mph=obs.get("wind_gust_mph"),
            wind_direction_deg=obs.get("wind_direction_deg"),
            prior_wind_direction_deg=obs.get("prior_wind_direction_deg"),
            network_observations=network,
            upper_air=upper_air,
        )
        shear_results.append(shear_result)
        if shear_result["score"] >= GAIA_THRESHOLDS["watch_threshold"]:
            trigger_events.append("shear_alert")

        historical_results.append(
            HISTORICAL_ENGINE.score(
                sid,
                timestamp=obs.get("timestamp", timestamp),
                temperature_f=obs.get("temperature_f"),
                dewpoint_f=obs.get("dewpoint_f"),
                wind_direction_deg=obs.get("wind_direction_deg"),
                wind_speed_mph=obs.get("wind_speed_mph"),
                pressure_mb=obs.get("pressure_mb"),
                visibility_mi=obs.get("visibility_mi"),
                pressure_trend=obs.get("pressure_trend"),
            )
        )

        instability_results.append(
            INSTABILITY_ENGINE.score(
                sid,
                timestamp=obs.get("timestamp", timestamp),
                cape_jkg=obs.get("cape_jkg"),
                cin_jkg=obs.get("cin_jkg"),
                temperature_f=obs.get("temperature_f"),
                dewpoint_f=obs.get("dewpoint_f"),
                pressure_mb=obs.get("pressure_mb"),
                humidity_pct=obs.get("humidity_pct"),
                wind_direction_deg=obs.get("wind_direction_deg"),
                text_description=obs.get("text_description"),
                daytime_heating_rate_fph=obs.get("daytime_heating_rate_fph"),
                pressure_acceleration=obs.get("pressure_acceleration"),
                pressure_temperature_divergence_index=obs.get("pressure_temperature_divergence_index"),
                sky_cover_trend=obs.get("sky_cover_trend"),
                trigger_events=trigger_events,
                upper_air=upper_air,
            )
        )
        siren_obs = gaia_obs_to_siren_obs({**obs, "timestamp": obs.get("timestamp", timestamp)})
        siren_val = SIREN_ENGINE.score(siren_obs)
        siren_results.append(siren_val)

    try:
        radar_result = RADAR_ENGINE.score(region, payload=payload)
        scores["radar"] = round(float(radar_result.get("score", 0.0)), 4)
        engine_details["radar"] = radar_result
    except Exception as e:
        logger.debug("Radar engine failed: %s", e)
        scores["radar"] = 0.0
        engine_details["radar"] = {"score": 0.0, "tornado_indicated": False, "severe_indicated": False}
    obs0 = station_observations[0] if station_observations else {}
    tier1_payload = {
        **payload,
        "wind_direction_deg": obs0.get("wind_direction_deg"),
        "wind_speed_mph": obs0.get("wind_speed_mph") or (obs0.get("wind_speed_kt") and float(obs0.get("wind_speed_kt", 0)) * 1.15078),
    }
    for name, eng, key in [
        ("goes", GOES_ENGINE, "goes"),
        ("lightning", LIGHTNING_ENGINE, "lightning"),
        ("terrain", TERRAIN_ENGINE, "terrain"),
        ("soil", SOIL_ENGINE, "soil"),
    ]:
        try:
            p = tier1_payload if key in ("terrain", "soil") else payload
            res = eng.score(region, payload=p)
            scores[key] = round(float(res.get("score", 0.0)), 4) if res else 0.0
            engine_details[key] = res or {}
        except Exception as e:
            logger.debug("%s engine failed: %s", name, e)
            scores[key] = 0.0
            engine_details[key] = {}
    scores["pressure"] = round(max((r["score"] for r in pressure_results), default=0.0), 4)
    scores["thermal"] = round(max((r["score"] for r in thermal_results), default=0.0), 4)
    scores["moisture"] = round(max((r["score"] for r in moisture_results), default=0.0), 4)
    scores["shear"] = round(max((r["score"] for r in shear_results), default=0.0), 4)
    scores["instability"] = round(max((r["score"] for r in instability_results), default=0.0), 4)
    scores["siren"] = round(max((r if isinstance(r, (int, float)) else r.get("score", 0.0) for r in siren_results), default=0.0), 4)
    scores["historical_analog"] = round(max((r["score"] for r in historical_results), default=0.0), 4)
    if upper_air:
        composite_detail = COMPOSITE_ENGINE.score(upper_air)
        scores["composite"] = composite_detail["score"]
        engine_details["composite"] = composite_detail
    else:
        scores["composite"] = None
        engine_details["composite"] = {"engine": "composite", "score": None, "note": "abstain: no upper air"}
    uvrk_detail = UVRK_ENGINE.score()
    regime_detail = _update_regime_engine(region, timestamp, station_observations, payload)
    scores["uvrk"] = uvrk_detail["score"]
    scores["regime"] = regime_detail["score"]
    engine_details["uvrk"] = uvrk_detail
    engine_details["regime"] = regime_detail
    scores["infrastructure"] = INFRASTRUCTURE_ENGINE.score(
        observations=station_observations,
        current_time=timestamp,
        alerts_api_ok=payload.get("alerts_api_ok", True),
        expected_station_ids=payload.get("expected_station_ids"),
    )["score"]
    env_result = ENVIRONMENTAL_ENGINE.score(timestamp=timestamp, **payload.get("environmental_context", {}))
    scores["environmental"] = env_result["score"]
    engine_details["environmental"] = env_result
    hydro_result = HYDROLOGICAL_ENGINE.score()
    scores["hydrological"] = hydro_result["score"]
    engine_details["hydrological"] = hydro_result
    scores["oscillation"] = OSCILLATION_ENGINE.score(timestamp=timestamp)["score"]
    celestial_ctx = payload.get("celestial") or {}
    celestial_result = CELESTIAL_ENGINE.score(celestial_ctx if celestial_ctx else None)
    scores["celestial"] = celestial_result if isinstance(celestial_result, (int, float)) else celestial_result.get("score", 0.0)
    harmonic_obs = {}
    if station_observations:
        o = station_observations[0]
        harmonic_obs = {
            "thunder_count_nearby": o.get("thunder_count_nearby", 0),
            "celestial_score": scores.get("celestial"),
        }
    scores["harmonic"] = HARMONIC_ENGINE.score(harmonic_obs)
    # Flash flood engine: uses hydro, terrain, soil — call after those
    hydro_channels = engine_details.get("hydrological", {}).get("channels", {})
    stage_ratio = hydro_channels.get("stream_stage_vs_flood_ratio") or hydro_channels.get("stage_ratio") or 0
    soil_from_engine = engine_details.get("soil", {}).get("soil_moisture")
    soil_from_payload = payload.get("soil_moisture") or (payload.get("flash_flood_fixture") or {}).get("soil_moisture")
    goes_detail = engine_details.get("goes") or {}
    atmospheric_river = bool(goes_detail.get("atmospheric_river_detected", False))
    ff_payload = {
        **payload,
        "hydrological": {"stage_ratio": float(stage_ratio or 0)},
        "terrain": {
            "valley_flood_risk": float(
                payload.get("terrain", {}).get("valley_flood_risk")
                or engine_details.get("terrain", {}).get("valley_flood_risk", 0)
                or 0
            )
        },
        "soil_moisture": soil_from_engine if soil_from_engine is not None else soil_from_payload,
        "atmospheric_river_detected": atmospheric_river,
        "goes_tpw_mm": goes_detail.get("tpw_mm"),
    }
    try:
        ff_result = FLASH_FLOOD_ENGINE.score(region, payload=ff_payload)
        scores["flash_flood"] = ff_result.get("score", 0.0)
        engine_details["flash_flood"] = ff_result
    except Exception as e:
        logger.debug("Flash flood engine failed: %s", e)
        scores["flash_flood"] = 0.0
        engine_details["flash_flood"] = {"score": 0.0, "flash_flood_certain": False}
    try:
        wf_payload = {**payload, "wildfire_fixture": payload.get("wildfire_fixture") or {}}
        wf_result = WILDFIRE_ENGINE.score(region, payload=wf_payload)
        scores["wildfire"] = wf_result.get("score", 0.0)
        engine_details["wildfire"] = wf_result
    except Exception as e:
        logger.debug("Wildfire engine failed: %s", e)
        scores["wildfire"] = 0.0
        engine_details["wildfire"] = {"score": 0.0, "wildfire_certain": False}
    try:
        hail_result = HAIL_ENGINE.score(region, payload=payload, engine_scores=scores)
        scores["hail"] = hail_result.get("score", 0.0)
        engine_details["hail"] = hail_result
    except Exception as e:
        logger.debug("Hail engine failed: %s", e)
        scores["hail"] = 0.0
        engine_details["hail"] = {"score": 0.0, "hail_indicated": False, "hail_size_estimate": "none"}
    scores["sensor_mesh"] = SENSOR_MESH_ENGINE.score(
        observations=station_observations,
        current_time=timestamp,
        expected_station_ids=payload.get("expected_station_ids"),
    )["score"]
    scores["correlation_miner"] = None
    scores["chimera"] = None

    engine_details["pressure"] = max(pressure_results, key=lambda item: item["score"], default={})
    engine_details["thermal"] = max(thermal_results, key=lambda item: item["score"], default={})
    engine_details["moisture"] = max(moisture_results, key=lambda item: item["score"], default={})
    engine_details["shear"] = max(shear_results, key=lambda item: item["score"], default={})
    engine_details["instability"] = max(instability_results, key=lambda item: item["score"], default={})
    engine_details["siren"] = {"score": scores["siren"], "channels": getattr(SIREN_ENGINE, "channels", {})}
    engine_details["historical_analog"] = max(historical_results, key=lambda item: item["score"], default={})
    return scores, engine_details


def compute_decision_for_payload(payload: dict) -> dict:
    init_bus()
    region = payload.get("region", "unknown_region")
    timestamp = payload.get("timestamp") or time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    # Seasonal overlay — East TN has strong seasonal patterns
    try:
        month = int(timestamp[5:7]) if timestamp and len(timestamp) >= 7 else time.gmtime().tm_mon
    except (ValueError, TypeError):
        month = time.gmtime().tm_mon
    seasonal_profile = get_seasonal_profile(month, region)
    use_winter_engines = seasonal_profile.get("use_winter_engines_only", False)
    payload = {**payload, "seasonal_profile": seasonal_profile}
    station_observations = _station_observations(region, timestamp, payload)

    publish_simple(
        source="noaa_ingest",
        event_type="observation_received",
        payload={"region": region, "timestamp": timestamp, "station_count": len(station_observations)},
        context={"region": region},
        metrics={},
    )

    engine_scores, engine_details = _score_observation_engines(region, timestamp, station_observations, payload)
    score_snapshot = {
        "timestamp": timestamp,
        "region": region,
        **{
            k: (v or 0.0)
            for k, v in engine_scores.items()
            if k not in {"correlation_miner", "chimera", "siren"}
        },
    }
    SADDLE_ENGINE.ingest(region, timestamp, **{k: v for k, v in score_snapshot.items() if k != "timestamp"})
    saddle_result = SADDLE_ENGINE.score(region)
    engine_scores["saddle"] = saddle_result["score"]
    motion_correlation = engine_correlation(SADDLE_ENGINE.history.get(region, []), ALARM_ENGINES, window=4)

    instability_detail = engine_details.get("instability", {})
    if instability_detail.get("phase_transition"):
        publish_simple(
            source="instability_engine",
            event_type="phase_transition",
            payload=instability_detail["phase_transition"],
            context={"region": region},
            metrics={"instability": engine_scores["instability"] or 0.0},
        )

    real_scores = {name: score for name, score in engine_scores.items() if isinstance(score, (int, float))}
    decision_scores = {
        name: score for name, score in real_scores.items() if name not in CONTEXT_ONLY_ENGINES
    }
    max_score = max(decision_scores.values()) if decision_scores else 0.0
    oscillation_score = real_scores.get("oscillation", 0.0)
    warning_score = GAIA_THRESHOLDS["warning_score"]
    emergency_score = GAIA_THRESHOLDS["emergency_score"]
    # Tornado protection: radar or shear+saddle — don't let oscillation modulate thresholds
    radar_detail_early = engine_details.get("radar") or {}
    radar_tornado_early = radar_detail_early.get("tornado_indicated", False)
    shear_early = float(engine_scores.get("shear") or 0.0)
    saddle_early = float(engine_scores.get("saddle") or 0.0)
    tornado_protection = radar_tornado_early or (shear_early > 0.7 and saddle_early > 0.6)
    if not tornado_protection:
        if oscillation_score > 0.5:
            warning_score *= 0.95
            emergency_score *= 0.95
        elif oscillation_score < 0.2:
            warning_score *= 1.05
            emergency_score *= 1.05
    # Siren only votes in convergence when score > 0.3
    convergence_engines = [
        name for name, score in decision_scores.items()
        if score >= warning_score and (name != "siren" or score > 0.3)
    ]
    convergence_count = len(convergence_engines)
    thresholds = get_current_thresholds()
    pid_modifier = compute_pid_modifier(region)
    watch_threshold = max(
        0.2,
        min(0.95, GAIA_THRESHOLDS["watch_threshold"] * pid_modifier * (thresholds["review_threshold"] / 0.7)),
    )

    # SIRENS — independent watchers, each owns one element. Replace detection boost.
    obs_for_sirens = station_observations[0] if station_observations else {}
    siren_payload = {**payload, "station_observations": station_observations}
    siren_results: dict[str, Any] = {}
    for s in ALL_SIRENS:
        siren_results[s.name] = s.evaluate(obs_for_sirens, siren_payload, {})
    siren_results = BaseSiren.apply_corroboration(siren_results)
    screaming = [n for n, r in siren_results.items() if r.status == "SCREAMING"]
    alerting = [n for n, r in siren_results.items() if r.status == "ALERT"]
    silent = [n for n, r in siren_results.items() if r.status == "SILENT"]
    siren_summary = {
        "sirens_screaming": screaming,
        "sirens_alerting": alerting,
        "sirens_silent": silent,
    }
    # Siren-based detection: lower convergence when sirens agree
    detection_boost = (len(screaming) >= 1 and len(alerting) >= 1) or len(screaming) >= 2
    # ROTATION alerting on TW/hail/tornado/flash_flood = real convective signal, lower barrier
    event_type = payload.get("event_type") or ""
    rotation_boost = (
        "ROTATION" in alerting
        and event_type in ("thunderstorm_wind", "hail", "tornado", "flash_flood")
    )
    if rotation_boost:
        logger.info("Rotation boost: ROTATION siren alert, lowering convergence threshold to 2")
    effective_warning_convergence = 2 if (detection_boost or rotation_boost) else GAIA_THRESHOLDS["warning_convergence"]

    shear_score = float(engine_scores.get("shear") or 0.0)
    inst_score = float(engine_scores.get("instability") or 0.0)
    pressure_detail = engine_details.get("pressure") or {}
    pressure_drop = abs(float(pressure_detail.get("pressure_drop_rate_mbph") or 0))

    if convergence_count >= GAIA_THRESHOLDS["emergency_convergence"] and max_score >= emergency_score:
        decision = "EMERGENCY"
    elif convergence_count >= effective_warning_convergence and max_score >= warning_score:
        decision = "WARNING"
    elif any(score >= watch_threshold for score in decision_scores.values()):
        decision = "WATCH"
    else:
        decision = "CLEAR"

    decision_rank = {"CLEAR": 0, "WATCH": 1, "WARNING": 2, "EMERGENCY": 3}

    # Thunderstorm wind: weak events — shear>0.6 + instability>0.4 = 2 convergence enough
    if (
        shear_score > 0.6
        and inst_score > 0.4
        and convergence_count >= 2
        and max_score >= warning_score
        and decision in ("WATCH", "CLEAR")
    ):
        decision = "WARNING"
        logger.info("THUNDERSTORM_WIND: shear>0.6 inst>0.4 cc>=2 — min WARNING")

    # Thunderstorm wind: fast mover — pressure drop > 0.8 hPa/hr
    if (
        pressure_drop > 0.8
        and convergence_count >= 2
        and max_score >= warning_score
        and decision in ("WATCH", "CLEAR")
    ):
        decision = "WARNING"
        logger.info("THUNDERSTORM_WIND: fast mover pressure_drop=%.2f — min WARNING", pressure_drop)

    # FIX 2: Lower convergence for high shear (tornado signature)
    if shear_score > 0.8 and convergence_count >= 2 and max_score >= warning_score and decision in ("WATCH", "CLEAR"):
        decision = "WARNING"
    # Tornado protection: shear+saddle forces minimum WARNING (ENSO phase irrelevant)
    saddle_for_sig = float(engine_scores.get("saddle") or 0.0)
    if shear_score > 0.7 and saddle_for_sig > 0.6 and decision in ("WATCH", "CLEAR"):
        decision = "WARNING"
        logger.info("TORNADO_SIGNATURE: shear>0.7 saddle>0.6 — min WARNING (oscillation bypass)")

    if (
        engine_scores.get("saddle", 0.0) >= GAIA_THRESHOLDS["saddle_promotion_min"]
        and GAIA_THRESHOLDS["saddle_escalation"]
    ):
        decision = _promote(decision)

    # Siren escalation: 2 screaming = EMERGENCY, 1 screaming + 2 alerting = WARNING
    if len(screaming) >= 2 and decision_rank.get(decision, 0) < decision_rank["EMERGENCY"]:
        decision = "EMERGENCY"
        logger.info("SIREN_EMERGENCY: 2+ sirens screaming %s", screaming)
    elif len(screaming) >= 1 and len(alerting) >= 2 and decision_rank.get(decision, 0) < decision_rank["WARNING"]:
        decision = "WARNING"
        logger.info("SIREN_WARNING: 1 screaming + 2 alerting")
    elif (len(screaming) >= 1 or len(alerting) >= 2) and decision in ("CLEAR",):
        decision = "WATCH"
        logger.info("SIREN_WATCH: 1 screaming or 2 alerting")

    siren_score = float(engine_scores.get("siren") or 0.0)
    flash_collapse_override = False

    if siren_score >= 0.95:
        decision = "EMERGENCY"
        flash_collapse_override = True

    decision_before_veto = decision
    dd_value = None
    observation = station_observations[0] if station_observations else {}
    radar_detail = engine_details.get("radar") or {}
    radar_tornado = radar_detail.get("tornado_indicated", False)
    radar_severe = radar_detail.get("severe_indicated", False)
    if radar_tornado:
        decision = "EMERGENCY"
        logger.info("RADAR TORNADO SIGNATURE DETECTED — KMRX rotation couplet")
    elif radar_severe:
        if decision_rank.get(decision, 0) < decision_rank["WARNING"]:
            decision = "WARNING"
    # Tier 1 convergence: goes, radar, lightning, terrain, soil — nature agreeing
    tier1_scores = [
        float(engine_scores.get(k) or 0.0)
        for k in ("goes", "radar", "lightning", "terrain", "soil")
    ]
    tier1_agreement = sum(1 for s in tier1_scores if s > 0.6)
    tier1_agreement_met = tier1_agreement >= 3
    if tier1_agreement >= 4:
        decision = "EMERGENCY"
        logger.info("TIER 1 CONVERGENCE: 4+ nature engines > 0.6 — EMERGENCY")
    elif tier1_agreement >= 3 and decision_rank.get(decision, 0) < decision_rank["WARNING"]:
        decision = "WARNING"
        logger.info("TIER 1 CONVERGENCE: 3+ nature engines > 0.6 — min WARNING")
    if observation:
        temp_f = observation.get("temperature_f")
        dewpoint_f = observation.get("dewpoint_f")
        if temp_f is not None and dewpoint_f is not None:
            dd_value = temp_f - dewpoint_f

    # Winter event path: use thermal, pressure, temp — not convective engines
    event_type = payload.get("event_type") or ""
    if use_winter_engines and event_type in {"heavy_snow", "winter_storm"}:
        temp_f = (observation or {}).get("temperature_f")
        thermal_score = float(engine_scores.get("thermal") or 0.0)
        p_drop = float(pressure_detail.get("pressure_drop_rate_mbph") or 0)
        p_dropping = abs(p_drop) > 0.1  # meaningful pressure change
        if temp_f is not None and float(temp_f) < 36 and (thermal_score > 0.2 or p_dropping):
            if decision_rank.get(decision, 0) < decision_rank["WARNING"]:
                decision = "WARNING"
                logger.info("WINTER_EVENT: temp<36F + (thermal>0.2 or pressure dropping) — min WARNING")

    # Tornado shield: shear+saddle or tornado-event with strong analog/oscillation — never downgrade
    saddle_score = float(engine_scores.get("saddle") or 0.0)
    osc_score = float(engine_scores.get("oscillation") or 0.0)
    hist_score = float(engine_scores.get("historical_analog") or 0.0)
    tornado_signature = (
        (shear_score > 0.7 and saddle_score > 0.6)
        or (
            (payload.get("event_type") or "") == "tornado"
            and saddle_score >= 0.6
            and (osc_score >= 0.8 or hist_score >= 0.85)
        )
    )

    # === INSTABILITY QUALITY CHECK ===
    # If historical_analog is voting but instability is below 0.3,
    # the surface pattern matches a past storm but the atmosphere
    # lacks vertical energy. Downgrade one tier.
    # inst<0.3 cc>=2 threads needle: 2023-03-25 preserved (inst~0.3-0.4). 19/19 non-negotiable.
    # Skip for tornado signature (EF3 Blount 2011-03-24).
    inst_quality_applied = False
    inst_score = float(engine_scores.get("instability") or 0.0)
    hist_voted = "historical_analog" in convergence_engines
    if (
        not tornado_signature
        and hist_voted
        and inst_score < 0.3
        and convergence_count >= 2
        and decision in ("WARNING", "EMERGENCY")
    ):
        decision = _downgrade_one(decision)
        inst_quality_applied = True
        logger.info("Instability quality check: hist voted but inst=%.3f < 0.3 (cc=%d), downgrading", inst_score, convergence_count)

    # === SIREN CHORUS SCORER (West-OS design) ===
    # "One loud signal is noise. Three channels agreeing is evidence."
    # Don't fire on individual vetoes; watch multiple channels per dimension.
    # FIRE: >=3 channels hot on SAME dimension, OR >=2 dimensions each with >=2 channels hot
    # WATCH: any single dimension with >=2 channels hot
    # CLEAR: everything else
    # When FIRE and decision is WARNING/EMERGENCY → downgrade (chorus veto)
    moisture_channels = engine_details.get("moisture", {}).get("channels", {})
    thermal_channels = engine_details.get("thermal", {}).get("channels", {})
    instability_channels = engine_details.get("instability", {}).get("channels", {})
    environmental_channels = engine_details.get("environmental", {}).get("channels", {})

    # DIMENSION 1: COLUMN DRYNESS (gps_pw, overnight_cooling_rate, dewpoint_depression)
    column_dry_count = 0
    gps_pw_raw = moisture_channels.get("gps_pw")
    if gps_pw_raw is not None and float(gps_pw_raw) < 0.40:
        column_dry_count += 1  # Recalibrated for real PW (was 0.25 with rainfall proxy)
    overnight_cool = thermal_channels.get("overnight_cooling_rate")
    if overnight_cool is not None and float(overnight_cool) > 0.15:
        column_dry_count += 1
    if dd_value is not None and dd_value > 20:
        column_dry_count += 1

    # DIMENSION 2: ATMOSPHERIC STILLNESS (harmonic, t_td_convergence, wind)
    # wind_dir_variance REMOVED — inverted at scale (severe 34° > FA 29°); was backwards
    # if wind_dir_var_raw := observation.get("wind_dir_variance"):
    #     wind_dir_var = float(wind_dir_var_raw)
    #     if wind_dir_var > 40: stillness_count += 1
    #     if wind_dir_var < 20: stillness_count -= 1
    stillness_count = 0
    harmonic_score = float(engine_scores.get("harmonic") or 0.5)
    if harmonic_score < 0.05:
        stillness_count += 1
    t_td_conv = moisture_channels.get("t_td_convergence")
    if t_td_conv is not None and float(t_td_conv) < 0.10:
        stillness_count += 1
    # Siren silent >= 4 = quiet atmosphere, reinforces chorus veto
    if len(silent) >= 4:
        stillness_count += 1
    if observation:
        wind_mph = observation.get("wind_speed_mph")
        if wind_mph is None:
            kt = observation.get("wind_speed_kt")
            if kt is not None:
                try:
                    wind_mph = float(kt) * 1.15078
                except (TypeError, ValueError):
                    pass
        if wind_mph is not None:
            try:
                if float(wind_mph) < 3.0:
                    stillness_count += 1
            except (TypeError, ValueError):
                pass

    # DIMENSION 3: WEAK FORCING (daytime_heating_rate, instability, surface_ozone)
    # sky_cover_trend REMOVED — inverted at scale (FA 0.55 > severe 0.35); was backwards
    # if sky_tr := observation.get("sky_cover_trend"):
    #     if float(sky_tr) > 0.5: weak_forcing_count -= 1
    #     elif float(sky_tr) < 0.1: weak_forcing_count += 1
    # T-Td crossover velocity (0.77 sep at scale): KEEP — severe more negative, correct direction
    # pressure_acceleration (0.29 sep at scale): ADD — severe 0.40 > FA 0.11, correct direction
    weak_forcing_count = 0
    day_heat = instability_channels.get("daytime_heating_rate")
    if day_heat is not None and float(day_heat) < 0.10:
        weak_forcing_count += 1
    inst_score = float(engine_scores.get("instability") or 0.5)
    if inst_score < 0.35:
        weak_forcing_count += 1
    surface_ozone = environmental_channels.get("surface_ozone")
    if surface_ozone is not None and float(surface_ozone) < 0.15:
        weak_forcing_count += 1
    # Strong forcing modifiers (reduce weak_forcing)
    if observation:
        t_td_vel = observation.get("t_td_crossover_velocity")
        if t_td_vel is not None:
            v = float(t_td_vel)
            if v < -0.1:
                weak_forcing_count -= 1  # spread collapsing = moisture convergence = NOT quiet
            elif v > 0.1:
                weak_forcing_count += 1  # spread widening = quiet signal
        p_accel_raw = observation.get("pressure_acceleration")
        if p_accel_raw is not None:
            p_accel = float(p_accel_raw)
            if p_accel > 0.2:
                weak_forcing_count -= 1  # accelerating drop = forcing, NOT quiet
            elif p_accel < -0.1:
                weak_forcing_count += 1  # decelerating = settling, quiet signal
        if observation.get("vis_collapse_rate") is not None and float(observation.get("vis_collapse_rate", 0)) > 3:
            weak_forcing_count -= 1
        if observation.get("cross_station_gradient") is not None and float(observation.get("cross_station_gradient", 0)) > 3:
            weak_forcing_count -= 1
    weak_forcing_count = max(0, weak_forcing_count)

    dimensions_with_2plus = sum([
        column_dry_count >= 2,
        stillness_count >= 2,
        weak_forcing_count >= 2,
    ])
    max_single_dimension = max(column_dry_count, stillness_count, weak_forcing_count)

    # FIRE: max>=3 on one dimension OR 2+ dimensions each with 2+ channels (restored)
    siren_decision = "CLEAR"
    if max_single_dimension >= 3 or dimensions_with_2plus >= 2:
        siren_decision = "FIRE"
    elif dimensions_with_2plus >= 1:
        siren_decision = "WATCH"

    chorus_veto_applied = False
    # RADAR TORNADO: skip all chorus veto — NEXRAD rotation is definitive
    if radar_tornado:
        pass  # decision already EMERGENCY, no veto
    # FIX 1: Tornado shield — chorus cannot veto tornado signature (shear+saddle or tornado with strong analog)
    elif tornado_signature:
        if decision == "WATCH":
            decision = "WARNING"
        # Skip chorus veto entirely
    else:
        # FIRE: max>=3 on one dimension OR 2+ dimensions each with 2+ channels.
        # TRIPLE CHORUS: all 3 dimensions have 2+ channels (dims_with_2plus == 3) → double downgrade.
        # Wind guard: don't block veto when wind>=10 if column_dry_count>=2 (dry flow, not storm).
        # Don't veto winter events (heavy_snow, winter_storm).
        event_type = payload.get("event_type") or ""
        winter_event = event_type in {"heavy_snow", "winter_storm"}
        wind_mph_for_veto = None
        if observation:
            w = observation.get("wind_speed_mph")
            if w is None:
                kt = observation.get("wind_speed_kt")
                if kt is not None:
                    try:
                        wind_mph_for_veto = float(kt) * 1.15078
                    except (TypeError, ValueError):
                        pass
            else:
                try:
                    wind_mph_for_veto = float(w)
                except (TypeError, ValueError):
                    pass
        triple_chorus = dimensions_with_2plus == 3
        wind_high = wind_mph_for_veto is not None and wind_mph_for_veto >= 10.0
        wind_blocks = wind_high and not (triple_chorus and column_dry_count >= 3)
        fire_for_veto = (
            siren_decision == "FIRE"
            and not winter_event
            and not wind_blocks
        )
        if fire_for_veto and decision in ("WARNING", "EMERGENCY") and not radar_tornado and not radar_severe and not tier1_agreement_met:
            if triple_chorus:
                decision = "WATCH"
                chorus_veto_applied = True
                logger.info(
                    "Chorus veto (TRIPLE): dry=%d still=%d weak=%d -> WATCH",
                    column_dry_count, stillness_count, weak_forcing_count,
                )
            else:
                if decision == "EMERGENCY":
                    decision = "WARNING"
                elif decision == "WARNING":
                    decision = "WATCH"
                chorus_veto_applied = True
                logger.info(
                    "Chorus veto (FIRE): dry=%d still=%d weak=%d",
                    column_dry_count, stillness_count, weak_forcing_count,
                )

    # === SIREN GATE ===
    # No siren confirmation = surface engines firing on noise. Nature must agree.
    # Skip when use_winter_engines_only (winter storms use different physics).
    siren_gate_applied = False
    if not use_winter_engines and (
        len(screaming) == 0
        and len(alerting) == 0
        and decision in ("WARNING", "EMERGENCY")
        and not radar_tornado
    ):
        decision = "WATCH"
        siren_gate_applied = True
        logger.info("Siren gate: no siren confirmation, downgrading to WATCH")

    # TRI HAZMAT ELEVATION — query within 10 mi, elevate WARNING→EMERGENCY if Class 1 within 5 mi
    hazmat_elevated = False
    tri_facilities = []
    hazmat_score = 0.0
    if decision in ("WARNING", "EMERGENCY"):
        lat, lon = 35.81, -83.99  # East TN default
        for obs in station_observations:
            sid = obs.get("station_id")
            if sid and sid in STATIONS:
                lat = STATIONS[sid]["lat"]
                lon = STATIONS[sid]["lon"]
                break
        # Always list facilities within 10 miles in evidence packet
        facilities = get_facilities_in_radius(lat, lon, radius_miles=10)
        if facilities:
            tri_facilities = [{"name": f.get("name"), "distance_miles": f.get("distance_miles"), "has_class1": f.get("has_class1"), "county": f.get("county"), "top_chemicals_note": f.get("top_chemicals_note")} for f in facilities]
            # Distance-weighted score for display
            for f in facilities:
                dist = f.get("distance_miles", 10)
                hazmat_score += max(0, 1 - (dist / 10))
            hazmat_score = round(min(1.0, hazmat_score), 4)
            # Elevate WARNING→EMERGENCY if any facility with Class 1 (flammable, explosive, toxic gas) within 5 miles
            if has_class1_within_radius(lat, lon, radius_miles=5) and decision == "WARNING":
                decision = "EMERGENCY"
                hazmat_elevated = True
                class1_near = [f for f in facilities if f.get("has_class1") and f.get("distance_miles", 99) <= 5]
                logger.info(
                    "HAZMAT ELEVATION: Class 1 within 5 mi facilities=%d top=%s %.1f mi",
                    len(class1_near), class1_near[0].get("name", "?")[:30] if class1_near else "?",
                    class1_near[0].get("distance_miles", 0) if class1_near else 0,
                )

    AUTONOMIC.update(
        engine_weights={name: 1.0 for name, value in decision_scores.items() if value is not None},
        engine_variances={name: max(0.01, 1.0 - value) for name, value in decision_scores.items()},
        fallback_count=0,
        convergence_fired=convergence_count >= GAIA_THRESHOLDS["warning_convergence"],
        war_score=max_score,
        threat_score=max_score,
    )

    oscillation_bonus = real_scores.get("oscillation", 0.0) * 0.15
    environmental_score = real_scores.get("environmental", 0.0)
    infrastructure_score = real_scores.get("infrastructure", 0.0)
    consequence_multiplier = round(1.0 + (environmental_score * 0.5), 4) if environmental_score > 0.5 else 1.0
    vulnerability_flag = infrastructure_score > 0.3
    pressure_detail = engine_details.get("pressure", {})
    duration_class = DURATION_PREDICTOR.classify_duration(
        pressure_detail.get("pressure_drop_rate_mbph"),
        pressure_detail.get("max_drop_mb"),
        pressure_detail.get("drop_window_hours"),
    )
    duration_message = DURATION_PREDICTOR.format_warning(duration_class, "weather event")
    confidence = round(
        min(
            1.0,
            max_score
            + oscillation_bonus
            + (0.03 * convergence_count)
            + (0.1 if engine_scores.get("saddle", 0.0) > 0 else 0.0),
        ),
        4,
    )

    ff_detail = engine_details.get("flash_flood") or {}
    flash_flood_warning = bool(ff_detail.get("flash_flood_certain", False))
    if flash_flood_warning:
        logger.info("FLASH_FLOOD_WARNING — terrain-driven flood certain")
    wf_detail = engine_details.get("wildfire") or {}
    wildfire_warning = bool(wf_detail.get("wildfire_certain", False))
    if wildfire_warning:
        logger.info("WILDFIRE_WARNING — red flag and/or FIRMS fire detected")

    hail_detail = engine_details.get("hail") or {}
    if hail_detail.get("hail_indicated") and decision_rank.get(decision, 0) < decision_rank["WARNING"]:
        decision = "WARNING"
        logger.info("HAIL_INDICATED — min WARNING (VIL/echo_top)")
    if wildfire_warning and decision_rank.get(decision, 0) < decision_rank["WARNING"]:
        decision = "WARNING"
        logger.info("WILDFIRE_CERTAIN — min WARNING (red flag/FIRMS)")
    if hail_detail.get("hail_size_estimate") == "baseball":
        decision = "EMERGENCY"
        logger.info("BASEBALL_HAIL — force EMERGENCY (life safety)")

    seasonal_ctx = seasonal_profile.get("seasonal_context", "")
    if seasonal_profile.get("false_alarm_risk") == "HIGH":
        seasonal_ctx += " — elevated false alarm risk"

    response = {
        "region": region,
        "timestamp": timestamp,
        "decision": decision,
        "flash_flood_warning": flash_flood_warning,
        "wildfire_warning": wildfire_warning,
        "seasonal_context": seasonal_ctx.strip(),
        "seasonal_profile": seasonal_profile,
        "convergence_count": convergence_count,
        "engine_scores": engine_scores,
        "convergence_engines": convergence_engines,
        "saddle_active": engine_scores.get("saddle", 0.0) > 0.0,
        "flash_collapse_override": flash_collapse_override,
        "decision_before_veto": decision_before_veto,
        "inst_quality_applied": inst_quality_applied,
        "chorus_veto_applied": chorus_veto_applied,
        "siren_decision": siren_decision,
        "column_dry_count": column_dry_count,
        "stillness_count": stillness_count,
        "weak_forcing_count": weak_forcing_count,
        "dewpoint_depression_f": dd_value,
        "motion_correlation": motion_correlation,
        "confidence": confidence,
        "consequence_multiplier": consequence_multiplier,
        "vulnerability_flag": vulnerability_flag,
        "duration_class": duration_class,
        "duration_message": duration_message if decision != "CLEAR" else None,
        "tri_facilities": tri_facilities,
        "hazmat_score": hazmat_score,
        "hazmat_elevated": hazmat_elevated,
        "upper_air_available": bool(payload.get("upper_air")),
        "composite_stp": (payload.get("upper_air") or {}).get("significant_tornado_parameter"),
        "engine_details": engine_details,
        "hail_size_estimate": hail_detail.get("hail_size_estimate"),
        "siren_summary": siren_summary,
        "siren_gate_applied": siren_gate_applied,
    }
    response["audit_hash"] = _canonical_hash(response)

    if convergence_count >= GAIA_THRESHOLDS["warning_convergence"]:
        publish_simple(
            source="convergence_detector",
            event_type="convergence_alert",
            payload={
                "region": region,
                "services_count": convergence_count,
                "unique_services": convergence_engines,
                "combined_instability": round(sum(real_scores[name] for name in convergence_engines) / max(1, convergence_count), 4),
            },
            context={"region": region},
            metrics={"instability": max_score},
        )

    event_seq = publish_simple(
        source="gaia_governor",
        event_type="gaia_decision",
        payload={**response, "station_observations": station_observations, "engine_details": engine_details},
        context={"region": region},
        metrics={"instability": max_score},
    )

    record_pid_event(region, convergence_count / max(len(real_scores), 1), decision)
    record_decision(decision, max_score, claim_id=region, actor="gaia_governor")

    proposals = CORRELATION_MINER.mine(_bus_event_history())
    if proposals:
        publish_simple(
            source="correlation_miner",
            event_type="rule_proposal",
            payload={"proposal_count": len(proposals), "proposals": proposals},
            context={"region": region},
            metrics={"instability": 0.0},
        )

    if decision in ("WARNING", "EMERGENCY") or flash_flood_warning or wildfire_warning:
        try:
            from runtime.alerts.alert_formatter import format_from_governor_result
            from runtime.alerts.alert_dispatcher import dispatch
            alerts = format_from_governor_result(response)
            if alerts:
                dispatch(alerts)
        except Exception as e:
            logger.debug("Alert dispatch failed: %s", e)
    if MAAT_ENGINE is not None and not os.environ.get("GAIA_NO_EVIDENCE"):
        try:
            MAAT_ENGINE.handle_event(
                SimpleEvent(
                    event_id=f"gaia-decision-{event_seq}",
                    event_type="gaia_decision",
                    payload={**response, "observations": station_observations},
                    context={"region": region},
                    metrics={"instability": max_score},
                )
            )
        except Exception:
            pass

    LAST_STATUS.update(
        {
            "decision": decision,
            "convergence_count": convergence_count,
            "engine_scores": engine_scores,
            "region": region,
            "timestamp": timestamp,
        }
    )
    try:
        EVENT_MEMORY.record_prediction(response)
    except Exception:
        pass
    return response


@app.on_event("startup")
async def startup() -> None:
    init_bus()


@app.get("/health")
async def health() -> dict:
    return {
        "system": "GAIA",
        "status": "operational",
        "decision_tier": LAST_STATUS.get("decision", "CLEAR"),
        "engines_reporting": len([v for v in LAST_STATUS.get("engine_scores", {}).values() if v is not None]),
        "convergence_count": LAST_STATUS.get("convergence_count", 0),
        "uptime_seconds": int(time.time() - START_TS),
    }


@app.post("/analyze")
async def analyze(payload: dict) -> dict:
    return compute_decision_for_payload(payload)


if __name__ == "__main__":
    if FastAPI is None:
        raise RuntimeError("fastapi is not installed; use compute_decision_for_payload() in test mode or install FastAPI to run the server")
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=int(os.environ.get("GAIA_PORT", "7780")))
