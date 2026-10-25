"""
tests/test_dashboard.py
-----------------------
Unit tests for the Streamlit dashboard components, coordinates, and map builders.
"""

import pytest
import pandas as pd
import folium

from dashboard.app import ZONE_COORDINATES, build_folium_map, CUSTOM_CSS, get_cached_engine


def test_zone_coordinates_validity():
    """Verifies that all defined zone coordinates are valid geospatial lat/long bounds for NYC."""
    for puid, (lat, lon, label) in ZONE_COORDINATES.items():
        assert 40.5 <= lat <= 40.9, f"Latitude {lat} for {label} is outside NYC bounding box"
        assert -74.3 <= lon <= -73.6, f"Longitude {lon} for {label} is outside NYC bounding box"
        assert len(label) > 0


def test_build_folium_map():
    """Verifies that Folium map generates correctly with marker elements."""
    sample_hotspots = pd.DataFrame({
        "PULocationID": [132, 237, 161],
        "zone_name": ["JFK Airport", "Upper East Side South", "Midtown Center"],
        "borough": ["Queens", "Manhattan", "Manhattan"],
        "total_trips": [150000, 140000, 128000],
        "avg_fare": [60.9, 12.3, 15.2],
        "total_revenue": [11600000.0, 2770000.0, 3030000.0]
    })

    fmap = build_folium_map(sample_hotspots)
    assert isinstance(fmap, folium.Map)
    
    # Check that children / markers were added
    children_keys = list(fmap._children.keys())
    assert len(children_keys) > 1  # tile layer + markers


def test_custom_css_structure():
    """Verifies that custom CSS contains necessary styling tokens."""
    assert "metric-card" in CUSTOM_CSS
    assert "surge-badge" in CUSTOM_CSS
    assert "badge-base" in CUSTOM_CSS
    assert "badge-max" in CUSTOM_CSS


def test_get_cached_engine_connectivity():
    """Verifies that dashboard engine factory initializes properly."""
    engine = get_cached_engine()
    assert engine is not None
    assert "sqlite" in str(engine.url)
