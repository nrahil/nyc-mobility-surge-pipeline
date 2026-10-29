# NYC Mobility Intelligence

An end-to-end Big Data analytics pipeline that analyzes millions of NYC taxi rides to uncover traffic congestion patterns, identify lucrative pickup hotspots by time of day, and simulate real-time surge pricing rules.

---

## Architecture

```mermaid
graph LR
    A["NYC TLC Parquet Files\nRaw Data Lake"] --> B["Apache Spark\nETL and Feature Engineering"]
    B --> C["Pricing Engine\nPercentile Demand Model"]
    C --> D["SQLite / PostgreSQL\nServing Layer"]
    D --> E["Streamlit\nIntelligence Dashboard"]
    F["Live Stream Producer"] -->|"Real-Time Telemetry"| D
    D -->|"Auto-Refresh Fragment"| E
```

---

## Project structure

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

## Quickstart guide

### 1. Activate Virtual Environment
```powershell
.\.venv\Scripts\activate
```

On Windows, the project automatically uses the Java 17 runtime under `.runtime/java` for PySpark. A separate system-wide Java installation is not required when that folder is present.

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

# Step 5: Train and evaluate the ML demand forecast
python scripts/06_train_demand_model.py

# Step 6: Launch the Streamlit dashboard
streamlit run dashboard/app.py
```

The training script fits a histogram gradient-boosting regressor on dated hourly demand. It uses the final 30 days as a chronological test set, writes the model to `models/demand_forecast.joblib`, and records its comparison with the seasonal baseline in `models/demand_forecast_metrics.json`.

---

## Real-time streaming demonstration

You can demonstrate live streaming in **two flexible ways**:

### Method A: Directly inside the Streamlit Web UI
1. Launch `streamlit run dashboard/app.py`
2. Navigate to **Live Operations**.
3. Select **Start stream** to begin background ride generation, or **Inject 50 rides** for an immediate demonstration.
4. Watch the telemetry feed, velocity chart, and surge map update dynamically every 2 seconds without page refreshes!

### Method B: Standalone Terminal Stream Producer
Run the dedicated CLI producer in a separate PowerShell window:
```powershell
python scripts/05_stream_producer.py --rate 15 --batch-size 5
```
Watch real-time ride arrivals streamed into `live_trips` while the Streamlit dashboard visualizes incoming traffic and live surge tier escalation!

