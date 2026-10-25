"""
src/db.py
---------
Database connection, schema management, CSV ingestion, and integrity verification.
Supports SQLite (zero-config local) and PostgreSQL serving layers.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional
import os
import pandas as pd
from sqlalchemy import create_engine, text, Engine

from src.config import (
    DB_FILE,
    PROCESSED_DATA_DIR,
    LOOKUP_FILE,
    TABLE_FILES,
    BASE_DIR,
    resolve_safe_path,
)

SCHEMA_FILE = BASE_DIR / "db" / "schema.sql"


@dataclass
class DatabaseReport:
    """Holds database integrity statistics after loading."""
    is_valid: bool
    db_target: str
    table_counts: Dict[str, int] = field(default_factory=dict)
    indexes_created: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    def print_summary(self):
        print("\n" + "=" * 60)
        print("          SERVING LAYER DATABASE INGESTION REPORT          ")
        print("=" * 60)
        print(f"Target Database      : {self.db_target}")
        print(f"Ingestion Status     : {'PASSED [OK]' if self.is_valid else 'FAILED [X]'}")
        print("\n--- Table Record Counts ---")
        for table, count in self.table_counts.items():
            print(f"  [OK] {table:<25}: {count:>8,} records")

        if self.indexes_created:
            print("\n--- Active Database Indexes ---")
            for idx in self.indexes_created:
                print(f"  [OK] {idx}")

        if self.errors:
            print("\n--- Errors Encountered ---")
            for err in self.errors:
                print(f"  [X] {err}")
        print("=" * 60 + "\n")


def get_db_engine(db_target: Optional[str | Path] = None) -> Engine:
    """
    Creates an optimized SQLAlchemy engine.
    For SQLite: automatically ensures parent directory exists and enables WAL mode.
    """
    if db_target is None:
        target_path = resolve_safe_path(DB_FILE)
        target_path.parent.mkdir(parents=True, exist_ok=True)
        conn_str = f"sqlite:///{target_path}"
    elif str(db_target).startswith(("postgresql://", "sqlite://")):
        conn_str = str(db_target)
    else:
        target_path = resolve_safe_path(db_target)
        target_path.parent.mkdir(parents=True, exist_ok=True)
        conn_str = f"sqlite:///{target_path}"

    engine = create_engine(conn_str, future=True)

    # Enable WAL (Write-Ahead Logging) for SQLite for high concurrent read performance
    if "sqlite" in conn_str:
        with engine.connect() as conn:
            conn.execute(text("PRAGMA journal_mode=WAL;"))
            conn.execute(text("PRAGMA synchronous=NORMAL;"))
            conn.commit()

    return engine


def init_database_schema(engine: Engine, schema_path: Path | str = SCHEMA_FILE) -> None:
    """
    Reads schema.sql and creates tables and indexes.
    """
    safe_schema = resolve_safe_path(schema_path)
    if not safe_schema.exists():
        raise FileNotFoundError(f"Schema definition file not found at: {safe_schema}")

    with open(safe_schema, "r", encoding="utf-8") as f:
        sql_content = f.read()

    # Split into discrete executable SQL statements
    statements = [stmt.strip() for stmt in sql_content.split(";") if stmt.strip()]

    with engine.begin() as conn:
        for stmt in statements:
            conn.execute(text(stmt))


def load_lookup_dataframe(lookup_path: Path | str = LOOKUP_FILE) -> Optional[pd.DataFrame]:
    """
    Safely loads taxi zone lookup mapping (LocationID -> zone_name, borough, service_zone).
    """
    safe_lookup = resolve_safe_path(lookup_path)
    if not safe_lookup.exists():
        return None

    df = pd.read_csv(safe_lookup)
    rename_map = {
        "LocationID": "PULocationID",
        "Borough": "borough",
        "Zone": "zone_name",
        "service_zone": "service_zone"
    }
    return df.rename(columns=rename_map)[["PULocationID", "borough", "zone_name"]]


def enrich_table_with_zones(df: pd.DataFrame, lookup_df: Optional[pd.DataFrame]) -> pd.DataFrame:
    """
    Enriches tabular data with Borough and Zone names if PULocationID is present.
    """
    if lookup_df is None or "PULocationID" not in df.columns:
        return df

    # If already enriched, skip
    if "borough" in df.columns and "zone_name" in df.columns:
        return df

    merged = df.merge(lookup_df, on="PULocationID", how="left")
    merged["borough"] = merged["borough"].fillna("Unknown")
    merged["zone_name"] = merged["zone_name"].fillna("Unknown")
    return merged


def load_csv_to_table(
    engine: Engine,
    csv_path: Path | str,
    table_name: str,
    lookup_df: Optional[pd.DataFrame] = None
) -> int:
    """
    Ingests a processed CSV file into the target database table.
    """
    safe_csv = resolve_safe_path(csv_path)
    if not safe_csv.exists():
        raise FileNotFoundError(f"Processed file {safe_csv} not found.")

    df = pd.read_csv(safe_csv)
    enriched_df = enrich_table_with_zones(df, lookup_df)

    enriched_df.to_sql(
        name=table_name,
        con=engine,
        if_exists="replace",
        index=False,
        chunksize=10000
    )
    return len(enriched_df)


def verify_database_integrity(engine: Engine) -> DatabaseReport:
    """
    Validates row counts and indexes in the serving database.
    """
    expected_tables = [
        "hourly_demand",
        "zone_fare_stats",
        "zone_hourly_heatmap",
        "surge_pricing",
        "daily_trends"
    ]
    table_counts = {}
    errors = []

    with engine.connect() as conn:
        for tbl in expected_tables:
            try:
                res = conn.execute(text(f"SELECT COUNT(*) FROM {tbl}"))
                count = res.scalar() or 0
                table_counts[tbl] = count
                if count == 0:
                    errors.append(f"Table '{tbl}' is empty.")
            except Exception as e:
                errors.append(f"Failed to query table '{tbl}': {e}")

        # Check indexes if SQLite
        indexes = []
        try:
            res = conn.execute(text("SELECT name FROM sqlite_master WHERE type='index' AND name NOT LIKE 'sqlite_%'"))
            indexes = [row[0] for row in res.fetchall()]
        except Exception:
            pass

    is_valid = len(errors) == 0 and all(c > 0 for c in table_counts.values())

    return DatabaseReport(
        is_valid=is_valid,
        db_target=str(engine.url),
        table_counts=table_counts,
        indexes_created=indexes,
        errors=errors
    )


def run_database_loader(
    db_target: Optional[str | Path] = None,
    processed_dir: Path | str = PROCESSED_DATA_DIR,
    lookup_file: Path | str = LOOKUP_FILE,
    schema_file: Path | str = SCHEMA_FILE
) -> DatabaseReport:
    """
    Main orchestration routine for Phase 3 serving layer ingestion.
    """
    engine = get_db_engine(db_target)
    print(f"[*] Initializing database schema at {engine.url}...")
    init_database_schema(engine, schema_path=schema_file)

    lookup_df = load_lookup_dataframe(lookup_file)
    safe_proc_dir = resolve_safe_path(processed_dir)

    table_mapping = {
        "hourly_demand": safe_proc_dir / TABLE_FILES["hourly_demand"],
        "zone_fare_stats": safe_proc_dir / TABLE_FILES["zone_fare_stats"],
        "zone_hourly_heatmap": safe_proc_dir / TABLE_FILES["zone_hourly_heatmap"],
        "surge_pricing": safe_proc_dir / TABLE_FILES["surge_pricing"],
        "daily_trends": safe_proc_dir / TABLE_FILES["daily_trends"],
    }

    print("[*] Ingesting processed datasets into database tables...")
    for table_name, csv_path in table_mapping.items():
        if csv_path.exists():
            rows = load_csv_to_table(engine, csv_path, table_name, lookup_df=lookup_df)
            print(f"  [OK] Ingested {rows:>8,} rows into table: {table_name}")
        else:
            print(f"  [WARN] Skipping {table_name} — file not found: {csv_path}")

    # Re-apply indexes after bulk loading
    print("[*] Ensuring query optimization indexes are established...")
    with engine.begin() as conn:
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_hourly_demand_time ON hourly_demand(day_of_week, pickup_hour);"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_zone_heatmap_lookup ON zone_hourly_heatmap(PULocationID, day_of_week, pickup_hour);"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_zone_heatmap_borough ON zone_hourly_heatmap(borough, day_of_week, pickup_hour);"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_surge_pricing_zone ON surge_pricing(PULocationID, day_of_week, pickup_hour);"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_surge_pricing_borough ON surge_pricing(borough, day_of_week, pickup_hour);"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_daily_trends_date ON daily_trends(pickup_date);"))

    print("[*] Validating database integrity...")
    report = verify_database_integrity(engine)
    report.print_summary()
    return report
