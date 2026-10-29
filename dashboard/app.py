"""
dashboard/app.py
----------------
Interactive Big Data Analytics Dashboard for NYC Urban Mobility & Surge Pricing.
Built with Streamlit, Plotly, Folium, and SQLite/PostgreSQL.
"""

import sys
from pathlib import Path

# Add project root to sys.path so modules in src/ can be cleanly imported
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import folium
from streamlit_folium import st_folium

from src.config import DB_FILE
from src.db import get_db_engine
from src.streaming import get_stream_engine
from src.queries import (
    DAYS_OF_WEEK,
    get_kpi_metrics,
    get_hourly_heatmap_data,
    get_top_hotspots,
    get_hourly_speed_trend,
    get_daily_trends_data,
    get_surge_pricing_distribution,
    get_distinct_filter_options,
    simulate_zone_surge,
    get_live_stream_stats,
    get_live_recent_feed,
    get_live_active_hotspots,
    get_live_throughput_history,
    get_live_surge_alerts,
    get_demand_forecast,
    get_demand_spike_alerts,
)

# Page Configuration
st.set_page_config(
    page_title="NYC Mobility Intelligence",
    page_icon="NY",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for Sleek Modern Styling
CUSTOM_CSS = """
<style>
    /* Global Font & Header Aesthetics */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700;800&display=swap');
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }

    /* Metric Card Styling */
    .metric-card {
        background: linear-gradient(135deg, rgba(30, 41, 59, 0.7) 0%, rgba(15, 23, 42, 0.8) 100%);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 12px;
        padding: 18px 22px;
        box-shadow: 0 4px 14px 0 rgba(0, 0, 0, 0.25);
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    .metric-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px 0 rgba(0, 0, 0, 0.35);
        border-color: rgba(255, 255, 255, 0.18);
    }
    .metric-label {
        font-size: 0.85rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: #94A3B8;
        margin-bottom: 6px;
    }
    .metric-value {
        font-size: 1.85rem;
        font-weight: 800;
        color: #F8FAFC;
        margin-bottom: 4px;
    }
    .metric-sub {
        font-size: 0.80rem;
        color: #38BDF8;
        font-weight: 500;
    }

    /* Multiplier Badges */
    .surge-badge {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 20px;
        font-weight: 700;
        font-size: 0.85rem;
    }
    .badge-base { background-color: #10B981; color: #FFFFFF; }
    .badge-mid  { background-color: #F59E0B; color: #FFFFFF; }
    .badge-high { background-color: #EF4444; color: #FFFFFF; }
    .badge-max  { background-color: #8B5CF6; color: #FFFFFF; }

    /* Streaming Status & Alert Badges */
    .badge-live-pulse {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        padding: 6px 16px;
        border-radius: 20px;
        font-weight: 700;
        font-size: 0.88rem;
        background: rgba(239, 68, 68, 0.15);
        color: #F87171;
        border: 1px solid rgba(239, 68, 68, 0.6);
    }
    .badge-idle-status {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        padding: 6px 16px;
        border-radius: 20px;
        font-weight: 700;
        font-size: 0.88rem;
        background: rgba(100, 116, 139, 0.15);
        color: #94A3B8;
        border: 1px solid rgba(100, 116, 139, 0.4);
    }
    .live-dot {
        width: 10px;
        height: 10px;
        border-radius: 50%;
        background-color: #EF4444;
        box-shadow: 0 0 10px #EF4444;
        animation: livePulse 1.2s infinite;
    }
    @keyframes livePulse {
        0% { transform: scale(0.85); opacity: 0.6; }
        50% { transform: scale(1.35); opacity: 1.0; }
        100% { transform: scale(0.85); opacity: 0.6; }
    }
    .surge-alert-banner {
        background: linear-gradient(90deg, rgba(239, 68, 68, 0.25) 0%, rgba(139, 92, 246, 0.25) 100%);
        border: 1px solid rgba(239, 68, 68, 0.6);
        border-radius: 10px;
        padding: 12px 18px;
        margin-bottom: 16px;
        color: #F8FAFC;
        font-size: 0.95rem;
    }
    .professional-header {
        padding: 8px 0 18px 0;
        border-bottom: 1px solid rgba(148, 163, 184, 0.25);
        margin-bottom: 22px;
    }
    .professional-header h1 { margin: 0; font-size: 2rem; color: #F8FAFC; }
    .professional-header p { margin: 6px 0 0; color: #94A3B8; }
    .insight-card {
        background: rgba(15, 23, 42, 0.65);
        border-left: 4px solid #38BDF8;
        border-radius: 8px;
        padding: 14px 16px;
        margin-bottom: 10px;
    }
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)



@st.cache_resource
def get_cached_engine():
    """Initializes and caches the database connection pool."""
    return get_db_engine(DB_FILE)


# Coordinate mapping for prominent NYC Zones for Folium mapping
ZONE_COORDINATES = {
    132: (40.6413, -73.7781, "JFK Airport"),
    138: (40.7769, -73.8740, "LaGuardia Airport"),
    237: (40.7736, -73.9566, "Upper East Side South"),
    236: (40.7816, -73.9516, "Upper East Side North"),
    161: (40.7589, -73.9851, "Midtown Center"),
    162: (40.7554, -73.9740, "Midtown East"),
    186: (40.7505, -73.9934, "Penn Station"),
    230: (40.7580, -73.9855, "Times Sq/Theatre District"),
    142: (40.7710, -73.9818, "Lincoln Square East"),
    239: (40.7880, -73.9760, "Upper West Side South"),
    238: (40.7960, -73.9680, "Upper West Side North"),
    170: (40.7484, -73.9772, "Murray Hill"),
    107: (40.7350, -73.9840, "Gramercy"),
    79:  (40.7280, -73.9880, "East Village"),
    48:  (40.7630, -73.9910, "Clinton East"),
    68:  (40.7480, -74.0010, "Chelsea"),
    90:  (40.7400, -73.9940, "Flatiron"),
    100: (40.7520, -73.9880, "Garment District"),
    234: (40.7380, -73.9890, "Union Square"),
    114: (40.7300, -73.9980, "Greenwich Village South"),
}


def render_kpi_cards(kpis: dict):
    """Renders 4 modern KPI metric cards across the top header."""
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Total Rides Analyzed</div>
            <div class="metric-value">{kpis['total_trips']:,}</div>
            <div class="metric-sub">Verified Big Data Volume</div>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Total Gross Revenue</div>
            <div class="metric-value">${kpis['total_revenue']:,.2f}</div>
            <div class="metric-sub">Fare + Tips + Surcharges</div>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Average Trip Fare</div>
            <div class="metric-value">${kpis['avg_fare']:.2f}</div>
            <div class="metric-sub">Avg Distance: {kpis['avg_distance']:.1f} miles</div>
        </div>
        """, unsafe_allow_html=True)

    with col4:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Peak Mobility Window</div>
            <div class="metric-value">{kpis['peak_hour']:02d}:00 HRS</div>
            <div class="metric-sub">{kpis['peak_volume']:,} peak trips | {kpis['avg_speed']:.1f} mph</div>
        </div>
        """, unsafe_allow_html=True)


def render_executive_intelligence(engine, borough: str):
    """Render forecast, operating outlook, and historical demand-spike intelligence."""
    forecast = get_demand_forecast(engine, borough=borough, horizon=6)
    alerts = get_demand_spike_alerts(engine, borough=borough, limit=4)

    st.markdown("### Executive outlook")
    if not forecast.empty:
        forecast_method = (
            str(forecast.iloc[0]["forecast_method"])
            if "forecast_method" in forecast.columns
            else forecast.attrs.get("method", "Demand forecast")
        )
        next_hour = forecast.iloc[0]
        peak = forecast.loc[forecast["predicted_trips"].idxmax()]
        c1, c2, c3 = st.columns(3)
        c1.metric("Next-hour demand", f"{int(next_hour['predicted_trips']):,} rides", help=forecast_method)
        c2.metric("Six-hour peak", f"{int(peak['predicted_trips']):,} rides", peak["forecast_time"].strftime("%A %H:00"))
        c3.metric("Detected demand spikes", f"{len(alerts)} priority zones", help="At least 35% above the zone baseline")

        fig = go.Figure()
        fig.add_trace(go.Scatter(x=forecast["forecast_time"], y=forecast["upper_bound"], line=dict(width=0), hoverinfo="skip", showlegend=False))
        fig.add_trace(go.Scatter(x=forecast["forecast_time"], y=forecast["lower_bound"], line=dict(width=0), fill="tonexty", fillcolor="rgba(56,189,248,0.16)", name="Expected range"))
        fig.add_trace(go.Scatter(x=forecast["forecast_time"], y=forecast["predicted_trips"], mode="lines+markers", name="Forecast demand", line=dict(color="#38BDF8", width=3), marker=dict(size=8)))
        fig.update_layout(title="Next six hours: demand forecast", xaxis_title="New York time", yaxis_title="Expected rides", height=330, margin=dict(l=20, r=20, t=50, b=20), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", legend=dict(orientation="h", y=1.12))
        st.plotly_chart(fig, width="stretch")
        st.caption(f"Forecast method: {forecast_method}, with an uncertainty band. This is an operational planning estimate, not a live demand guarantee.")

    st.markdown("#### Priority demand-spike alerts")
    if alerts.empty:
        st.success("No historical zone-hour observations exceed the alert threshold in this scope.")
    else:
        cols = st.columns(min(2, len(alerts)))
        for idx, row in alerts.iterrows():
            with cols[idx % len(cols)]:
                st.markdown(
                    f'<div class="insight-card"><b>{row["severity"]}: {row["zone_name"]}</b><br>'
                    f'<span style="color:#94A3B8">{DAYS_OF_WEEK[int(row["day_of_week"])]} at {int(row["pickup_hour"]):02d}:00</span><br>'
                    f'Demand is <b>{row["increase_pct"]:.0f}% above</b> its zone baseline '
                    f'({int(row["trip_count"]):,} vs. {int(row["baseline_trips"]):,} rides).</div>',
                    unsafe_allow_html=True,
                )

def build_folium_map(hotspots_df: pd.DataFrame):
    """Constructs an interactive Folium map with NYC hotspots."""
    nyc_center = [40.730610, -73.935242]
    m = folium.Map(location=nyc_center, zoom_start=11, tiles="OpenStreetMap")

    max_trips = hotspots_df["total_trips"].max() if not hotspots_df.empty else 1

    for _, row in hotspots_df.iterrows():
        puid = int(row["PULocationID"])
        if puid in ZONE_COORDINATES:
            lat, lon, label = ZONE_COORDINATES[puid]
            trips = row["total_trips"]
            fare = row["avg_fare"]
            borough = row["borough"]
            
            # Radius proportional to trip density
            radius = 6 + (trips / max_trips) * 20

            popup_html = f"""
            <div style="font-family: Arial; font-size: 13px; min-width: 160px;">
                <b style="color: #0284C7; font-size: 14px;">{label}</b><br>
                <b>Borough:</b> {borough}<br>
                <b>Total Trips:</b> {trips:,}<br>
                <b>Average Fare:</b> ${fare:.2f}<br>
                <b>Total Revenue:</b> ${row['total_revenue']:,.2f}
            </div>
            """

            color = "#EF4444" if trips > max_trips * 0.7 else ("#F59E0B" if trips > max_trips * 0.3 else "#38BDF8")

            folium.CircleMarker(
                location=[lat, lon],
                radius=radius,
                color=color,
                fill=True,
                fill_color=color,
                fill_opacity=0.65,
                weight=2,
                tooltip=f"{label} ({trips:,} trips)",
                popup=folium.Popup(popup_html, max_width=300)
            ).add_to(m)

    return m


def build_live_folium_map(hotspots_df: pd.DataFrame):
    """Constructs a real-time Folium map color-coded by active surge tier."""
    nyc_center = [40.730610, -73.935242]
    m = folium.Map(location=nyc_center, zoom_start=11, tiles="OpenStreetMap")

    if hotspots_df.empty:
        return m

    max_trips = hotspots_df["live_trips_count"].max() if not hotspots_df.empty else 1

    for _, row in hotspots_df.iterrows():
        puid = int(row["PULocationID"])
        if puid in ZONE_COORDINATES:
            lat, lon, label = ZONE_COORDINATES[puid]
            trips = int(row["live_trips_count"])
            fare = float(row["avg_fare"])
            borough = str(row["borough"])
            surge = float(row.get("current_surge", 1.0))
            
            radius = 8 + (trips / max_trips) * 20

            if surge >= 2.5:
                color = "#8B5CF6"  # Purple
                tier_text = "2.5x Peak Surge"
            elif surge >= 1.8:
                color = "#EF4444"  # Red
                tier_text = "1.8x High Surge"
            elif surge >= 1.3:
                color = "#F59E0B"  # Amber
                tier_text = "1.3x Moderate Surge"
            else:
                color = "#10B981"  # Emerald
                tier_text = "1.0x Normal"

            popup_html = f"""
            <div style="font-family: Arial; font-size: 13px; min-width: 170px;">
                <b style="color: {color}; font-size: 14px;">{label}</b><br>
                <b>Borough:</b> {borough}<br>
                <b>Live Stream Rides:</b> {trips}<br>
                <b>Active Surge:</b> <b style="color:{color};">{surge:.1f}x ({tier_text})</b><br>
                <b>Simulated Avg Fare:</b> ${fare:.2f}
            </div>
            """

            folium.CircleMarker(
                location=[lat, lon],
                radius=radius,
                color=color,
                fill=True,
                fill_color=color,
                fill_opacity=0.75,
                weight=3,
                tooltip=f"{label} | {surge:.1f}x Surge ({trips} rides)",
                popup=folium.Popup(popup_html, max_width=300)
            ).add_to(m)

    return m


def render_live_streaming_section(engine):
    """Renders the Real-Time Streaming and Surge Monitoring interface."""
    streamer = get_stream_engine()
    if "live_stream_active" not in st.session_state:
        st.session_state.live_stream_active = False

    st.markdown("### Live operations and dynamic pricing")
    st.markdown("Observe simulated taxi event ingestion, dynamic pricing recommendations and arrival velocity.")

    # Control Bar
    ctrl_col1, ctrl_col2, ctrl_col3, ctrl_col4, ctrl_col5 = st.columns([2.2, 1.2, 1.2, 1.4, 1.2])

    with ctrl_col1:
        if st.session_state.live_stream_active:
            st.markdown('<div class="badge-live-pulse"><div class="live-dot"></div> <b>STREAMING ACTIVE</b> (15 rides/s)</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="badge-idle-status"><b>STREAMING IDLE / PAUSED</b></div>', unsafe_allow_html=True)

    with ctrl_col2:
        if st.button("Start stream", width="stretch", help="Starts background live taxi stream"):
            st.session_state.live_stream_active = True
            st.rerun()

    with ctrl_col3:
        if st.button("Pause", width="stretch", help="Pauses background stream thread"):
            st.session_state.live_stream_active = False
            st.rerun()

    with ctrl_col4:
        if st.button("Inject 50 rides", width="stretch", help="Instantly injects 50 simulated taxi rides"):
            streamer.inject_trips(count=50)
            st.rerun()

    with ctrl_col5:
        if st.button("Clear buffer", width="stretch", help="Flushes live streaming database buffer"):
            streamer.clear_live_buffer()
            st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)

    # Isolated auto-refreshing fragment for real-time visualization
    @st.fragment(run_every="2s")
    def render_live_telemetry_fragment():
        if st.session_state.get("live_stream_active", False):
            streamer.inject_trips(count=30)
        stats = get_live_stream_stats(engine)
        total_trips = stats["total_streamed"]

        # Alert Banners
        alerts = get_live_surge_alerts(engine)
        for alert in alerts:
            st.markdown(
                f"""
                <div class="surge-alert-banner">
                    <b>LIVE PRICING ALERT:</b> <b>{alert['zone_name']}</b> ({alert['borough']}) is experiencing 
                    <b>{alert['surge_multiplier']:.1f}x SURGE</b> with <b>{alert['trips_in_surge']}</b> active dispatches!
                </div>
                """,
                unsafe_allow_html=True
            )

        # 4 Metric Cards
        col_m1, col_m2, col_m3, col_m4 = st.columns(4)

        with col_m1:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">Ingestion Velocity</div>
                <div class="metric-value">{stats['throughput_rps']:.1f} <span style="font-size: 1rem; color: #94A3B8;">rps</span></div>
                <div class="metric-sub">Real-Time Ingestion Throughput</div>
            </div>
            """, unsafe_allow_html=True)

        with col_m2:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">Total Streamed Rides</div>
                <div class="metric-value">{total_trips:,}</div>
                <div class="metric-sub">{stats['active_zones']} Active Pickup Zones</div>
            </div>
            """, unsafe_allow_html=True)

        with col_m3:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">Live Gross Revenue</div>
                <div class="metric-value">${stats['total_revenue']:,.2f}</div>
                <div class="metric-sub">Avg Surged Fare: ${stats['avg_fare']:.2f}</div>
            </div>
            """, unsafe_allow_html=True)

        with col_m4:
            surge_color = "#8B5CF6" if stats['max_multiplier'] >= 2.5 else ("#EF4444" if stats['max_multiplier'] >= 1.8 else "#10B981")
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">Peak Live Multiplier</div>
                <div class="metric-value" style="color: {surge_color};">{stats['max_multiplier']:.1f}x</div>
                <div class="metric-sub">{stats['top_zone_name'][:20]}</div>
            </div>
            """, unsafe_allow_html=True)

        if total_trips == 0:
            st.info("The live stream buffer is empty. Select **Start stream** or **Inject 50 rides**, or run `python scripts/05_stream_producer.py` in a terminal.")
            return

        st.markdown("<br>", unsafe_allow_html=True)

        # Real-time Chart & Hotspots Columns
        chart_col1, chart_col2 = st.columns([1, 1])

        with chart_col1:
            st.markdown("#### Real-time ride arrival velocity")
            hist_df = get_live_throughput_history(engine, limit=20)
            if not hist_df.empty:
                fig_stream = go.Figure()
                fig_stream.add_trace(go.Scatter(
                    x=hist_df["time_sec"],
                    y=hist_df["rides_count"],
                    mode="lines+markers",
                    name="Arrivals",
                    line=dict(color="#EF4444", width=3),
                    marker=dict(size=8, color="#F87171"),
                    fill="tozeroy",
                    fillcolor="rgba(239, 68, 68, 0.15)"
                ))
                fig_stream.update_layout(
                    title="Live Event Ingestion Pulse",
                    xaxis_title="Timestamp",
                    yaxis_title="Trips Ingested",
                    height=340,
                    margin=dict(l=20, r=20, t=35, b=20),
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)"
                )
                st.plotly_chart(fig_stream, width="stretch")
            else:
                st.caption("Awaiting arrival time series...")

        with chart_col2:
            st.markdown("#### Active hotspots and pricing multiplier")
            hotspots_df = get_live_active_hotspots(engine, limit=8)
            if not hotspots_df.empty:
                # Color map based on current surge
                color_map = {
                    1.0: "#10B981",
                    1.3: "#F59E0B",
                    1.8: "#EF4444",
                    2.5: "#8B5CF6"
                }
                bar_colors = [color_map.get(s, "#38BDF8") for s in hotspots_df["current_surge"]]

                fig_hotspots = go.Figure(go.Bar(
                    x=hotspots_df["live_trips_count"],
                    y=hotspots_df["zone_name"],
                    orientation="h",
                    marker=dict(color=bar_colors),
                    text=[f"{s:.1f}x Surge" for s in hotspots_df["current_surge"]],
                    textposition="auto"
                ))
                fig_hotspots.update_layout(
                    title="Live Demand Volume by Zone",
                    xaxis_title="Streamed Rides",
                    yaxis=dict(autorange="reversed"),
                    height=340,
                    margin=dict(l=20, r=20, t=35, b=20),
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)"
                )
                st.plotly_chart(fig_hotspots, width="stretch")
            else:
                st.caption("Awaiting zone activity...")

        st.markdown("<br>", unsafe_allow_html=True)

        # Geospatial Live Map & Dispatches Feed
        map_col, feed_col = st.columns([1, 1])

        with map_col:
            st.markdown("#### Live NYC pricing map")
            live_map = build_live_folium_map(hotspots_df)
            st_folium(live_map, width=580, height=400, returned_objects=[])

        with feed_col:
            st.markdown("#### Recent dispatch feed")
            feed_df = get_live_recent_feed(engine, limit=12)
            if not feed_df.empty:
                display_feed = feed_df.rename(columns={
                    "event_time": "Time",
                    "zone_name": "Pickup Zone",
                    "borough": "Borough",
                    "trip_distance": "Dist (mi)",
                    "fare_amount": "Base ($)",
                    "surge_multiplier": "Surge",
                    "simulated_fare": "Final ($)",
                    "speed_mph": "Speed (mph)"
                })
                st.dataframe(
                    display_feed,
                    width="stretch",
                    hide_index=True,
                    height=390
                )
            else:
                st.caption("Awaiting telemetry records...")

    render_live_telemetry_fragment()


def main():
    engine = get_cached_engine()

    # Sidebar Controls
    with st.sidebar:
        st.title("NYC Mobility Intelligence")
        st.markdown("**Demand, congestion and pricing analytics**")
        st.markdown("---")

        try:
            borough_list, zone_map = get_distinct_filter_options(engine)
        except Exception as e:
            st.error(f"Failed to connect to database: {e}")
            st.info("Please verify `mobility.db` exists in `db/`.")
            return

        selected_borough = st.selectbox(
            "Filter by Borough",
            options=borough_list,
            index=0,
            help="Select a specific NYC borough to filter downstream metrics and heatmap"
        )

        if st.button("Refresh data cache", width="stretch"):
            st.cache_data.clear()
            st.rerun()

    # Header Title
    st.markdown(
        '<div class="professional-header"><h1>NYC Mobility Intelligence</h1>'
        '<p>Demand forecasting, congestion monitoring and explainable pricing decisions</p></div>',
        unsafe_allow_html=True,
    )
    st.caption(f"Analysis scope: **{selected_borough}**")

    # Fetch Top-level KPIs
    kpis = get_kpi_metrics(engine, borough=selected_borough)
    render_kpi_cards(kpis)

    st.markdown("<br>", unsafe_allow_html=True)

    # Main Tabs
    tab0, tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "Executive Intelligence",
        "Demand and Congestion",
        "Pickup Hotspots",
        "Explainable Pricing",
        "Daily Trends",
        "Live Operations"
    ])

    with tab0:
        render_executive_intelligence(engine, selected_borough)


    # TAB 1: DEMAND & CONGESTION
    with tab1:
        st.markdown("### Weekly demand distribution")
        heatmap_df = get_hourly_heatmap_data(engine, borough=selected_borough)

        if not heatmap_df.empty:
            fig_heatmap = px.imshow(
                heatmap_df,
                labels=dict(x="Hour of Day (0–23)", y="Day of Week", color="Ride Volume"),
                x=list(heatmap_df.columns),
                y=list(heatmap_df.index),
                color_continuous_scale="Plasma",
                aspect="auto"
            )
            fig_heatmap.update_layout(
                margin=dict(l=20, r=20, t=30, b=20),
                height=380,
                xaxis=dict(tickmode="linear", tick0=0, dtick=1),
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)"
            )
            st.plotly_chart(fig_heatmap, width="stretch")
        else:
            st.info("No demand data available for the selected borough.")

        st.markdown("### Traffic velocity and congestion profile")
        speed_df = get_hourly_speed_trend(engine, borough=selected_borough)
        if not speed_df.empty:
            fig_speed = go.Figure()
            fig_speed.add_trace(go.Scatter(
                x=speed_df["pickup_hour"],
                y=speed_df["avg_speed_mph"],
                mode="lines+markers",
                name="Average Speed (mph)",
                line=dict(color="#38BDF8", width=3),
                marker=dict(size=7, color="#0284C7")
            ))
            fig_speed.update_layout(
                title="Hour-by-Hour Traffic Speed (mph)",
                xaxis_title="Hour of Day",
                yaxis_title="Speed (mph)",
                margin=dict(l=20, r=20, t=40, b=20),
                height=340,
                xaxis=dict(tickmode="linear", tick0=0, dtick=1),
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)"
            )
            st.plotly_chart(fig_speed, width="stretch")

    # TAB 2: PICKUP HOTSPOTS & GEOSPATIAL MAP
    with tab2:
        col_chart, col_map = st.columns([1, 1])

        hotspots_df = get_top_hotspots(engine, borough=selected_borough, limit=15)

        with col_chart:
            st.markdown("### Top 15 pickup hotspots")
            if not hotspots_df.empty:
                fig_hotspots = px.bar(
                    hotspots_df.sort_values(by="total_trips", ascending=True),
                    x="total_trips",
                    y="zone_name",
                    orientation="h",
                    color="avg_fare",
                    color_continuous_scale="Viridis",
                    labels={"total_trips": "Total Rides", "zone_name": "NYC Taxi Zone", "avg_fare": "Avg Fare ($)"},
                    title="Ranked by Total Ride Volume"
                )
                fig_hotspots.update_layout(
                    height=520,
                    margin=dict(l=10, r=10, t=40, b=10),
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)"
                )
                st.plotly_chart(fig_hotspots, width="stretch")
            else:
                st.info("No zone data found.")

        with col_map:
            st.markdown("### NYC geospatial demand map")
            m = build_folium_map(hotspots_df)
            st_folium(m, width=620, height=520, returned_objects=[])

    # TAB 3: SURGE PRICING SIMULATOR
    with tab3:
        st.markdown("### Explainable pricing decision workbench")
        st.markdown("Inspect the demand evidence, percentile thresholds and fare impact behind each recommendation.")

        col_sim_left, col_sim_right = st.columns([1, 2])

        with col_sim_left:
            st.markdown("#### Decision controls")
            
            # Select Zone
            default_zone = "JFK Airport" if "JFK Airport" in zone_map else list(zone_map.keys())[0]
            sim_zone_name = st.selectbox("Select Pickup Zone", options=list(zone_map.keys()), index=list(zone_map.keys()).index(default_zone))
            sim_zone_id = zone_map[sim_zone_name]

            # Select Day
            sim_day = st.selectbox("Select Day of Week", options=list(range(7)), format_func=lambda d: DAYS_OF_WEEK[d], index=0)

            # Select Hour
            sim_hour = st.slider("Select Pickup Hour", min_value=0, max_value=23, value=18, format="%d:00")

            # Execute Simulation Lookup
            sim_record = simulate_zone_surge(engine, pulocation_id=sim_zone_id, day_of_week=sim_day, pickup_hour=sim_hour)

            if sim_record:
                multiplier = sim_record["surge_multiplier"]
                base_fare = sim_record["avg_fare"]
                sim_fare = sim_record["simulated_fare"]
                trips = sim_record["trip_count"]

                if multiplier >= 2.5:
                    badge_class = "badge-max"
                elif multiplier >= 1.8:
                    badge_class = "badge-high"
                elif multiplier >= 1.3:
                    badge_class = "badge-mid"
                else:
                    badge_class = "badge-base"

                st.markdown(f"""
                <div class="metric-card" style="margin-top: 15px;">
                    <div class="metric-label">Zone Status & Multiplier</div>
                    <div style="margin: 8px 0;">
                        <span class="surge-badge {badge_class}">{multiplier:.1f}x MULTIPLIER</span>
                    </div>
                    <div class="metric-sub">Observed Demand: <b>{trips:,} rides</b></div>
                    <hr style="border-color: rgba(255,255,255,0.1); margin: 12px 0;">
                    <div style="font-size: 0.9rem; color: #94A3B8;">Base Average Fare: <b style="color: #F8FAFC;">${base_fare:.2f}</b></div>
                    <div style="font-size: 1.25rem; font-weight: 700; color: #10B981; margin-top: 4px;">
                        Simulated Fare: ${sim_fare:.2f}
                    </div>
                </div>
                """, unsafe_allow_html=True)

                percentile = sim_record.get("demand_percentile", 0)
                if multiplier >= 2.5:
                    tier, rationale = "Critical demand", f"Demand meets or exceeds the zone's 90th-percentile threshold ({sim_record.get('p90', 0):,.0f} rides)."
                elif multiplier >= 1.8:
                    tier, rationale = "High demand", f"Demand meets or exceeds the zone's 75th-percentile threshold ({sim_record.get('p75', 0):,.0f} rides)."
                elif multiplier >= 1.3:
                    tier, rationale = "Elevated demand", f"Demand meets or exceeds the zone's median threshold ({sim_record.get('p50', 0):,.0f} rides)."
                else:
                    tier, rationale = "Normal demand", f"Demand is below the zone's median threshold ({sim_record.get('p50', 0):,.0f} rides)."
                st.markdown("#### Decision explanation")
                st.info(f"**{tier}.** {rationale} This observation ranks at the {percentile:.0f}th percentile for the selected zone.")
                st.markdown(
                    f"**Fare impact:** \\${base_fare:.2f} base fare + \\${sim_record.get('fare_uplift', 0):.2f} adjustment = **\\${sim_fare:.2f} recommended fare**."
                )
            else:
                st.warning(f"No trip data recorded for {sim_zone_name} on {DAYS_OF_WEEK[sim_day]} at {sim_hour:02d}:00.")

        with col_sim_right:
            st.markdown("#### Pricing tier distribution")
            dist_df = get_surge_pricing_distribution(engine, borough=selected_borough)
            if not dist_df.empty:
                dist_df["multiplier_label"] = dist_df["surge_multiplier"].apply(lambda x: f"{x:.1f}x Tier")

                fig_donut = px.pie(
                    dist_df,
                    names="multiplier_label",
                    values="window_count",
                    hole=0.45,
                    color="multiplier_label",
                    color_discrete_map={
                        "1.0x Tier": "#10B981",
                        "1.3x Tier": "#F59E0B",
                        "1.8x Tier": "#EF4444",
                        "2.5x Tier": "#8B5CF6"
                    },
                    title="Operating Hours by Multiplier Tier"
                )
                fig_donut.update_layout(
                    height=380,
                    margin=dict(l=10, r=10, t=40, b=10),
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)"
                )
                st.plotly_chart(fig_donut, width="stretch")

                st.dataframe(
                    dist_df[["surge_multiplier", "window_count", "avg_base_fare", "avg_simulated_fare", "total_trips_impacted"]].rename(
                        columns={
                            "surge_multiplier": "Multiplier",
                            "window_count": "Active Windows",
                            "avg_base_fare": "Base Fare ($)",
                            "avg_simulated_fare": "Surged Fare ($)",
                            "total_trips_impacted": "Impacted Rides"
                        }
                    ),
                    width="stretch",
                    hide_index=True
                )

    # TAB 4: DAILY TRENDS
    with tab4:
        st.markdown("### Daily ride volume and revenue")
        daily_df = get_daily_trends_data(engine)

        if not daily_df.empty:
            fig_daily = go.Figure()
            fig_daily.add_trace(go.Bar(
                x=daily_df["pickup_date"],
                y=daily_df["trip_count"],
                name="Daily Trips",
                marker_color="#0284C7",
                yaxis="y"
            ))
            fig_daily.add_trace(go.Scatter(
                x=daily_df["pickup_date"],
                y=daily_df["total_revenue"],
                name="Gross Revenue ($)",
                line=dict(color="#10B981", width=3),
                yaxis="y2"
            ))
            fig_daily.update_layout(
                title="Daily Rides vs. Gross Revenue",
                xaxis_title="Date",
                yaxis=dict(title="Ride Count", side="left"),
                yaxis2=dict(title="Revenue ($)", overlaying="y", side="right"),
                height=420,
                legend=dict(x=0.01, y=0.99),
                margin=dict(l=20, r=20, t=40, b=20),
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)"
            )
            st.plotly_chart(fig_daily, width="stretch")
        else:
            st.info("No daily trend data available.")

    # TAB 5: REAL-TIME STREAMING & SURGE ENGINE
    with tab5:
        render_live_streaming_section(engine)


if __name__ == "__main__":

    main()
