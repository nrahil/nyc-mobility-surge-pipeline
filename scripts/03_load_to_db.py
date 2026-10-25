"""
03_load_to_db.py
----------------
Step 4: Load Summarized Data into Database (Serving Layer)

Responsibilities:
- Connect to SQLite (`db/mobility.db`) or PostgreSQL
- Apply schema definitions from `db/schema.sql`
- Ingest processed CSV files from `data/processed/`
- Merge with `data/lookup/taxi_zone_lookup.csv` for Borough and Zone names
- Populate SQL tables:
    * hourly_demand
    * zone_fare_stats
    * zone_hourly_heatmap
    * surge_pricing
    * daily_trends
"""

import os
import sqlite3
import pandas as pd
from sqlalchemy import create_engine

DB_PATH = os.path.join("db", "mobility.db")

def load_data():
    print(f"[*] Connecting to database at {DB_PATH}...")
    pass

if __name__ == "__main__":
    load_data()
