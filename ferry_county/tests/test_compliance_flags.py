from __future__ import annotations

from datetime import date

from backend.models.treatment import Treatment
from backend.services.compliance_engine import compliance_flags_for_treatment


def test_davis_bacon_warning_when_over_threshold_and_not_certified():
    t = Treatment(
        road_id=1,
        treatment_date=date(2026, 1, 1),
        miles_treated=0.1,
        contractor_invoice_amount=2500.0,
        davis_bacon_certified=False,
    )
    flags = compliance_flags_for_treatment(t)
    assert flags.davis_bacon_warning is True


def test_match_ratio_flag():
    t = Treatment(
        road_id=1,
        treatment_date=date(2026, 1, 1),
        miles_treated=0.1,
        amount_federal=75.0,
        amount_match=25.0,
        davis_bacon_certified=True,
        contractor_invoice_amount=100.0,
    )
    flags = compliance_flags_for_treatment(t)
    assert flags.match_ratio_ok is True
    assert abs((flags.match_ratio or 0) - 0.25) < 1e-9
