"""
tests/test_validation.py
------------------------
Unit tests for data validation, schema integrity checks, and security constraints.
"""

import pytest
from pathlib import Path
from pyspark.sql.types import StructType, StructField, StringType, IntegerType, DoubleType, TimestampType
from datetime import datetime

from src.validation import validate_schema, compute_null_profiles, find_raw_parquet_files
from src.config import resolve_safe_path, BASE_DIR, REQUIRED_COLUMNS


def test_validate_schema_success(sample_raw_trips_df):
    """Verifies that schema validation succeeds when all expected columns exist."""
    missing = validate_schema(sample_raw_trips_df, REQUIRED_COLUMNS)
    assert missing == [], f"Expected no missing columns, but got: {missing}"


def test_validate_schema_missing_columns(spark_test_session):
    """Verifies that missing critical columns are correctly flagged."""
    incomplete_schema = StructType([
        StructField("PULocationID", IntegerType(), True),
        StructField("fare_amount", DoubleType(), True),
    ])
    df = spark_test_session.createDataFrame([(1, 10.0)], incomplete_schema)
    missing = validate_schema(df, REQUIRED_COLUMNS)
    
    assert "tpep_pickup_datetime" in missing
    assert "tpep_dropoff_datetime" in missing
    assert "passenger_count" in missing
    assert "trip_distance" in missing


def test_compute_null_profiles(spark_test_session):
    """Verifies exact calculation of null counts and percentages."""
    schema = StructType([
        StructField("col_a", IntegerType(), True),
        StructField("col_b", StringType(), True),
    ])
    data = [
        (1, "val1"),
        (None, "val2"),
        (None, None),
        (4, None),
    ]
    df = spark_test_session.createDataFrame(data, schema)
    null_counts, null_pcts = compute_null_profiles(df, ["col_a", "col_b"], total_rows=4)

    assert null_counts["col_a"] == 2
    assert null_pcts["col_a"] == 50.0
    assert null_counts["col_b"] == 2
    assert null_pcts["col_b"] == 50.0


def test_find_raw_parquet_files_with_limit():
    """Verifies that file discovery respects max_files limits."""
    files = find_raw_parquet_files(max_files=2)
    assert len(files) <= 2


def test_security_resolve_safe_path():
    """
    Verifies that safe path resolution allows valid subpaths but rejects
    illegal directory traversal attempts.
    """
    # Valid relative path inside workspace
    safe = resolve_safe_path("data/raw")
    assert safe.is_dir()

    # Traversal attempt outside workspace to a non-existent or forbidden path
    with pytest.raises(ValueError):
        resolve_safe_path("../../non_existent_system_secret_xyz")
