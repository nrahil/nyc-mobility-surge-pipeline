"""
02_spark_process.py
-------------------
Phase 2 - Step 2: Core PySpark Big Data ETL Pipeline

Usage:
    python scripts/02_spark_process.py
    python scripts/02_spark_process.py --max-files 1 --sample-fraction 0.1
"""

import sys
import argparse
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import RAW_DATA_DIR, PROCESSED_DATA_DIR, LOOKUP_FILE
from src.spark_session import spark_session_scope
from src.etl import run_etl_pipeline


def parse_arguments():
    parser = argparse.ArgumentParser(description="NYC TLC PySpark ETL Processing Pipeline")
    parser.add_argument(
        "--raw-dir",
        type=str,
        default=str(RAW_DATA_DIR),
        help="Path to folder containing raw Parquet files (default: data/raw)"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=str(PROCESSED_DATA_DIR),
        help="Path to folder where processed tables are exported (default: data/processed)"
    )
    parser.add_argument(
        "--lookup-file",
        type=str,
        default=str(LOOKUP_FILE),
        help="Path to taxi_zone_lookup.csv (default: data/lookup/taxi_zone_lookup.csv)"
    )
    parser.add_argument(
        "--max-files",
        type=int,
        default=None,
        help="Limit number of parquet files processed (useful for rapid testing)"
    )
    parser.add_argument(
        "--sample-fraction",
        type=float,
        default=None,
        help="Fraction of dataset to sample (0.01 - 1.0) for rapid testing"
    )
    parser.add_argument(
        "--memory",
        type=str,
        default="4g",
        help="Spark driver memory allocation (e.g., 4g, 8g)"
    )
    parser.add_argument(
        "--partitions",
        type=int,
        default=8,
        help="Spark SQL shuffle partition count (default: 8)"
    )
    return parser.parse_args()


def main():
    args = parse_arguments()
    print("[*] Starting PySpark Processing Pipeline...")

    with spark_session_scope(
        app_name="NYC_TLC_PySpark_ETL",
        driver_memory=args.memory,
        shuffle_partitions=args.partitions
    ) as spark:
        try:
            results = run_etl_pipeline(
                spark=spark,
                raw_dir=args.raw_dir,
                output_dir=args.output_dir,
                lookup_file=args.lookup_file,
                max_files=args.max_files,
                sample_fraction=args.sample_fraction
            )
            print(f"[OK] Processed tables generated: {list(results.keys())}")
        except Exception as e:
            print(f"[X] Pipeline execution encountered an error: {e}", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    main()
