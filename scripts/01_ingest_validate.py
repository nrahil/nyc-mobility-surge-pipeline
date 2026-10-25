"""
01_ingest_validate.py
---------------------
Phase 2 - Step 1: Ingest & Validate NYC TLC Parquet Files

Usage:
    python scripts/01_ingest_validate.py
    python scripts/01_ingest_validate.py --max-files 2
    python scripts/01_ingest_validate.py --sample-fraction 0.05
"""

import sys
import argparse
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import RAW_DATA_DIR
from src.spark_session import spark_session_scope
from src.validation import validate_raw_dataset


def parse_arguments():
    parser = argparse.ArgumentParser(description="NYC TLC Parquet Ingestion and Data Validation")
    parser.add_argument(
        "--raw-dir",
        type=str,
        default=str(RAW_DATA_DIR),
        help="Path to folder containing raw Parquet files (default: data/raw)"
    )
    parser.add_argument(
        "--max-files",
        type=int,
        default=None,
        help="Optional limit on number of Parquet files to inspect"
    )
    parser.add_argument(
        "--sample-fraction",
        type=float,
        default=None,
        help="Optional sampling fraction between 0.01 and 1.0 for high-speed profiling"
    )
    return parser.parse_args()


def main():
    args = parse_arguments()
    print("[*] Launching Spark Session for Schema Validation...")

    with spark_session_scope(app_name="NYC_TLC_Schema_Validation") as spark:
        report = validate_raw_dataset(
            spark=spark,
            raw_dir=args.raw_dir,
            max_files=args.max_files,
            sample_fraction=args.sample_fraction
        )
        report.print_summary()

        if not report.is_valid:
            print("[X] Validation FAILED. Please review dataset before starting PySpark processing.")
            sys.exit(1)
        else:
            print("[OK] All checks passed. Dataset is ready for PySpark processing.")


if __name__ == "__main__":
    main()
