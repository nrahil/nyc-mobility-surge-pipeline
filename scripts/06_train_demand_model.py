"""Train the city/borough hourly demand ML model from raw TLC Parquet files."""

from pathlib import Path
import sys

import pandas as pd
import pyarrow.parquet as pq

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.ml_forecast import train_model


def build_training_frame() -> pd.DataFrame:
    lookup = pd.read_csv(PROJECT_ROOT / "data" / "lookup" / "taxi_zone_lookup.csv")
    zone_to_borough = lookup.set_index("LocationID")["Borough"]
    official_boroughs = {"Bronx", "Brooklyn", "EWR", "Manhattan", "Queens", "Staten Island"}
    parts = []
    for path in sorted((PROJECT_ROOT / "data" / "raw").glob("yellow_tripdata_*.parquet")):
        table = pq.read_table(path, columns=["tpep_pickup_datetime", "PULocationID"])
        frame = table.to_pandas()
        frame["pickup_hour"] = pd.to_datetime(frame["tpep_pickup_datetime"]).dt.floor("h")
        frame["borough"] = frame["PULocationID"].map(zone_to_borough)
        frame = frame.dropna(subset=["pickup_hour", "borough"])
        # Remove timestamps outside the month encoded in the source file.
        expected_month = path.stem.rsplit("_", 1)[-1]
        frame = frame[frame["pickup_hour"].dt.strftime("%Y-%m") == expected_month]
        borough = frame[frame["borough"].isin(official_boroughs)].groupby(
            ["pickup_hour", "borough"], observed=True
        ).size().rename("trip_count").reset_index()
        city = frame.groupby("pickup_hour").size().rename("trip_count").reset_index()
        city["borough"] = "All Boroughs"
        parts.extend([borough, city])
        print(f"Prepared {path.name}: {len(frame):,} valid timestamp/location rows", flush=True)
    if not parts:
        raise FileNotFoundError("No yellow_tripdata_*.parquet files found in data/raw.")
    return pd.concat(parts, ignore_index=True).groupby(
        ["pickup_hour", "borough"], as_index=False, observed=True
    )["trip_count"].sum()


if __name__ == "__main__":
    metrics = train_model(build_training_frame())
    print("Saved gradient-boosting demand model")
    for key, value in metrics.items():
        print(f"  {key}: {value}")
