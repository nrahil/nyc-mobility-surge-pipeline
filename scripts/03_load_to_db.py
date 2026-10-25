"""
03_load_to_db.py
----------------
Phase 3: Load Processed Tables into Serving Database (SQLite / PostgreSQL)

Usage:
    python scripts/03_load_to_db.py
    python scripts/03_load_to_db.py --db-target db/mobility.db
    python scripts/03_load_to_db.py --db-target postgresql://user:pass@localhost:5432/mobility
"""

import sys
import argparse
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import DB_FILE, PROCESSED_DATA_DIR, LOOKUP_FILE
from src.db import run_database_loader, SCHEMA_FILE


def parse_arguments():
    parser = argparse.ArgumentParser(description="NYC TLC Serving Layer Database Loader")
    parser.add_argument(
        "--db-target",
        type=str,
        default=str(DB_FILE),
        help="Target database path or SQLAlchemy connection URL (default: db/mobility.db)"
    )
    parser.add_argument(
        "--processed-dir",
        type=str,
        default=str(PROCESSED_DATA_DIR),
        help="Path to folder containing processed CSV files (default: data/processed)"
    )
    parser.add_argument(
        "--lookup-file",
        type=str,
        default=str(LOOKUP_FILE),
        help="Path to taxi_zone_lookup.csv (default: data/lookup/taxi_zone_lookup.csv)"
    )
    parser.add_argument(
        "--schema-file",
        type=str,
        default=str(SCHEMA_FILE),
        help="Path to schema.sql (default: db/schema.sql)"
    )
    return parser.parse_args()


def main():
    args = parse_arguments()
    try:
        report = run_database_loader(
            db_target=args.db_target,
            processed_dir=args.processed_dir,
            lookup_file=args.lookup_file,
            schema_file=args.schema_file
        )
        if not report.is_valid:
            print("[X] Database loading completed with errors. See report above.", file=sys.stderr)
            sys.exit(1)
        else:
            print("[OK] All tables loaded and verified successfully.")
    except Exception as e:
        print(f"[X] Database loader encountered an unhandled exception: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
