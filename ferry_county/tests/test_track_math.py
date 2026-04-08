from backend.services.track_service import haversine_miles, polyline_length_miles


def test_haversine_short_segment():
    # ~0.05 mi order of magnitude for small offset near 48N
    d = haversine_miles(48.55, -118.5, 48.551, -118.5)
    assert 0.04 < d < 0.12


def test_polyline_two_points():
    pts = [(48.55, -118.5), (48.551, -118.501)]
    m = polyline_length_miles(pts)
    assert m > 0
