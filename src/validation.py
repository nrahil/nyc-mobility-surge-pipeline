"""
src/validation.py
-----------------
Data validation and schema integrity checking for NYC TLC raw files.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional
import glob
from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F

from src.config import REQUIRED_COLUMNS, resolve_safe_path, RAW_DATA_DIR


@dataclass
class ValidationReport:
    """Holds the summary metrics and validation status of raw datasets."""
    is_valid: bool
    total_files: int
    file_paths: List[str]
    total_rows: int
    missing_columns: List[str] = field(default_factory=list)
    null_counts: Dict[str, int] = field(default_factory=dict)
    null_percentages: Dict[str, float] = field(default_factory=dict)
    date_range: Optional[Dict[str, str]] = None
    warnings: List[str] = field(default_factory=list)

    def print_summary(self):
        print("\n" + "=" * 60)
        print("          DATA LAKE INGESTION & VALIDATION REPORT          ")
        print("=" * 60)
        print(f"Status               : {'PASSED [OK]' if self.is_valid else 'FAILED [X]'}")
        print(f"Files Found          : {self.total_files}")
        print(f"Total Rows Ingested  : {self.total_rows:,}")
        
        if self.missing_columns:
            print(f"[!] Missing Columns  : {', '.join(self.missing_columns)}")
        else:
            print("[OK] Schema Integrity : All required columns present.")
            
        if self.date_range:
            print(f"[OK] Pickup Dates     : {self.date_range.get('min_pickup')} -> {self.date_range.get('max_pickup')}")

        if self.null_percentages:
            print("\n--- Critical Column Null Profiles ---")
            for col_name, pct in self.null_percentages.items():
                count = self.null_counts.get(col_name, 0)
                flag = "[WARN]" if pct > 5.0 else "[OK]"
                print(f"  {flag} {col_name:<25}: {count:>8,} nulls ({pct:>6.2f}%)")

        if self.warnings:
            print("\n--- Pipeline Warnings ---")
            for warn in self.warnings:
                print(f"  [!] {warn}")
        print("=" * 60 + "\n")


def find_raw_parquet_files(raw_dir: Path | str = RAW_DATA_DIR, max_files: Optional[int] = None) -> List[str]:
    """
    Safely locates Parquet files in the specified directory.
    """
    safe_dir = resolve_safe_path(raw_dir)
    pattern = str(safe_dir / "*.parquet")
    files = sorted(glob.glob(pattern))
    
    if max_files and max_files > 0:
        files = files[:max_files]
        
    return files


def validate_schema(df: DataFrame, required_cols: Optional[List[str]] = None) -> List[str]:
    """
    Checks if all required columns exist in the DataFrame schema.
    Returns list of missing columns (empty list if valid).
    """
    required = required_cols or REQUIRED_COLUMNS
    actual_columns = set(df.columns)
    missing = [c for c in required if c not in actual_columns]
    return missing


def compute_null_profiles(df: DataFrame, target_cols: Optional[List[str]] = None, total_rows: int = 0) -> tuple[Dict[str, int], Dict[str, float]]:
    """
    Computes exact count and percentage of nulls for specified columns.
    """
    columns_to_check = [c for c in (target_cols or REQUIRED_COLUMNS) if c in df.columns]
    if not columns_to_check or total_rows == 0:
        return {}, {}

    agg_exprs = [F.count(F.when(F.col(c).isNull(), c)).alias(c) for c in columns_to_check]
    null_row = df.select(agg_exprs).collect()[0]

    null_counts = {}
    null_percentages = {}
    for col_name in columns_to_check:
        cnt = null_row[col_name]
        null_counts[col_name] = cnt
        null_percentages[col_name] = round((cnt / total_rows) * 100.0, 2)

    return null_counts, null_percentages


def validate_raw_dataset(
    spark: SparkSession,
    raw_dir: Path | str = RAW_DATA_DIR,
    max_files: Optional[int] = None,
    sample_fraction: Optional[float] = None
) -> ValidationReport:
    """
    Full validation pipeline for raw TLC Parquet files.
    """
    parquet_files = find_raw_parquet_files(raw_dir, max_files=max_files)
    if not parquet_files:
        return ValidationReport(
            is_valid=False,
            total_files=0,
            file_paths=[],
            total_rows=0,
            warnings=[f"No .parquet files found in target directory: {raw_dir}"]
        )

    df = spark.read.parquet(*parquet_files)
    
    if sample_fraction and 0.0 < sample_fraction < 1.0:
        df = df.sample(fraction=sample_fraction, seed=42)

    missing_cols = validate_schema(df)
    total_rows = df.count()
    
    null_counts, null_pcts = compute_null_profiles(df, REQUIRED_COLUMNS, total_rows=total_rows)

    date_range = None
    if "tpep_pickup_datetime" in df.columns and total_rows > 0:
        min_max = df.select(
            F.min("tpep_pickup_datetime").alias("min_dt"),
            F.max("tpep_pickup_datetime").alias("max_dt")
        ).collect()[0]
        date_range = {
            "min_pickup": str(min_max["min_dt"]),
            "max_pickup": str(min_max["max_dt"])
        }

    warnings = []
    if missing_cols:
        warnings.append(f"Missing required columns: {missing_cols}")
    if total_rows == 0:
        warnings.append("Dataset has zero records.")
        
    is_valid = (len(missing_cols) == 0) and (total_rows > 0)

    return ValidationReport(
        is_valid=is_valid,
        total_files=len(parquet_files),
        file_paths=parquet_files,
        total_rows=total_rows,
        missing_columns=missing_cols,
        null_counts=null_counts,
        null_percentages=null_pcts,
        date_range=date_range,
        warnings=warnings
    )
