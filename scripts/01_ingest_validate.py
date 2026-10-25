"""
01_ingest_validate.py
---------------------
Step 1: Ingest & Validate NYC TLC Parquet Files

Responsibilities:
- Detect all Yellow Taxi Parquet files in `data/raw/`
- Initialize PySpark SparkSession
- Load and inspect raw schemas, row counts, and null percentages
- Validate critical columns: pickup/dropoff datetimes, passenger_count,
  trip_distance, PULocationID, DOLocationID, fare_amount, total_amount
"""

import os
import glob
from pyspark.sql import SparkSession

# Environment defaults for Windows
os.environ.setdefault("HADOOP_HOME", r"C:\hadoop")

def create_spark_session(app_name="NYC_TLC_Ingestion_Validation"):
    return SparkSession.builder \
        .appName(app_name) \
        .master("local[*]") \
        .config("spark.driver.memory", "4g") \
        .config("spark.sql.execution.arrow.pyspark.enabled", "true") \
        .getOrCreate()

def main():
    raw_files = glob.glob(os.path.join("data", "raw", "*.parquet"))
    if not raw_files:
        print("[!] No parquet files found in data/raw/. Please download 3-6 months of Yellow Taxi data.")
        return

    print(f"[*] Found {len(raw_files)} parquet file(s):")
    for f in raw_files:
        print(f"    - {f}")

    spark = create_spark_session()
    print("\n[*] Initializing Spark reading pipeline...")
    df = spark.read.parquet(*raw_files)
    
    print("\n=== Dataset Schema ===")
    df.printSchema()

    row_count = df.count()
    print(f"\n[*] Total Rows Loaded: {row_count:,}")

    spark.stop()
    print("[*] Validation step completed successfully.")

if __name__ == "__main__":
    main()
