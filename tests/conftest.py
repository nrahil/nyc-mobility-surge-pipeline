"""
tests/conftest.py
-----------------
Pytest configuration and shared fixtures for PySpark & ETL testing.
"""

import sys
import os
from pathlib import Path
import pytest
from pyspark.sql import SparkSession
from pyspark.sql.types import (
    StructType,
    StructField,
    StringType,
    IntegerType,
    DoubleType,
    TimestampType
)
from datetime import datetime

# Ensure project root is available to tests
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.spark_session import configure_pyspark_environment


@pytest.fixture(scope="session")
def spark_test_session():
    """
    Creates a single lightweight local SparkSession for the entire test suite.
    """
    configure_pyspark_environment()
    
    spark = (
        SparkSession.builder
        .master("local[1]")
        .appName("NYC_Pipeline_UnitTests")
        .config("spark.driver.memory", "1g")
        .config("spark.sql.shuffle.partitions", "2")
        .config("spark.ui.enabled", "false")
        .config("spark.ui.showConsoleProgress", "false")
        .getOrCreate()
    )
    spark.sparkContext.setLogLevel("ERROR")
    yield spark
    spark.stop()


@pytest.fixture
def sample_raw_trips_df(spark_test_session):
    """
    Produces a small, deterministic DataFrame containing both valid records and edge cases
    (e.g., negative fares, excessive passenger counts, zero duration) for testing ETL rules.
    """
    schema = StructType([
        StructField("VendorID", IntegerType(), True),
        StructField("tpep_pickup_datetime", TimestampType(), True),
        StructField("tpep_dropoff_datetime", TimestampType(), True),
        StructField("passenger_count", DoubleType(), True),
        StructField("trip_distance", DoubleType(), True),
        StructField("RatecodeID", DoubleType(), True),
        StructField("store_and_fwd_flag", StringType(), True),
        StructField("PULocationID", IntegerType(), True),
        StructField("DOLocationID", IntegerType(), True),
        StructField("payment_type", IntegerType(), True),
        StructField("fare_amount", DoubleType(), True),
        StructField("extra", DoubleType(), True),
        StructField("mta_tax", DoubleType(), True),
        StructField("tip_amount", DoubleType(), True),
        StructField("tolls_amount", DoubleType(), True),
        StructField("improvement_surcharge", DoubleType(), True),
        StructField("total_amount", DoubleType(), True),
        StructField("congestion_surcharge", DoubleType(), True),
        StructField("airport_fee", DoubleType(), True),
    ])

    data = [
        # 1. Valid ride: Monday 8:00 AM, 15 min, 3 miles, $15 fare, zone 100 -> 101
        (1, datetime(2023, 5, 1, 8, 0, 0), datetime(2023, 5, 1, 8, 15, 0), 1.0, 3.0, 1.0, "N", 100, 101, 1, 15.0, 0.0, 0.5, 3.0, 0.0, 1.0, 19.5, 2.5, 0.0),
        # 2. Valid ride: Saturday 11:30 PM, 20 min, 5 miles, $25 fare, zone 100 -> 102
        (1, datetime(2023, 5, 6, 23, 30, 0), datetime(2023, 5, 6, 23, 50, 0), 2.0, 5.0, 1.0, "N", 100, 102, 1, 25.0, 1.0, 0.5, 5.0, 0.0, 1.0, 32.5, 2.5, 0.0),
        # 3. Invalid ride: negative fare (-10.0) -> SHOULD BE FILTERED
        (1, datetime(2023, 5, 1, 9, 0, 0), datetime(2023, 5, 1, 9, 10, 0), 1.0, 2.0, 1.0, "N", 100, 101, 2, -10.0, 0.0, 0.5, 0.0, 0.0, 1.0, -9.5, 0.0, 0.0),
        # 4. Invalid ride: 0 passengers -> SHOULD BE FILTERED
        (1, datetime(2023, 5, 1, 9, 0, 0), datetime(2023, 5, 1, 9, 10, 0), 0.0, 2.0, 1.0, "N", 100, 101, 1, 12.0, 0.0, 0.5, 2.0, 0.0, 1.0, 15.5, 2.5, 0.0),
        # 5. Invalid ride: zero duration (dropoff == pickup) -> SHOULD BE FILTERED
        (1, datetime(2023, 5, 1, 9, 0, 0), datetime(2023, 5, 1, 9, 0, 0), 1.0, 0.0, 1.0, "N", 100, 101, 1, 5.0, 0.0, 0.5, 0.0, 0.0, 1.0, 6.5, 2.5, 0.0),
        # 6. Invalid ride: excessive passenger count (9) -> SHOULD BE FILTERED
        (1, datetime(2023, 5, 1, 10, 0, 0), datetime(2023, 5, 1, 10, 15, 0), 9.0, 3.0, 1.0, "N", 100, 101, 1, 18.0, 0.0, 0.5, 3.0, 0.0, 1.0, 22.5, 2.5, 0.0),
        # 7. Invalid ride: out of year bounds (2020) -> SHOULD BE FILTERED
        (1, datetime(2020, 1, 1, 8, 0, 0), datetime(2020, 1, 1, 8, 15, 0), 1.0, 3.0, 1.0, "N", 100, 101, 1, 15.0, 0.0, 0.5, 3.0, 0.0, 1.0, 19.5, 2.5, 0.0),
    ]

    return spark_test_session.createDataFrame(data, schema)
