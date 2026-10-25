"""
src/surge.py
------------
Dynamic Surge Pricing Simulation Engine based on zone-level demand percentiles.
"""

from pathlib import Path
from typing import Dict, Optional, Tuple
import pandas as pd
import numpy as np

from src.config import (
    PROCESSED_DATA_DIR,
    SURGE_CONFIG,
    TABLE_FILES,
    resolve_safe_path,
)


def calculate_zone_surge_multiplier(
    trip_count: float,
    p50: float,
    p75: float,
    p90: float,
    config: Optional[Dict] = None
) -> float:
    """
    Evaluates tiered surge pricing multiplier based on demand thresholds.
    """
    cfg = config or SURGE_CONFIG
    m_p90 = cfg.get("percentile_90_multiplier", 2.50)
    m_p75 = cfg.get("percentile_75_multiplier", 1.80)
    m_p50 = cfg.get("percentile_50_multiplier", 1.30)
    m_base = cfg.get("baseline_multiplier", 1.00)

    if trip_count >= p90 and p90 > 0:
        return m_p90
    elif trip_count >= p75 and p75 > 0:
        return m_p75
    elif trip_count >= p50 and p50 > 0:
        return m_p50
    else:
        return m_base


def compute_surge_pricing(
    df: pd.DataFrame,
    config: Optional[Dict] = None
) -> pd.DataFrame:
    """
    Calculates dynamic surge multipliers and simulated fares per zone, day, and hour.
    Input must contain: PULocationID, day_of_week, pickup_hour, trip_count, avg_fare.
    """
    required_cols = {"PULocationID", "day_of_week", "pickup_hour", "trip_count", "avg_fare"}
    missing = required_cols - set(df.columns)
    if missing:
        raise ValueError(f"Input DataFrame is missing required columns for surge simulation: {missing}")

    if df.empty:
        result_df = df.copy()
        result_df["surge_multiplier"] = 1.0
        result_df["simulated_fare"] = 0.0
        return result_df

    # Calculate zone-specific baseline percentiles across hours
    zone_quantiles = (
        df.groupby("PULocationID")["trip_count"]
        .quantile([0.50, 0.75, 0.90])
        .unstack(level=-1)
        .rename(columns={0.50: "p50", 0.75: "p75", 0.90: "p90"})
        .reset_index()
    )

    merged = df.merge(zone_quantiles, on="PULocationID", how="left")

    cfg = config or SURGE_CONFIG
    multipliers = []
    for _, row in merged.iterrows():
        mult = calculate_zone_surge_multiplier(
            trip_count=row["trip_count"],
            p50=row["p50"],
            p75=row["p75"],
            p90=row["p90"],
            config=cfg
        )
        multipliers.append(mult)

    merged["surge_multiplier"] = multipliers
    merged["simulated_fare"] = (merged["avg_fare"] * merged["surge_multiplier"]).round(2)

    output_columns = [
        "PULocationID",
        "day_of_week",
        "pickup_hour",
        "trip_count",
        "avg_fare",
        "surge_multiplier",
        "simulated_fare"
    ]
    
    return merged[output_columns].sort_values(
        by=["PULocationID", "day_of_week", "pickup_hour"]
    ).reset_index(drop=True)


def run_surge_pipeline(
    input_file: Path | str = PROCESSED_DATA_DIR / TABLE_FILES["zone_hourly_heatmap"],
    output_file: Path | str = PROCESSED_DATA_DIR / TABLE_FILES["surge_pricing"],
    config: Optional[Dict] = None
) -> pd.DataFrame:
    """
    Executes the Surge Pricing Simulation pipeline:
    Loads zone hourly demand -> Computes percentiles & multipliers -> Exports surge_pricing.csv
    """
    safe_input = resolve_safe_path(input_file)
    safe_output = resolve_safe_path(output_file)

    if not safe_input.exists():
        raise FileNotFoundError(
            f"Input demand file not found: {safe_input}. Please run the PySpark ETL step first."
        )

    print(f"[*] Loading demand heatmap from {safe_input}...")
    demand_df = pd.read_csv(safe_input)
    print(f"[*] Ingested {len(demand_df):,} zone-hour demand records.")

    print("[*] Simulating surge pricing model...")
    surge_df = compute_surge_pricing(demand_df, config=config)

    # Summary metrics
    surge_active_count = len(surge_df[surge_df["surge_multiplier"] > 1.0])
    surge_pct = (surge_active_count / len(surge_df) * 100.0) if len(surge_df) > 0 else 0
    avg_base_fare = surge_df["avg_fare"].mean()
    avg_sim_fare = surge_df["simulated_fare"].mean()

    print("\n=== Surge Pricing Simulation Summary ===")
    print(f"Total Evaluated Windows : {len(surge_df):,}")
    print(f"Surge-Triggered Windows : {surge_active_count:,} ({surge_pct:.1f}%)")
    print(f"Average Base Fare       : ${avg_base_fare:.2f}")
    print(f"Average Simulated Fare  : ${avg_sim_fare:.2f} (+{((avg_sim_fare / avg_base_fare - 1) * 100):.1f}% avg uplift)")

    safe_output.parent.mkdir(parents=True, exist_ok=True)
    surge_df.to_csv(safe_output, index=False)
    print(f"[OK] Saved surge pricing results -> {safe_output}\n")

    return surge_df
