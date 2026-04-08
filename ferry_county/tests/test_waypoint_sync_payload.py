from backend.schemas.api import WaypointSyncPayload


def test_waypoint_sync_payload_parses():
    p = WaypointSyncPayload.model_validate(
        {
            "lat": 48.55,
            "lon": -118.5,
            "road_id": 2,
            "waypoint_type": "material_site",
            "buy_america_certified": True,
            "material_cost": 120.5,
            "vendor": "ACME",
        }
    )
    assert p.lat == 48.55
    assert p.buy_america_certified is True
