"""Distance / Haversine tests."""

from core.location import haversine_km


def test_haversine_same_point():
    assert haversine_km(51.22, 6.91, 51.22, 6.91) == 0


def test_haversine_nearby_cities_reasonable():
    # Rough distance between two nearby German city centers should be under ~20 km
    d = haversine_km(51.2200, 6.9100, 51.2277, 6.7735)
    assert 5 < d < 20
