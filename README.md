# 🚕 Urban Mobility & Surge Pricing Analytics

An end-to-end Big Data analytics pipeline that analyzes millions of NYC taxi rides to uncover traffic congestion patterns, identify lucrative pickup hotspots by time of day, and simulate real-time surge pricing rules.

---

## 🏗️ Architecture

```mermaid
graph LR
    A["📥 NYC TLC Parquet Files\n(Raw Data Lake)"] --> B["⚡ Apache Spark (PySpark)\nETL & Feature Engineering"]
    B --> C["📈 Surge Pricing Engine\nPercentile Demand Model"]
    C --> D["🛢️ SQLite / PostgreSQL\nAggregated Serving Layer"]
    D --> E["📊 Streamlit Web UI\nInteractive Analytics Dashboard"]
    F["📡 Live Stream Producer\n(scripts/05_stream_producer.py)"] -->|Real-Time Telemetry| D
    D -->|@st.fragment Auto-Refresh| E
```

---

## 📁 Project Structure

```
BDA_project/
├── .gitignore                     # Git ignore rules for venv, parquet, and DB files
├── requirements.txt               # Pinned Python package dependencies
├── README.md                      # Project documentation and execution instructions
├── data/
│   ├── raw/                       # NYC TLC Yellow Taxi Parquet files
│   ├── processed/                 # Spark output CSVs (aggregated summaries)
│   └── lookup/
│       └── taxi_zone_lookup.csv   # NYC Taxi zone metadata
├── scripts/
│   ├── 01_ingest_validate.py      # Schema check and raw data validation
│   ├── 02_spark_process.py        # Core PySpark cleaning, features & aggregations
│   ├── 03_load_to_db.py           # Loads processed CSV summaries into SQLite/Postgres
│   ├── 04_surge_pricing.py        # Dynamic surge multiplier simulation engine
│   └── 05_stream_producer.py      # Real-time streaming telemetry producer
├── src/
│   ├── streaming.py               # Real-time live streaming engine & background threader
│   ├── queries.py                 # Analytical & streaming queries for dashboard
│   ├── surge.py                   # Percentile-based surge multiplier calculator
│   └── ...
├── dashboard/
│   └── app.py                     # Streamlit dashboard with Real-Time Streaming Tab
└── db/
    ├── schema.sql                 # Serving layer database schema (including live_trips)
    └── mobility.db                # SQLite serving database (WAL mode)
```

---

## 🚀 Quickstart Guide

### 1. Activate Virtual Environment
```powershell
.\.venv\Scripts\activate
```

### 2. Verify Raw Files
Place your Yellow Taxi `.parquet` files in `data/raw/` and `taxi_zone_lookup.csv` in `data/lookup/`.

### 3. Pipeline Execution Sequence
Run the batch pipeline:

```powershell
# Step 1: Validate data and inspect schemas
python scripts/01_ingest_validate.py

# Step 2: Run Big Data PySpark ETL (cleans and aggregates millions of rides)
python scripts/02_spark_process.py

# Step 3: Run the surge pricing simulation model
python scripts/04_surge_pricing.py

# Step 4: Populate the serving database
python scripts/03_load_to_db.py

# Step 5: Launch the Streamlit dashboard
streamlit run dashboard/app.py
```

---

## 🔴 Real-Time Live Streaming Demonstration

You can demonstrate live streaming in **two flexible ways**:

### Method A: Directly inside the Streamlit Web UI
1. Launch `streamlit run dashboard/app.py`
2. Navigate to tab **"🔴 Real-Time Streaming"**
3. Click **"▶ Start Stream"** to initiate background ride generation, or click **"⚡ Burst (50 Rides)"** for instant injection.
4. Watch the telemetry feed, velocity chart, and surge map update dynamically every 2 seconds without page refreshes!

### Method B: Standalone Terminal Stream Producer
Run the dedicated CLI producer in a separate PowerShell window:
```powershell
python scripts/05_stream_producer.py --rate 15 --batch-size 5
```
Watch real-time ride arrivals streamed into `live_trips` while the Streamlit dashboard visualizes incoming traffic and live surge tier escalation!

