import os
import sys
import tempfile

sys.path.insert(0, ".")
os.environ["GAIA_BUS_MEMORY"] = "1"
os.environ["GAIA_DISABLE_EVIDENCE"] = "1"
os.environ["GAIA_STATE_PATH"] = os.path.join(
    tempfile.gettempdir(),
    "gaia_live_threshold_state.json",
)

from runtime.governor.governor import compute_decision_for_payload


def test_classic_severe_setup():
    payload = {
        "region": "hawkins_county_tn",
        "timestamp": "2026-03-21T18:00:00Z",
        "station_observations": [
            {
                "station_id": "KTRI",
                "timestamp": "2026-03-21T18:00:00Z",
                "pressure_mb": 1005.0,
                "temperature_f": 85.0,
                "dewpoint_f": 68.0,
                "prior_dewpoint_f": 60.0,
                "overnight_low_f": 68.0,
                "humidity_pct": 78.0,
                "wind_speed_mph": 25.0,
                "wind_direction_deg": 190.0,
                "prior_wind_direction_deg": 160.0,
                "wind_gust_mph": 35.0,
                "cape_jkg": 2200,
                "cin_jkg": -20,
                "precipitable_water_in": 2.1,
                "visibility_mi": 9.0,
                "text_description": "Towering cumulus",
                "pressure_trend": "falling_fast",
            },
            {
                "station_id": "KMOR",
                "timestamp": "2026-03-21T18:00:00Z",
                "pressure_mb": 1004.0,
                "temperature_f": 83.0,
                "dewpoint_f": 67.0,
                "prior_dewpoint_f": 61.0,
                "overnight_low_f": 66.0,
                "humidity_pct": 80.0,
                "wind_speed_mph": 22.0,
                "wind_direction_deg": 205.0,
                "prior_wind_direction_deg": 175.0,
                "wind_gust_mph": 34.0,
                "cape_jkg": 2100,
                "cin_jkg": -25,
                "precipitable_water_in": 2.0,
                "visibility_mi": 8.0,
                "text_description": "Towering cumulus",
                "pressure_trend": "falling",
            },
            {
                "station_id": "KTYS",
                "timestamp": "2026-03-21T18:00:00Z",
                "pressure_mb": 1003.0,
                "temperature_f": 84.0,
                "dewpoint_f": 69.0,
                "prior_dewpoint_f": 62.0,
                "overnight_low_f": 67.0,
                "humidity_pct": 79.0,
                "wind_speed_mph": 28.0,
                "wind_direction_deg": 220.0,
                "prior_wind_direction_deg": 180.0,
                "wind_gust_mph": 40.0,
                "cape_jkg": 2400,
                "cin_jkg": -15,
                "precipitable_water_in": 2.1,
                "visibility_mi": 10.0,
                "text_description": "Towering cumulus",
                "pressure_trend": "falling_fast",
            },
            {
                "station_id": "KGKT",
                "timestamp": "2026-03-21T18:00:00Z",
                "pressure_mb": 1004.5,
                "temperature_f": 82.0,
                "dewpoint_f": 68.0,
                "prior_dewpoint_f": 60.0,
                "overnight_low_f": 65.0,
                "humidity_pct": 81.0,
                "wind_speed_mph": 20.0,
                "wind_direction_deg": 210.0,
                "prior_wind_direction_deg": 178.0,
                "wind_gust_mph": 32.0,
                "cape_jkg": 2000,
                "cin_jkg": -18,
                "precipitable_water_in": 1.9,
                "visibility_mi": 10.0,
                "text_description": "Cumulonimbus",
                "pressure_trend": "falling",
            },
        ],
        "environmental_context": {
            "recent_event_severity": 0.35,
            "precip_7d_ratio": 1.5,
            "stream_level_ratio": 1.1,
            "drought_class": 0,
        },
        "radar_fixture": {
            "composite_reflectivity": 68.0,
            "rotation_couplet_kt": 42.0,
            "velocity_max": 32.0,
            "velocity_min": -28.0,
            "vil": 58.0,
            "echo_top_km": 13.0,
        },
        "lightning_fixture": {
            "flash_rate_per_min": 24.0,
            "energy_j": 1800.0,
            "available": True,
        },
    }
    result = compute_decision_for_payload(payload)
    scores = result["engine_scores"]
    assert scores["pressure"] > 0.6, result
    assert scores["thermal"] > 0.7, result
    assert scores["moisture"] > 0.7, result
    assert scores["shear"] > 0.5, result
    assert scores["instability"] > 0.6, result
    assert scores["historical_analog"] > 0.5, result
    assert scores["infrastructure"] == 0.0, result
    assert scores["environmental"] > 0.4, result
    assert scores["oscillation"] >= 0.5, result
    assert result["convergence_count"] >= 6, result
    assert result["decision"] in {"WARNING", "EMERGENCY"}, result
    print("PASS: GAIA synthetic severe setup integration")


if __name__ == "__main__":
    test_classic_severe_setup()
    print("GAIA INTEGRATION TEST PASSED")
