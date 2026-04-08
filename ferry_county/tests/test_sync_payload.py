from __future__ import annotations

from datetime import date

import pytest
from pydantic import ValidationError

from backend.schemas.api import TreatmentSyncPayload


def test_treatment_sync_payload_parses():
    p = TreatmentSyncPayload.model_validate(
        {
            "road_id": 1,
            "treatment_date": "2026-04-01",
            "miles_treated": 0.1,
        }
    )
    assert p.road_id == 1
    assert p.treatment_date == date(2026, 4, 1)


def test_treatment_sync_payload_rejects_bad_miles():
    with pytest.raises(ValidationError):
        TreatmentSyncPayload.model_validate(
            {
                "road_id": 1,
                "treatment_date": "2026-04-01",
                "miles_treated": -1,
            }
        )
