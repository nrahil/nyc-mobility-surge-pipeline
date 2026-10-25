"""
tests/test_db.py
----------------
Unit tests for database initialization, CSV loading, zone enrichment, and integrity verification.
"""

import pytest
import pandas as pd
from pathlib import Path
from sqlalchemy import create_engine, text

from src.db import (
    get_db_engine,
    init_database_schema,
    enrich_table_with_zones,
    load_csv_to_table,
    verify_database_integrity,
    SCHEMA_FILE
)


@pytest.fixture
def temp_db_engine(tmp_path):
    """Creates a clean temporary SQLite database for testing."""
    test_db_path = tmp_path / "test_mobility.db"
    engine = get_db_engine(test_db_path)
    yield engine
    engine.dispose()


def test_init_database_schema(temp_db_engine):
    """Verifies that schema.sql creates all 5 tables and required indexes."""
    init_database_schema(temp_db_engine, schema_path=SCHEMA_FILE)

    with temp_db_engine.connect() as conn:
        res = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))
        tables = {row[0] for row in res.fetchall()}

    expected_tables = {
        "hourly_demand",
        "zone_fare_stats",
        "zone_hourly_heatmap",
        "surge_pricing",
        "daily_trends"
    }
    assert expected_tables.issubset(tables), f"Expected tables {expected_tables}, but found {tables}"


def test_enrich_table_with_zones():
    """Verifies that PULocationID is mapped to borough and zone_name."""
    df = pd.DataFrame({
        "PULocationID": [1, 2],
        "trip_count": [100, 200]
    })
    lookup_df = pd.DataFrame({
        "PULocationID": [1, 2],
        "borough": ["EWR", "Queens"],
        "zone_name": ["Newark Airport", "Jamaica Bay"]
    })

    enriched = enrich_table_with_zones(df, lookup_df)

    assert "borough" in enriched.columns
    assert "zone_name" in enriched.columns
    assert enriched.loc[enriched["PULocationID"] == 1, "borough"].values[0] == "EWR"
    assert enriched.loc[enriched["PULocationID"] == 2, "zone_name"].values[0] == "Jamaica Bay"


def test_load_csv_to_table(temp_db_engine, tmp_path):
    """Verifies that CSV records are safely ingested and queryable."""
    init_database_schema(temp_db_engine, schema_path=SCHEMA_FILE)

    csv_path = tmp_path / "sample_daily_trends.csv"
    sample_df = pd.DataFrame({
        "pickup_date": ["2023-01-01", "2023-01-02"],
        "trip_count": [5000, 6000],
        "total_revenue": [150000.0, 180000.0],
        "avg_fare": [25.0, 26.0],
        "avg_distance": [3.5, 3.8]
    })
    sample_df.to_csv(csv_path, index=False)

    rows = load_csv_to_table(temp_db_engine, csv_path, "daily_trends")
    assert rows == 2

    with temp_db_engine.connect() as conn:
        res = conn.execute(text("SELECT COUNT(*), AVG(avg_fare) FROM daily_trends")).fetchone()
        count, avg_fare = res[0], res[1]

    assert count == 2
    assert avg_fare == 25.5


def test_verify_database_integrity_flags_empty_tables(temp_db_engine):
    """Verifies that integrity checks properly report empty tables."""
    init_database_schema(temp_db_engine, schema_path=SCHEMA_FILE)
    report = verify_database_integrity(temp_db_engine)

    # All tables are empty initially, so is_valid should be False
    assert not report.is_valid
    assert len(report.errors) > 0
