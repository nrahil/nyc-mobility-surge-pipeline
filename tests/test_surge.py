"""
tests/test_surge.py
-------------------
Unit tests for the Surge Pricing Simulation engine.
"""

import pytest
import pandas as pd
import numpy as np

from src.surge import calculate_zone_surge_multiplier, compute_surge_pricing


def test_calculate_zone_surge_multiplier_tiers():
    """Verifies that surge multipliers follow the tiered rules exactly."""
    p50, p75, p90 = 50.0, 75.0, 90.0

    # Demand >= 90th percentile -> 2.5x
    assert calculate_zone_surge_multiplier(95, p50, p75, p90) == 2.50
    assert calculate_zone_surge_multiplier(90, p50, p75, p90) == 2.50

    # Demand >= 75th percentile and < 90th -> 1.8x
    assert calculate_zone_surge_multiplier(80, p50, p75, p90) == 1.80
    assert calculate_zone_surge_multiplier(75, p50, p75, p90) == 1.80

    # Demand >= 50th percentile and < 75th -> 1.3x
    assert calculate_zone_surge_multiplier(60, p50, p75, p90) == 1.30
    assert calculate_zone_surge_multiplier(50, p50, p75, p90) == 1.30

    # Demand < 50th percentile -> 1.0x (standard pricing)
    assert calculate_zone_surge_multiplier(20, p50, p75, p90) == 1.00


def test_compute_surge_pricing_simulation():
    """
    Simulates demand across 10 hours for a zone and verifies
    simulated fare calculation.
    """
    # Create test data for zone 10 across 10 hours with known trip counts: 10, 20, ..., 100
    df = pd.DataFrame({
        "PULocationID": [10] * 10,
        "day_of_week": [1] * 10,
        "pickup_hour": list(range(10)),
        "trip_count": [10, 20, 30, 40, 50, 60, 70, 80, 90, 100],
        "avg_fare": [20.0] * 10
    })

    result = compute_surge_pricing(df)

    assert len(result) == 10
    assert "surge_multiplier" in result.columns
    assert "simulated_fare" in result.columns

    # Peak hour (trip_count=100) should have surge_multiplier 2.5x
    peak_row = result[result["trip_count"] == 100].iloc[0]
    assert peak_row["surge_multiplier"] == 2.50
    assert peak_row["simulated_fare"] == 50.0  # 20.0 * 2.5

    # Off-peak hour (trip_count=10) should have surge_multiplier 1.0x
    offpeak_row = result[result["trip_count"] == 10].iloc[0]
    assert offpeak_row["surge_multiplier"] == 1.00
    assert offpeak_row["simulated_fare"] == 20.0


def test_compute_surge_pricing_missing_columns():
    """Verifies that compute_surge_pricing raises ValueError when required columns are absent."""
    invalid_df = pd.DataFrame({"PULocationID": [1], "trip_count": [10]})
    with pytest.raises(ValueError):
        compute_surge_pricing(invalid_df)


def test_compute_surge_pricing_empty():
    """Verifies graceful handling of an empty DataFrame."""
    empty_df = pd.DataFrame(columns=["PULocationID", "day_of_week", "pickup_hour", "trip_count", "avg_fare"])
    result = compute_surge_pricing(empty_df)
    assert len(result) == 0
    assert "surge_multiplier" in result.columns
    assert "simulated_fare" in result.columns
