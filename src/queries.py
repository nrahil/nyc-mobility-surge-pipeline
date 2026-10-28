"""
src/queries.py
--------------
High-performance analytical queries for the Streamlit dashboard.
All queries use parameterized filtering against SQLite/PostgreSQL serving layers.
"""

from typing import Dict, List, Optional, Tuple, Any
import pandas as pd
import numpy as np
from sqlalchemy import text, Engine

DAYS_OF_WEEK = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def get_kpi_metrics(engine: Engine, borough: Optional[str] = None) -> Dict[str, Any]:
    """
    Computes high-level KPI metrics: Total Rides, Total Revenue, Avg Fare, Avg Speed, Peak Hour.
    """
    params = {}
    where_clause = ""
    if borough and borough != "All Boroughs":
        where_clause = "WHERE borough = :borough"
        params["borough"] = borough

    with engine.connect() as conn:
        # Aggregated stats from zone_fare_stats
        zone_query = f"""
            SELECT 
                COALESCE(SUM(total_trips), 0) AS total_trips,
                COALESCE(SUM(total_revenue), 0) AS total_revenue,
                COALESCE(SUM(avg_fare * total_trips) / NULLIF(SUM(total_trips), 0), 0) AS weighted_avg_fare,
                COALESCE(AVG(avg_distance), 0) AS avg_distance
            FROM zone_fare_stats
            {where_clause}
        """
        zone_res = conn.execute(text(zone_query), params).mappings().fetchone()

        # Speed and peak demand hour from hourly_demand / zone_hourly_heatmap
        if borough and borough != "All Boroughs":
            heatmap_query = """
                SELECT 
                    pickup_hour,
                    SUM(trip_count) AS hour_trips,
                    AVG(avg_speed_mph) AS hour_speed
                FROM zone_hourly_heatmap
                WHERE borough = :borough
                GROUP BY pickup_hour
                ORDER BY hour_trips DESC
            """
            hour_rows = conn.execute(text(heatmap_query), params).mappings().fetchall()
        else:
            hourly_query = """
                SELECT 
                    pickup_hour,
                    SUM(trip_count) AS hour_trips,
                    AVG(avg_speed_mph) AS hour_speed
                FROM hourly_demand
                GROUP BY pickup_hour
                ORDER BY hour_trips DESC
            """
            hour_rows = conn.execute(text(hourly_query)).mappings().fetchall()

    total_trips = int(zone_res["total_trips"]) if zone_res else 0
    total_revenue = float(zone_res["total_revenue"]) if zone_res else 0.0
    avg_fare = float(zone_res["weighted_avg_fare"]) if zone_res else 0.0
    avg_distance = float(zone_res["avg_distance"]) if zone_res else 0.0

    peak_hour = hour_rows[0]["pickup_hour"] if hour_rows else 18
    peak_volume = hour_rows[0]["hour_trips"] if hour_rows else 0
    avg_speed = float(np.mean([r["hour_speed"] for r in hour_rows])) if hour_rows else 15.0

    return {
        "total_trips": total_trips,
        "total_revenue": total_revenue,
        "avg_fare": round(avg_fare, 2),
        "avg_distance": round(avg_distance, 2),
        "avg_speed": round(avg_speed, 1),
        "peak_hour": int(peak_hour),
        "peak_volume": int(peak_volume)
    }


def get_hourly_heatmap_data(engine: Engine, borough: Optional[str] = None) -> pd.DataFrame:
    """
    Returns a pivot table for the 7x24 Demand Heatmap (Day of Week vs Hour).
    """
    params = {}
    if borough and borough != "All Boroughs":
        sql = """
            SELECT day_of_week, pickup_hour, SUM(trip_count) AS trip_count
            FROM zone_hourly_heatmap
            WHERE borough = :borough
            GROUP BY day_of_week, pickup_hour
            ORDER BY day_of_week, pickup_hour
        """
        params["borough"] = borough
    else:
        sql = """
            SELECT day_of_week, pickup_hour, trip_count
            FROM hourly_demand
            ORDER BY day_of_week, pickup_hour
        """

    with engine.connect() as conn:
        df = pd.read_sql_query(text(sql), conn, params=params)

    if df.empty:
        return pd.DataFrame()

    # Pivot into 7 rows x 24 columns (ensuring complete 7x24 grid even for sparse boroughs)
    pivot_df = df.pivot(index="day_of_week", columns="pickup_hour", values="trip_count").fillna(0)
    pivot_df = pivot_df.reindex(index=range(7), columns=range(24), fill_value=0)
    pivot_df.index = DAYS_OF_WEEK
    return pivot_df


def get_top_hotspots(engine: Engine, borough: Optional[str] = None, limit: int = 10) -> pd.DataFrame:
    """
    Returns the ranked list of top pickup hotspots by total trips.
    """
    params = {"limit": limit}
    where_clause = ""
    if borough and borough != "All Boroughs":
        where_clause = "WHERE borough = :borough"
        params["borough"] = borough

    sql = f"""
        SELECT 
            PULocationID,
            zone_name,
            borough,
            total_trips,
            avg_fare,
            avg_distance,
            total_revenue
        FROM zone_fare_stats
        {where_clause}
        ORDER BY total_trips DESC
        LIMIT :limit
    """
    with engine.connect() as conn:
        return pd.read_sql_query(text(sql), conn, params=params)


def get_hourly_speed_trend(engine: Engine, borough: Optional[str] = None) -> pd.DataFrame:
    """
    Returns hour-by-hour average speed and passenger velocity to analyze traffic congestion.
    """
    params = {}
    if borough and borough != "All Boroughs":
        sql = """
            SELECT 
                pickup_hour,
                ROUND(AVG(avg_speed_mph), 2) AS avg_speed_mph,
                SUM(trip_count) AS trip_volume
            FROM zone_hourly_heatmap
            WHERE borough = :borough
            GROUP BY pickup_hour
            ORDER BY pickup_hour
        """
        params["borough"] = borough
    else:
        sql = """
            SELECT 
                pickup_hour,
                ROUND(AVG(avg_speed_mph), 2) AS avg_speed_mph,
                SUM(trip_count) AS trip_volume
            FROM hourly_demand
            GROUP BY pickup_hour
            ORDER BY pickup_hour
        """

    with engine.connect() as conn:
        return pd.read_sql_query(text(sql), conn, params=params)


def get_daily_trends_data(engine: Engine) -> pd.DataFrame:
    """
    Returns date-indexed volume, revenue, and average fare for time-series charts.
    """
    sql = """
        SELECT 
            pickup_date,
            trip_count,
            total_revenue,
            avg_fare,
            avg_distance
        FROM daily_trends
        ORDER BY pickup_date
    """
    with engine.connect() as conn:
        df = pd.read_sql_query(text(sql), conn)
    return df


def get_surge_pricing_distribution(engine: Engine, borough: Optional[str] = None) -> pd.DataFrame:
    """
    Returns breakdown of hours across the 4 surge multipliers (1.0x, 1.3x, 1.8x, 2.5x).
    """
    params = {}
    where_clause = ""
    if borough and borough != "All Boroughs":
        where_clause = "WHERE borough = :borough"
        params["borough"] = borough

    sql = f"""
        SELECT 
            surge_multiplier,
            COUNT(*) AS window_count,
            ROUND(AVG(avg_fare), 2) AS avg_base_fare,
            ROUND(AVG(simulated_fare), 2) AS avg_simulated_fare,
            SUM(trip_count) AS total_trips_impacted
        FROM surge_pricing
        {where_clause}
        GROUP BY surge_multiplier
        ORDER BY surge_multiplier
    """
    with engine.connect() as conn:
        return pd.read_sql_query(text(sql), conn, params=params)


def get_distinct_filter_options(engine: Engine) -> Tuple[List[str], Dict[str, int]]:
    """
    Retrieves available Boroughs and mapping of Zone Name -> PULocationID for dynamic controls.
    """
    with engine.connect() as conn:
        boroughs_res = conn.execute(text("SELECT DISTINCT borough FROM zone_fare_stats WHERE borough != 'Unknown' ORDER BY borough")).fetchall()
        zones_res = conn.execute(text("SELECT zone_name, PULocationID FROM zone_fare_stats WHERE zone_name != 'Unknown' ORDER BY zone_name")).fetchall()

    boroughs = ["All Boroughs"] + [b[0] for b in boroughs_res if b[0]]
    zones = {z[0]: z[1] for z in zones_res if z[0]}
    return boroughs, zones


def simulate_zone_surge(
    engine: Engine,
    pulocation_id: int,
    day_of_week: int,
    pickup_hour: int
) -> Optional[Dict[str, Any]]:
    """
    Pulls specific surge evaluation metrics for a single zone, day, and hour.
    """
    sql = """
        SELECT 
            PULocationID,
            zone_name,
            borough,
            day_of_week,
            pickup_hour,
            trip_count,
            avg_fare,
            surge_multiplier,
            simulated_fare
        FROM surge_pricing
        WHERE PULocationID = :puid AND day_of_week = :dow AND pickup_hour = :hour
        LIMIT 1
    """
    params = {"puid": pulocation_id, "dow": day_of_week, "hour": pickup_hour}
    with engine.connect() as conn:
        row = conn.execute(text(sql), params).mappings().fetchone()
        if row:
            return dict(row)
        return None


# ====================================================================
# Real-Time Live Streaming Queries
# ====================================================================

def get_live_stream_stats(engine: Engine) -> Dict[str, Any]:
    """
    Computes real-time streaming metrics:
    Total events, active rate (trips/sec), gross revenue, average fare,
    average speed, and top surging zone.
    """
    with engine.connect() as conn:
        stats_sql = """
            SELECT 
                COUNT(*) AS total_streamed,
                COALESCE(SUM(simulated_fare), 0.0) AS total_revenue,
                COALESCE(AVG(simulated_fare), 0.0) AS avg_fare,
                COALESCE(AVG(speed_mph), 14.5) AS avg_speed,
                COALESCE(AVG(trip_distance), 0.0) AS avg_distance,
                COUNT(DISTINCT PULocationID) AS active_zones,
                COALESCE(MAX(surge_multiplier), 1.0) AS max_multiplier
            FROM live_trips;
        """
        stats_res = conn.execute(text(stats_sql)).mappings().fetchone()

        # Throughput in last 20 seconds
        rate_sql = """
            SELECT COUNT(*) AS recent_count
            FROM live_trips
            WHERE event_time >= datetime('now', '-20 seconds');
        """
        recent_res = conn.execute(text(rate_sql)).mappings().fetchone()

        # Top surging zone currently
        top_surge_sql = """
            SELECT zone_name, borough, surge_multiplier, COUNT(*) as zone_trips
            FROM live_trips
            WHERE event_time >= datetime('now', '-60 seconds')
            GROUP BY zone_name, borough, surge_multiplier
            ORDER BY surge_multiplier DESC, zone_trips DESC
            LIMIT 1;
        """
        top_surge = conn.execute(text(top_surge_sql)).mappings().fetchone()

    total_streamed = int(stats_res["total_streamed"]) if stats_res else 0
    total_revenue = float(stats_res["total_revenue"]) if stats_res else 0.0
    avg_fare = float(stats_res["avg_fare"]) if stats_res else 0.0
    avg_speed = float(stats_res["avg_speed"]) if stats_res else 14.5
    avg_distance = float(stats_res["avg_distance"]) if stats_res else 0.0
    active_zones = int(stats_res["active_zones"]) if stats_res else 0
    max_multiplier = float(stats_res["max_multiplier"]) if stats_res else 1.0

    recent_trips = int(recent_res["recent_count"]) if recent_res else 0
    # Approximate throughput
    throughput_rps = round(recent_trips / 20.0, 1)

    top_zone_name = top_surge["zone_name"] if top_surge else "Midtown / JFK"
    top_zone_mult = float(top_surge["surge_multiplier"]) if top_surge else 1.0

    return {
        "total_streamed": total_streamed,
        "throughput_rps": throughput_rps,
        "total_revenue": round(total_revenue, 2),
        "avg_fare": round(avg_fare, 2),
        "avg_speed": round(avg_speed, 1),
        "avg_distance": round(avg_distance, 2),
        "active_zones": active_zones,
        "max_multiplier": max_multiplier,
        "top_zone_name": top_zone_name,
        "top_zone_multiplier": top_zone_mult
    }


def get_live_recent_feed(engine: Engine, limit: int = 15) -> pd.DataFrame:
    """
    Returns the most recent streaming rides for the live telemetry log table.
    """
    sql = """
        SELECT 
            event_time,
            zone_name,
            borough,
            trip_distance,
            fare_amount,
            surge_multiplier,
            simulated_fare,
            speed_mph
        FROM live_trips
        ORDER BY id DESC
        LIMIT :limit;
    """
    with engine.connect() as conn:
        df = pd.read_sql_query(text(sql), conn, params={"limit": limit})
    return df


def get_live_active_hotspots(engine: Engine, limit: int = 10) -> pd.DataFrame:
    """
    Returns top active pickup zones in the live buffer with surge tiers and volumes.
    """
    sql = """
        SELECT 
            PULocationID,
            zone_name,
            borough,
            COUNT(*) AS live_trips_count,
            ROUND(AVG(simulated_fare), 2) AS avg_fare,
            ROUND(MAX(surge_multiplier), 1) AS current_surge,
            ROUND(SUM(simulated_fare), 2) AS gross_revenue
        FROM live_trips
        GROUP BY PULocationID, zone_name, borough
        ORDER BY live_trips_count DESC
        LIMIT :limit;
    """
    with engine.connect() as conn:
        df = pd.read_sql_query(text(sql), conn, params={"limit": limit})
    return df


def get_live_throughput_history(engine: Engine, limit: int = 25) -> pd.DataFrame:
    """
    Aggregates ride arrivals across time slices for the real-time velocity chart.
    """
    sql = """
        SELECT 
            strftime('%H:%M:%S', event_time) AS time_sec,
            COUNT(*) AS rides_count,
            ROUND(AVG(simulated_fare), 2) AS avg_fare,
            ROUND(MAX(surge_multiplier), 1) AS max_surge
        FROM live_trips
        GROUP BY time_sec
        ORDER BY event_time DESC
        LIMIT :limit;
    """
    with engine.connect() as conn:
        df = pd.read_sql_query(text(sql), conn, params={"limit": limit})
    
    if not df.empty:
        df = df.iloc[::-1].reset_index(drop=True)
    return df


def get_live_surge_alerts(engine: Engine) -> List[Dict[str, Any]]:
    """
    Identifies zones currently experiencing elevated or severe surge (>= 1.8x).
    """
    sql = """
        SELECT 
            zone_name,
            borough,
            MAX(surge_multiplier) AS surge_multiplier,
            COUNT(*) AS trips_in_surge
        FROM live_trips
        WHERE surge_multiplier >= 1.8
        GROUP BY zone_name, borough
        ORDER BY surge_multiplier DESC, trips_in_surge DESC
        LIMIT 4;
    """
    with engine.connect() as conn:
        rows = conn.execute(text(sql)).mappings().fetchall()
    return [dict(r) for r in rows]

