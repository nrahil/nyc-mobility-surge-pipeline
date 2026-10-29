"""
tests/test_queries.py
---------------------
Unit tests for dashboard analytical queries against the serving layer database.
"""

import pytest
from sqlalchemy import text

from src.db import get_db_engine, init_database_schema, SCHEMA_FILE
from src.queries import (
    get_kpi_metrics,
    get_hourly_heatmap_data,
    get_top_hotspots,
    get_hourly_speed_trend,
    get_daily_trends_data,
    get_surge_pricing_distribution,
    get_distinct_filter_options,
    simulate_zone_surge,
    get_demand_forecast,
    get_demand_spike_alerts,
)


@pytest.fixture
def populated_test_db(tmp_path):
    """Initializes and seeds an in-memory or temp SQLite database with known records."""
    db_path = tmp_path / "test_queries.db"
    engine = get_db_engine(db_path)
    init_database_schema(engine, schema_path=SCHEMA_FILE)

    with engine.begin() as conn:
        # Seed zone_fare_stats
        conn.execute(text("""
            INSERT INTO zone_fare_stats (PULocationID, zone_name, borough, service_zone, total_trips, avg_fare, avg_distance, total_revenue)
            VALUES 
                (132, 'JFK Airport', 'Queens', 'Airports', 10000, 60.0, 15.0, 600000.0),
                (237, 'Upper East Side South', 'Manhattan', 'Yellow Zone', 8000, 15.0, 2.0, 120000.0),
                (161, 'Midtown Center', 'Manhattan', 'Yellow Zone', 5000, 18.0, 2.5, 90000.0)
        """))

        # Seed hourly_demand
        conn.execute(text("""
            INSERT INTO hourly_demand (day_of_week, pickup_hour, trip_count, avg_fare, avg_speed_mph, avg_passengers, total_revenue)
            VALUES 
                (0, 8, 1200, 20.0, 11.5, 1.3, 24000.0),
                (0, 18, 2500, 22.0, 9.8, 1.4, 55000.0),
                (5, 23, 3000, 28.0, 16.0, 1.6, 84000.0)
        """))

        # Seed zone_hourly_heatmap
        conn.execute(text("""
            INSERT INTO zone_hourly_heatmap (PULocationID, zone_name, borough, day_of_week, pickup_hour, trip_count, avg_fare, avg_speed_mph)
            VALUES 
                (132, 'JFK Airport', 'Queens', 0, 18, 500, 60.0, 15.0),
                (132, 'JFK Airport', 'Queens', 0, 3, 50, 60.0, 20.0),
                (237, 'Upper East Side South', 'Manhattan', 0, 18, 400, 15.0, 8.0)
        """))

        # Seed surge_pricing
        conn.execute(text("""
            INSERT INTO surge_pricing (PULocationID, zone_name, borough, day_of_week, pickup_hour, trip_count, avg_fare, surge_multiplier, simulated_fare)
            VALUES 
                (132, 'JFK Airport', 'Queens', 0, 18, 500, 60.0, 2.5, 150.0),
                (132, 'JFK Airport', 'Queens', 0, 3, 50, 60.0, 1.0, 60.0),
                (237, 'Upper East Side South', 'Manhattan', 0, 18, 400, 15.0, 1.8, 27.0)
        """))

        # Seed daily_trends
        conn.execute(text("""
            INSERT INTO daily_trends (pickup_date, trip_count, total_revenue, avg_fare, avg_distance)
            VALUES 
                ('2023-01-01', 50000, 1200000.0, 24.0, 4.5),
                ('2023-01-02', 45000, 1100000.0, 24.4, 4.6)
        """))

    yield engine
    engine.dispose()


def test_get_kpi_metrics(populated_test_db):
    """Verifies KPI calculations across all boroughs and with borough filter."""
    overall_kpi = get_kpi_metrics(populated_test_db)
    assert overall_kpi["total_trips"] == 23000
    assert overall_kpi["total_revenue"] == 810000.0
    assert overall_kpi["peak_hour"] == 23  # Saturday 23:00 has 3000 trips

    manhattan_kpi = get_kpi_metrics(populated_test_db, borough="Manhattan")
    assert manhattan_kpi["total_trips"] == 13000  # 8000 + 5000
    assert manhattan_kpi["total_revenue"] == 210000.0


def test_get_top_hotspots(populated_test_db):
    """Verifies hotspot ranking and limit enforcement."""
    top_2 = get_top_hotspots(populated_test_db, limit=2)
    assert len(top_2) == 2
    assert top_2.iloc[0]["zone_name"] == "JFK Airport"
    assert top_2.iloc[0]["total_trips"] == 10000


def test_get_daily_trends(populated_test_db):
    """Verifies daily time-series retrieval."""
    daily = get_daily_trends_data(populated_test_db)
    assert len(daily) == 2
    assert daily.iloc[0]["pickup_date"] == "2023-01-01"


def test_simulate_zone_surge(populated_test_db):
    """Verifies simulated surge rule query for JFK Airport at 18:00."""
    result = simulate_zone_surge(populated_test_db, pulocation_id=132, day_of_week=0, pickup_hour=18)
    assert result is not None
    assert result["surge_multiplier"] == 2.5
    assert result["simulated_fare"] == 150.0
    assert result["demand_percentile"] == 100.0
    assert result["fare_uplift"] == 90.0

    # Non-existent window
    empty = simulate_zone_surge(populated_test_db, pulocation_id=999, day_of_week=0, pickup_hour=0)
    assert empty is None


def test_get_distinct_filter_options(populated_test_db):
    """Verifies distinct borough and zone extraction."""
    boroughs, zones = get_distinct_filter_options(populated_test_db)
    assert "All Boroughs" in boroughs
    assert "Queens" in boroughs
    assert "Manhattan" in boroughs
    assert "JFK Airport" in zones
    assert zones["JFK Airport"] == 132


def test_get_hourly_heatmap_data(populated_test_db):
    """Verifies that heatmap data always returns a complete 7x24 grid."""
    heatmap_all = get_hourly_heatmap_data(populated_test_db)
    assert heatmap_all.shape == (7, 24)
    assert list(heatmap_all.columns) == list(range(24))
    assert list(heatmap_all.index) == ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    assert heatmap_all.loc["Monday", 8] == 1200
    assert heatmap_all.loc["Monday", 18] == 2500
    assert heatmap_all.loc["Monday", 0] == 0  # Missing hour is 0-filled

    # Sparse borough test
    heatmap_queens = get_hourly_heatmap_data(populated_test_db, borough="Queens")
    assert heatmap_queens.shape == (7, 24)
    assert heatmap_queens.loc["Monday", 18] == 500
    assert heatmap_queens.loc["Monday", 0] == 0


def test_demand_forecast(populated_test_db):
    """Forecast returns a bounded six-hour seasonal outlook."""
    from datetime import datetime
    forecast = get_demand_forecast(
        populated_test_db,
        horizon=6,
        reference_time=datetime(2023, 1, 2, 7, 30),
        use_ml=False,
    )
    assert len(forecast) == 6
    assert forecast.iloc[0]["predicted_trips"] == 1200
    assert (forecast["lower_bound"] <= forecast["predicted_trips"]).all()
    assert (forecast["upper_bound"] >= forecast["predicted_trips"]).all()


def test_demand_spike_alerts(populated_test_db):
    """Spike detection compares observations with their zone baseline."""
    alerts = get_demand_spike_alerts(populated_test_db, limit=5)
    assert not alerts.empty
    assert alerts.iloc[0]["increase_pct"] >= 35
    assert alerts.iloc[0]["severity"] in {"Elevated", "Critical"}

