from __future__ import annotations

from backend.services.acreage import calculate_acres


def test_one_mile_fifteen_foot_buffer():
    assert abs(calculate_acres(1.0, 15.0) - 3.6363636363636362) < 1e-6


def test_ten_miles():
    assert abs(calculate_acres(10.0, 15.0) - 36.36363636363637) < 0.01
