"""
04_surge_pricing.py
-------------------
Phase 2 - Step 3: Surge Pricing Simulation Engine

Usage:
    python scripts/04_surge_pricing.py
    python scripts/04_surge_pricing.py --input-file data/processed/zone_hourly_heatmap.csv
"""

import sys
import argparse
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import PROCESSED_DATA_DIR, TABLE_FILES
from src.surge import run_surge_pipeline


def parse_arguments():
    parser = argparse.ArgumentParser(description="NYC TLC Surge Pricing Simulation Engine")
    parser.add_argument(
        "--input-file",
        type=str,
        default=str(PROCESSED_DATA_DIR / TABLE_FILES["zone_hourly_heatmap"]),
        help="Path to zone_hourly_heatmap.csv input"
    )
    parser.add_argument(
        "--output-file",
        type=str,
        default=str(PROCESSED_DATA_DIR / TABLE_FILES["surge_pricing"]),
        help="Path for generated surge_pricing.csv"
    )
    return parser.parse_args()


def main():
    args = parse_arguments()
    try:
        run_surge_pipeline(
            input_file=args.input_file,
            output_file=args.output_file
        )
    except Exception as e:
        print(f"[X] Surge Pricing simulation failed: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
