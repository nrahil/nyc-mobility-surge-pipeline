-- ====================================================================
-- Serving Layer SQL Schema: Urban Mobility & Surge Pricing Analytics
-- Database: SQLite (mobility.db) or PostgreSQL
-- ====================================================================

-- 1. Hourly demand and trip performance across the week (168 rows)
CREATE TABLE IF NOT EXISTS hourly_demand (
    day_of_week         INTEGER,    -- 0=Monday ... 6=Sunday
    pickup_hour         INTEGER,    -- 0 to 23
    trip_count          INTEGER,
    avg_fare            REAL,
    avg_speed_mph       REAL,
    avg_passengers      REAL,
    total_revenue       REAL
);

-- 2. Zone-level fare and volume statistics (~263 zones)
CREATE TABLE IF NOT EXISTS zone_fare_stats (
    PULocationID        INTEGER PRIMARY KEY,
    zone_name           TEXT,
    borough             TEXT,
    service_zone        TEXT,
    total_trips         INTEGER,
    avg_fare            REAL,
    avg_distance        REAL,
    total_revenue       REAL
);

-- 3. High-resolution zone hourly heatmap
CREATE TABLE IF NOT EXISTS zone_hourly_heatmap (
    PULocationID        INTEGER,
    zone_name           TEXT,
    borough             TEXT,
    day_of_week         INTEGER,
    pickup_hour         INTEGER,
    trip_count          INTEGER,
    avg_fare            REAL,
    avg_speed_mph       REAL
);

-- 4. Simulated surge pricing rules
CREATE TABLE IF NOT EXISTS surge_pricing (
    PULocationID        INTEGER,
    zone_name           TEXT,
    borough             TEXT,
    day_of_week         INTEGER,
    pickup_hour         INTEGER,
    trip_count          INTEGER,
    avg_fare            REAL,
    surge_multiplier    REAL,
    simulated_fare      REAL
);

-- 5. Daily macro trends for time series
CREATE TABLE IF NOT EXISTS daily_trends (
    pickup_date         TEXT PRIMARY KEY,
    trip_count          INTEGER,
    total_revenue       REAL,
    avg_fare            REAL,
    avg_distance        REAL
);

-- High-performance indexes for Streamlit dashboard queries
CREATE INDEX IF NOT EXISTS idx_hourly_demand_time ON hourly_demand(day_of_week, pickup_hour);
CREATE INDEX IF NOT EXISTS idx_zone_heatmap_lookup ON zone_hourly_heatmap(PULocationID, day_of_week, pickup_hour);
CREATE INDEX IF NOT EXISTS idx_zone_heatmap_borough ON zone_hourly_heatmap(borough, day_of_week, pickup_hour);
CREATE INDEX IF NOT EXISTS idx_surge_pricing_zone ON surge_pricing(PULocationID, day_of_week, pickup_hour);
CREATE INDEX IF NOT EXISTS idx_surge_pricing_borough ON surge_pricing(borough, day_of_week, pickup_hour);
CREATE INDEX IF NOT EXISTS idx_daily_trends_date ON daily_trends(pickup_date);
