"""
src/streaming.py
----------------
High-Throughput Real-Time Streaming Telemetry Producer & Surge Engine.
Simulates live GPS taxi ride dispatch events from raw NYC TLC data into the serving layer.
Supports both background threaded streaming and batch injection.
"""

from datetime import datetime
from pathlib import Path
import random
import threading
import time
from typing import Dict, List, Optional, Tuple, Any
import numpy as np
import pandas as pd
from sqlalchemy import text, Engine

from src.config import (
    BASE_DIR,
    DB_FILE,
    LOOKUP_FILE,
    RAW_DATA_DIR,
    SURGE_CONFIG,
    resolve_safe_path,
)
from src.db import get_db_engine, load_lookup_dataframe


class LiveStreamEngine:
    """
    Manages real-time taxi trip streaming, rolling surge computation,
    and concurrent ingestion into the live_trips serving table.
    """

    def __init__(self, db_target: Optional[str | Path] = None, pool_size: int = 10000):
        self.engine: Engine = get_db_engine(db_target)
        self.pool_size = pool_size
        self._zone_lookup: Dict[int, Tuple[str, str]] = {}
        self._trip_pool: List[Dict[str, Any]] = []
        self._pool_index: int = 0
        
        # Threading state for background streaming
        self._stop_event = threading.Event()
        self._stream_thread: Optional[threading.Thread] = None
        self._rate_per_sec: float = 10.0
        self._is_running: bool = False
        self._lock = threading.Lock()
        
        # Rolling demand counter per zone (PULocationID -> list of timestamp floats)
        self._recent_pings: Dict[int, List[float]] = {}
        
        # Initialize lookups and sample pool
        self._init_lookup()
        self._load_sample_pool()

    def _init_lookup(self) -> None:
        """Loads taxi zone names and boroughs into memory for instantaneous lookups."""
        lookup_df = load_lookup_dataframe(LOOKUP_FILE)
        if lookup_df is not None and not lookup_df.empty:
            for _, row in lookup_df.iterrows():
                try:
                    puid = int(row["PULocationID"])
                    zone = str(row["zone_name"])
                    boro = str(row["borough"])
                    self._zone_lookup[puid] = (zone, boro)
                except (ValueError, TypeError):
                    continue

    def _load_sample_pool(self) -> None:
        """
        Samples realistic historical trips from available raw Parquet files.
        Falls back to a synthetic generator if no Parquet files are present.
        """
        safe_raw_dir = resolve_safe_path(RAW_DATA_DIR)
        parquet_files = sorted(list(safe_raw_dir.glob("*.parquet")))

        if parquet_files:
            try:
                # Read a slice of columns from the first available parquet
                sample_path = parquet_files[0]
                cols = [
                    "PULocationID", "DOLocationID", "passenger_count",
                    "trip_distance", "fare_amount", "tip_amount", "total_amount"
                ]
                df = pd.read_parquet(sample_path, columns=cols).dropna()
                
                # Basic cleaning
                df = df[
                    (df["trip_distance"] > 0.2) & (df["trip_distance"] < 50.0) &
                    (df["fare_amount"] >= 3.0) & (df["fare_amount"] <= 250.0) &
                    (df["PULocationID"] > 0) & (df["PULocationID"] <= 265)
                ]
                
                sampled = df.sample(min(self.pool_size, len(df)), random_state=42)
                for _, row in sampled.iterrows():
                    puid = int(row["PULocationID"])
                    duid = int(row["DOLocationID"]) if pd.notnull(row["DOLocationID"]) else puid
                    dist = float(row["trip_distance"])
                    fare = float(row["fare_amount"])
                    tip = float(row["tip_amount"]) if pd.notnull(row["tip_amount"]) else 0.0
                    tot = float(row["total_amount"]) if pd.notnull(row["total_amount"]) else (fare + tip)
                    passengers = int(row["passenger_count"]) if pd.notnull(row["passenger_count"]) else 1
                    
                    # Estimate realistic duration and speed
                    duration_min = max(2.0, (dist / 14.0) * 60.0 + random.uniform(-2, 3))
                    speed = max(4.0, min(55.0, (dist / (duration_min / 60.0))))

                    self._trip_pool.append({
                        "PULocationID": puid,
                        "DOLocationID": duid,
                        "passenger_count": passengers,
                        "trip_distance": round(dist, 2),
                        "fare_amount": round(fare, 2),
                        "tip_amount": round(tip, 2),
                        "total_amount": round(tot, 2),
                        "speed_mph": round(speed, 1),
                        "duration_minutes": round(duration_min, 1)
                    })
            except Exception as e:
                print(f"[Streaming Warning] Error loading Parquet pool: {e}. Using synthetic fallback.")

        # If pool is still empty, populate with realistic NYC synthetic trips
        if not self._trip_pool:
            self._generate_synthetic_pool(count=1000)

    def _generate_synthetic_pool(self, count: int = 1000) -> None:
        """Generates realistic synthetic trip templates across major NYC zones."""
        common_zones = [132, 138, 237, 236, 161, 162, 186, 230, 142, 239, 68, 79]
        for _ in range(count):
            puid = random.choice(common_zones) if random.random() < 0.6 else random.randint(1, 263)
            duid = random.randint(1, 263)
            dist = round(random.uniform(0.8, 14.5), 2)
            base_fare = round(2.50 + dist * 2.80 + random.uniform(1.0, 5.0), 2)
            tip = round(base_fare * random.choice([0.15, 0.18, 0.20, 0.25]), 2) if random.random() < 0.75 else 0.0
            dur = round(max(3.0, (dist / 12.0) * 60.0 + random.uniform(-1, 4)), 1)
            spd = round(max(5.0, min(45.0, (dist / (dur / 60.0)))), 1)

            self._trip_pool.append({
                "PULocationID": puid,
                "DOLocationID": duid,
                "passenger_count": random.randint(1, 4),
                "trip_distance": dist,
                "fare_amount": base_fare,
                "tip_amount": tip,
                "total_amount": round(base_fare + tip + 2.50, 2),
                "speed_mph": spd,
                "duration_minutes": dur
            })

    def _calculate_live_surge(self, puid: int, current_time: float) -> Tuple[float, float]:
        """
        Dynamically calculates the surge multiplier based on recent event frequency
        in this zone over a sliding 45-second window.
        Returns (surge_multiplier, simulated_fare).
        """
        window_seconds = 45.0
        cutoff = current_time - window_seconds

        # Clean old timestamps
        pings = self._recent_pings.get(puid, [])
        valid_pings = [t for t in pings if t >= cutoff]
        valid_pings.append(current_time)
        self._recent_pings[puid] = valid_pings

        recent_count = len(valid_pings)

        # Multiplier tiers based on active burst intensity
        if recent_count >= 8:
            mult = SURGE_CONFIG.get("percentile_90_multiplier", 2.50)
        elif recent_count >= 5:
            mult = SURGE_CONFIG.get("percentile_75_multiplier", 1.80)
        elif recent_count >= 3:
            mult = SURGE_CONFIG.get("percentile_50_multiplier", 1.30)
        else:
            mult = SURGE_CONFIG.get("baseline_multiplier", 1.00)

        return mult

    def generate_trip_batch(self, count: int = 10) -> List[Dict[str, Any]]:
        """Generates a batch of enriched streaming trip records with live timestamps."""
        now_dt = datetime.now()
        now_str = now_dt.strftime("%Y-%m-%d %H:%M:%S")
        now_epoch = now_dt.timestamp()

        batch = []
        pool_len = len(self._trip_pool)

        for _ in range(count):
            template = self._trip_pool[self._pool_index % pool_len]
            self._pool_index += 1

            puid = template["PULocationID"]
            duid = template["DOLocationID"]
            
            # Lookup zone & borough
            zone_info = self._zone_lookup.get(puid, (f"Zone #{puid}", "Unknown"))
            zone_name, borough = zone_info[0], zone_info[1]

            # Evaluate real-time surge multiplier
            surge_mult = self._calculate_live_surge(puid, now_epoch)
            fare = template["fare_amount"]
            simulated_fare = round(fare * surge_mult, 2)
            total = round(simulated_fare + template["tip_amount"] + 2.50, 2)

            batch.append({
                "event_time": now_str,
                "PULocationID": puid,
                "DOLocationID": duid,
                "passenger_count": template["passenger_count"],
                "trip_distance": template["trip_distance"],
                "fare_amount": fare,
                "tip_amount": template["tip_amount"],
                "total_amount": total,
                "speed_mph": template["speed_mph"],
                "duration_minutes": template["duration_minutes"],
                "zone_name": zone_name,
                "borough": borough,
                "surge_multiplier": surge_mult,
                "simulated_fare": simulated_fare
            })

        return batch

    def inject_trips(self, count: int = 10) -> int:
        """
        Synchronously creates and inserts a batch of streaming trips into the database.
        Returns the number of trips inserted.
        """
        batch = self.generate_trip_batch(count=count)
        if not batch:
            return 0

        df = pd.DataFrame(batch)
        with self.engine.begin() as conn:
            df.to_sql("live_trips", conn, if_exists="append", index=False)

        # Periodically prune old records to prevent unbounded database growth
        self.trim_buffer_if_needed(max_records=12000, keep_records=8000)
        return len(batch)

    def trim_buffer_if_needed(self, max_records: int = 12000, keep_records: int = 8000) -> None:
        """Ensures the live buffer table does not exceed memory/disk limits."""
        try:
            with self.engine.begin() as conn:
                count_res = conn.execute(text("SELECT COUNT(*) FROM live_trips")).scalar()
                if count_res and count_res > max_records:
                    delete_sql = f"""
                        DELETE FROM live_trips 
                        WHERE id NOT IN (
                            SELECT id FROM live_trips ORDER BY id DESC LIMIT {keep_records}
                        )
                    """
                    conn.execute(text(delete_sql))
        except Exception as e:
            # Non-critical pruning error
            pass

    def clear_live_buffer(self) -> None:
        """Clears all records in the live_trips streaming table and resets counters."""
        with self.engine.begin() as conn:
            conn.execute(text("DELETE FROM live_trips;"))
        self._recent_pings.clear()

    def _stream_worker(self) -> None:
        """Background thread target for continuous ingestion."""
        batch_interval = 0.5  # Emit every 500ms
        while not self._stop_event.is_set():
            batch_count = max(1, int(self._rate_per_sec * batch_interval))
            try:
                self.inject_trips(count=batch_count)
            except Exception as e:
                print(f"[Streaming Producer Error]: {e}")
            time.sleep(batch_interval)

    def start_background_streaming(self, rate_per_sec: float = 10.0) -> bool:
        """Starts background streaming thread if not already running."""
        with self._lock:
            if self._is_running and self._stream_thread and self._stream_thread.is_alive():
                # Already running, update rate
                self._rate_per_sec = max(1.0, min(100.0, float(rate_per_sec)))
                return True

            self._rate_per_sec = max(1.0, min(100.0, float(rate_per_sec)))
            self._stop_event.clear()
            self._stream_thread = threading.Thread(target=self._stream_worker, daemon=True, name="LiveTaxiStreamer")
            self._stream_thread.start()
            self._is_running = True
            return True

    def stop_background_streaming(self) -> bool:
        """Signals the background streaming thread to stop."""
        with self._lock:
            if not self._is_running:
                return False
            self._stop_event.set()
            if self._stream_thread:
                self._stream_thread.join(timeout=2.0)
            self._is_running = False
            return True

    def is_streaming_active(self) -> bool:
        """Checks if background streaming thread is actively running."""
        with self._lock:
            active = self._is_running and (self._stream_thread is not None and self._stream_thread.is_alive())
            if not active:
                self._is_running = False
            return active

    def get_rate(self) -> float:
        return self._rate_per_sec


# Global Singleton Instance for shared in-process access
_GLOBAL_STREAM_ENGINE: Optional[LiveStreamEngine] = None
_ENGINE_LOCK = threading.Lock()


def get_stream_engine(db_target: Optional[str | Path] = None) -> LiveStreamEngine:
    """Returns or initializes the process-wide LiveStreamEngine singleton."""
    global _GLOBAL_STREAM_ENGINE
    with _ENGINE_LOCK:
        if _GLOBAL_STREAM_ENGINE is None:
            _GLOBAL_STREAM_ENGINE = LiveStreamEngine(db_target=db_target)
        return _GLOBAL_STREAM_ENGINE
