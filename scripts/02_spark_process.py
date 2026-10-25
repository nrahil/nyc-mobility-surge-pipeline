"""
02_spark_process.py
-------------------
Step 2: Core PySpark Big Data ETL Pipeline

Responsibilities:
- Ingest all raw Parquet files from `data/raw/`
- Data Cleaning:
    * passenger_count between 1 and 6
    * fare_amount between $2.50 and $500
    * trip_distance between 0.1 and 150 miles
    * trip duration between 1 minute and 5 hours
- Feature Engineering:
    * pickup_hour (0-23), pickup_day_of_week (0=Mon..6=Sun)
    * trip_duration_minutes, avg_speed_mph
- Aggregations:
    * hourly_demand (168 rows: 7 days x 24 hours)
    * zone_fare_stats (aggregated per PULocationID)
    * zone_hourly_heatmap (PULocationID x day x hour)
    * daily_trends (trip counts, revenue per calendar day)
- Export clean summaries to `data/processed/`
"""

import os
import glob
from pyspark.sql import SparkSession
from pyspark.sql import functions as F

os.environ.setdefault("HADOOP_HOME", r"C:\hadoop")

def get_spark():
    return SparkSession.builder \
        .appName("NYC_TLC_Spark_ETL") \
        .master("local[*]") \
        .config("spark.driver.memory", "4g") \
        .config("spark.sql.shuffle.partitions", "8") \
        .getOrCreate()

def main():
    print("[*] Starting PySpark Processing Pipeline...")
    # Pipeline implementation details will be loaded here
    pass

if __name__ == "__main__":
    main()
