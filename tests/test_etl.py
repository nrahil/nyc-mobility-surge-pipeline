"""
tests/test_etl.py
-----------------
Unit tests for data cleaning, feature engineering, and analytical aggregations.
"""

from src.etl import (
    clean_trip_data,
    engineer_features,
    compute_hourly_demand,
    compute_zone_fare_stats,
    compute_zone_hourly_heatmap,
    compute_daily_trends
)


def test_clean_trip_data_filters_anomalies(sample_raw_trips_df):
    """
    Tests that clean_trip_data rejects:
    - negative fares
    - passenger counts <= 0 or > 6
    - duration < 1 minute (dropoff == pickup)
    - dates outside allowable range (2020)
    Only the 2 valid trips should remain.
    """
    cleaned_df = clean_trip_data(sample_raw_trips_df)
    remaining_count = cleaned_df.count()
    
    assert remaining_count == 2, f"Expected exactly 2 valid records to remain, found {remaining_count}"


def test_engineer_features(sample_raw_trips_df):
    """
    Validates temporal extraction and speed calculation:
    - 2023-05-01 is Monday (day_of_week = 0, is_weekend = 0)
    - 2023-05-06 is Saturday (day_of_week = 5, is_weekend = 1)
    """
    cleaned = clean_trip_data(sample_raw_trips_df)
    enriched = engineer_features(cleaned)

    rows = enriched.orderBy("tpep_pickup_datetime").collect()
    assert len(rows) == 2

    # Ride 1: Monday 8:00 AM, 15 min, 3 miles -> 12 mph
    r1 = rows[0]
    assert r1["pickup_hour"] == 8
    assert r1["pickup_day_of_week"] == 0  # Monday
    assert r1["is_weekend"] == 0
    assert r1["trip_duration_minutes"] == 15.0
    assert r1["avg_speed_mph"] == 12.0

    # Ride 2: Saturday 11:30 PM (23:30), 20 min, 5 miles -> 15 mph
    r2 = rows[1]
    assert r2["pickup_hour"] == 23
    assert r2["pickup_day_of_week"] == 5  # Saturday
    assert r2["is_weekend"] == 1
    assert r2["trip_duration_minutes"] == 20.0
    assert r2["avg_speed_mph"] == 15.0


def test_compute_hourly_demand(sample_raw_trips_df):
    """Verifies hourly demand aggregation produces distinct day x hour entries."""
    cleaned = clean_trip_data(sample_raw_trips_df)
    enriched = engineer_features(cleaned)
    hourly = compute_hourly_demand(enriched).collect()

    assert len(hourly) == 2
    for row in hourly:
        assert row["trip_count"] == 1
        assert row["avg_fare"] > 0


def test_compute_zone_fare_stats(sample_raw_trips_df):
    """Verifies zone aggregation sums trips correctly for PULocationID 100."""
    cleaned = clean_trip_data(sample_raw_trips_df)
    enriched = engineer_features(cleaned)
    zone_stats = compute_zone_fare_stats(enriched).collect()

    # Both valid trips originated in PULocationID 100
    assert len(zone_stats) == 1
    assert zone_stats[0]["PULocationID"] == 100
    assert zone_stats[0]["total_trips"] == 2
    assert zone_stats[0]["avg_fare"] == 20.0  # (15 + 25) / 2
    assert zone_stats[0]["avg_distance"] == 4.0  # (3 + 5) / 2


def test_compute_daily_trends(sample_raw_trips_df):
    """Verifies daily aggregation groups by calendar date."""
    cleaned = clean_trip_data(sample_raw_trips_df)
    enriched = engineer_features(cleaned)
    daily = compute_daily_trends(enriched).collect()

    # Two distinct dates: 2023-05-01 and 2023-05-06
    assert len(daily) == 2
    dates = [row["pickup_date"] for row in daily]
    assert "2023-05-01" in dates
    assert "2023-05-06" in dates
