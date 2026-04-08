from backend.schemas.api import TrackSyncPayload


def test_track_sync_payload_parses():
    p = TrackSyncPayload.model_validate(
        {
            "road_id": 1,
            "points": [
                {"lon": -118.5, "lat": 48.55, "accuracy_m": 5.0},
                {"lon": -118.51, "lat": 48.56},
            ],
        }
    )
    assert p.road_id == 1
    assert len(p.points) == 2
