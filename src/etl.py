"""
src/etl.py
----------
Core PySpark ETL Pipeline: Data Cleaning, Feature Engineering, Aggregations, and Export.
"""

from pathlib import Path
from typing import Dict, List, Optional
import os
import pandas as pd
from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import IntegerType, DoubleType

from src.config import (
    CLEANING_RULES,
    PROCESSED_DATA_DIR,
    LOOKUP_FILE,
    RAW_DATA_DIR,
    TABLE_FILES,
    resolve_safe_path,
)
from src.validation import find_raw_parquet_files


def clean_trip_data(
    df: DataFrame,
    rules: Optional[Dict] = None
) -> DataFrame:
    """
    Applies data quality filters to eliminate outliers, invalid rides,
    and measurement anomalies according to TLC business rules.
    """
    cfg = rules or CLEANING_RULES
    min_passengers = cfg.get("min_passengers", 1)
    max_passengers = cfg.get("max_passengers", 6)
    min_fare = cfg.get("min_fare", 2.50)
    max_fare = cfg.get("max_fare", 500.00)
    min_dist = cfg.get("min_distance_miles", 0.10)
    max_dist = cfg.get("max_distance_miles", 150.00)
    min_duration = cfg.get("min_duration_minutes", 1.0)
    max_duration = cfg.get("max_duration_minutes", 300.0)
    min_year = cfg.get("min_year", 2023)
    max_year = cfg.get("max_year", 2024)

    # Calculate trip duration in minutes
    duration_min_col = (
        F.unix_timestamp("tpep_dropoff_datetime") - F.unix_timestamp("tpep_pickup_datetime")
    ) / 60.0

    cleaned_df = (
        df.filter(F.col("tpep_pickup_datetime").isNotNull() & F.col("tpep_dropoff_datetime").isNotNull())
        .filter(F.col("PULocationID").isNotNull() & (F.col("PULocationID") > 0) & (F.col("PULocationID") <= 265))
        .filter(F.col("DOLocationID").isNotNull() & (F.col("DOLocationID") > 0) & (F.col("DOLocationID") <= 265))
        .filter((F.col("passenger_count") >= min_passengers) & (F.col("passenger_count") <= max_passengers))
        .filter((F.col("fare_amount") >= min_fare) & (F.col("fare_amount") <= max_fare))
        .filter((F.col("trip_distance") >= min_dist) & (F.col("trip_distance") <= max_dist))
        .filter((duration_min_col >= min_duration) & (duration_min_col <= max_duration))
        .filter(
            (F.year("tpep_pickup_datetime") >= min_year) &
            (F.year("tpep_pickup_datetime") <= max_year)
        )
    )

    return cleaned_df


def engineer_features(df: DataFrame) -> DataFrame:
    """
    Enriches cleaned trip records with temporal and spatial mobility metrics.
    Features:
    - trip_duration_minutes
    - pickup_hour (0-23)
    - pickup_day_of_week (0=Mon ... 6=Sun)
    - pickup_date (yyyy-MM-dd)
    - pickup_month (1-12)
    - is_weekend (1 if Sat/Sun, else 0)
    - avg_speed_mph
    """
    duration_minutes = (
        F.unix_timestamp("tpep_dropoff_datetime") - F.unix_timestamp("tpep_pickup_datetime")
    ) / 60.0

    # Spark dayofweek: 1=Sun, 2=Mon, ..., 7=Sat -> convert to 0=Mon ... 6=Sun
    day_of_week_expr = (F.dayofweek("tpep_pickup_datetime") + 5) % 7

    # Calculate speed in mph (protect against division by zero)
    raw_speed = F.col("trip_distance") / (duration_minutes / 60.0)
    safe_speed = F.when(raw_speed > 100.0, 100.0).otherwise(raw_speed)

    enriched_df = (
        df.withColumn("trip_duration_minutes", F.round(duration_minutes, 2))
        .withColumn("pickup_hour", F.hour("tpep_pickup_datetime").cast(IntegerType()))
        .withColumn("pickup_day_of_week", day_of_week_expr.cast(IntegerType()))
        .withColumn("pickup_date", F.date_format("tpep_pickup_datetime", "yyyy-MM-dd"))
        .withColumn("pickup_month", F.month("tpep_pickup_datetime").cast(IntegerType()))
        .withColumn(
            "is_weekend",
            F.when(day_of_week_expr.isin([5, 6]), 1).otherwise(0).cast(IntegerType())
        )
        .withColumn("avg_speed_mph", F.round(safe_speed, 2).cast(DoubleType()))
    )

    return enriched_df


def load_zone_lookup(spark: SparkSession, lookup_path: Path | str = LOOKUP_FILE) -> Optional[DataFrame]:
    """
    Safely loads the Taxi Zone Lookup table into a Spark DataFrame.
    """
    resolved_path = resolve_safe_path(lookup_path)
    if not resolved_path.exists():
        print(f"[!] Warning: Lookup file not found at {resolved_path}. Zone names will not be joined.")
        return None

    return (
        spark.read.option("header", "true")
        .option("inferSchema", "true")
        .csv(str(resolved_path))
        .select(
            F.col("LocationID").cast(IntegerType()).alias("lookup_LocationID"),
            F.col("Borough").alias("borough"),
            F.col("Zone").alias("zone_name"),
            F.col("service_zone")
        )
    )


def compute_hourly_demand(df: DataFrame) -> DataFrame:
    """
    Aggregates metrics by day of week and hour (168 rows total).
    Columns: day_of_week, pickup_hour, trip_count, avg_fare, avg_speed_mph, avg_passengers, total_revenue
    """
    return (
        df.groupBy("pickup_day_of_week", "pickup_hour")
        .agg(
            F.count(F.lit(1)).alias("trip_count"),
            F.round(F.avg("fare_amount"), 2).alias("avg_fare"),
            F.round(F.avg("avg_speed_mph"), 2).alias("avg_speed_mph"),
            F.round(F.avg("passenger_count"), 2).alias("avg_passengers"),
            F.round(F.sum("total_amount"), 2).alias("total_revenue")
        )
        .withColumnRenamed("pickup_day_of_week", "day_of_week")
        .orderBy("day_of_week", "pickup_hour")
    )


def compute_zone_fare_stats(df: DataFrame, zone_lookup: Optional[DataFrame] = None) -> DataFrame:
    """
    Aggregates volume, fare, and distance per pickup zone (PULocationID),
    enriched with Borough and Zone name if lookup data is present.
    """
    stats = (
        df.groupBy("PULocationID")
        .agg(
            F.count(F.lit(1)).alias("total_trips"),
            F.round(F.avg("fare_amount"), 2).alias("avg_fare"),
            F.round(F.avg("trip_distance"), 2).alias("avg_distance"),
            F.round(F.sum("total_amount"), 2).alias("total_revenue")
        )
    )

    if zone_lookup is not None:
        stats = (
            stats.join(
                zone_lookup,
                stats.PULocationID == zone_lookup.lookup_LocationID,
                how="left"
            )
            .select(
                "PULocationID",
                F.coalesce(F.col("zone_name"), F.lit("Unknown")).alias("zone_name"),
                F.coalesce(F.col("borough"), F.lit("Unknown")).alias("borough"),
                F.coalesce(F.col("service_zone"), F.lit("Unknown")).alias("service_zone"),
                "total_trips",
                "avg_fare",
                "avg_distance",
                "total_revenue"
            )
        )
    else:
        stats = stats.select(
            "PULocationID",
            F.lit("Unknown").alias("zone_name"),
            F.lit("Unknown").alias("borough"),
            F.lit("Unknown").alias("service_zone"),
            "total_trips",
            "avg_fare",
            "avg_distance",
            "total_revenue"
        )

    return stats.orderBy(F.desc("total_trips"))


def compute_zone_hourly_heatmap(df: DataFrame) -> DataFrame:
    """
    Aggregates trip demand and average fare for each zone x day_of_week x hour combination.
    This serves as the primary input for the Surge Pricing engine.
    """
    return (
        df.groupBy("PULocationID", "pickup_day_of_week", "pickup_hour")
        .agg(
            F.count(F.lit(1)).alias("trip_count"),
            F.round(F.avg("fare_amount"), 2).alias("avg_fare"),
            F.round(F.avg("avg_speed_mph"), 2).alias("avg_speed_mph")
        )
        .withColumnRenamed("pickup_day_of_week", "day_of_week")
        .orderBy("PULocationID", "day_of_week", "pickup_hour")
    )


def compute_daily_trends(df: DataFrame) -> DataFrame:
    """
    Aggregates macro trends per calendar day (trip volume, total revenue, average fare, distance).
    """
    return (
        df.groupBy("pickup_date")
        .agg(
            F.count(F.lit(1)).alias("trip_count"),
            F.round(F.sum("total_amount"), 2).alias("total_revenue"),
            F.round(F.avg("fare_amount"), 2).alias("avg_fare"),
            F.round(F.avg("trip_distance"), 2).alias("avg_distance")
        )
        .orderBy("pickup_date")
    )


def export_dataframe_to_csv(df: DataFrame, output_filepath: Path | str) -> None:
    """
    Safely exports an aggregated Spark DataFrame to a single clean CSV file
    for high-speed ingestion into SQLite / PostgreSQL serving layers.
    """
    safe_output = resolve_safe_path(output_filepath)
    safe_output.parent.mkdir(parents=True, exist_ok=True)
    
    # Convert to pandas and export cleanly
    pandas_df = df.toPandas()
    pandas_df.to_csv(safe_output, index=False)
    print(f"[OK] Exported {len(pandas_df):,} rows -> {safe_output}")


def run_etl_pipeline(
    spark: SparkSession,
    raw_dir: Path | str = RAW_DATA_DIR,
    output_dir: Path | str = PROCESSED_DATA_DIR,
    lookup_file: Path | str = LOOKUP_FILE,
    max_files: Optional[int] = None,
    sample_fraction: Optional[float] = None
) -> Dict[str, pd.DataFrame]:
    """
    Executes the complete PySpark ETL pipeline end-to-end:
    Ingest -> Clean -> Engineer Features -> Aggregate -> Export
    """
    parquet_files = find_raw_parquet_files(raw_dir, max_files=max_files)
    if not parquet_files:
        raise FileNotFoundError(f"No raw parquet files found in {raw_dir}")

    print(f"[*] Ingesting {len(parquet_files)} Parquet file(s)...")
    raw_df = spark.read.parquet(*parquet_files)

    if sample_fraction and 0.0 < sample_fraction < 1.0:
        print(f"[*] Subsampling dataset with fraction: {sample_fraction}")
        raw_df = raw_df.sample(fraction=sample_fraction, seed=42)

    raw_count = raw_df.count()
    print(f"[*] Total Raw Rows Ingested: {raw_count:,}")

    print("[*] Applying data quality filters (cleaning)...")
    cleaned_df = clean_trip_data(raw_df)
    clean_count = cleaned_df.count()
    print(f"[*] Cleaned Rows Remaining: {clean_count:,} (Removed {raw_count - clean_count:,} anomalies)")

    print("[*] Engineering features (temporal, speed, weekend flags)...")
    enriched_df = engineer_features(cleaned_df)

    print("[*] Loading taxi zone lookup data...")
    zone_lookup = load_zone_lookup(spark, lookup_file)

    print("[*] Computing analytical aggregations...")
    hourly_demand = compute_hourly_demand(enriched_df)
    zone_fare_stats = compute_zone_fare_stats(enriched_df, zone_lookup)
    zone_hourly_heatmap = compute_zone_hourly_heatmap(enriched_df)
    daily_trends = compute_daily_trends(enriched_df)

    # Safe export to processed directory
    safe_out_dir = resolve_safe_path(output_dir)
    safe_out_dir.mkdir(parents=True, exist_ok=True)

    print("[*] Exporting aggregated tables to CSV...")
    export_dataframe_to_csv(hourly_demand, safe_out_dir / TABLE_FILES["hourly_demand"])
    export_dataframe_to_csv(zone_fare_stats, safe_out_dir / TABLE_FILES["zone_fare_stats"])
    export_dataframe_to_csv(zone_hourly_heatmap, safe_out_dir / TABLE_FILES["zone_hourly_heatmap"])
    export_dataframe_to_csv(daily_trends, safe_out_dir / TABLE_FILES["daily_trends"])

    print("[OK] PySpark ETL pipeline completed successfully!")

    return {
        "hourly_demand": hourly_demand.toPandas(),
        "zone_fare_stats": zone_fare_stats.toPandas(),
        "zone_hourly_heatmap": zone_hourly_heatmap.toPandas(),
        "daily_trends": daily_trends.toPandas()
    }
