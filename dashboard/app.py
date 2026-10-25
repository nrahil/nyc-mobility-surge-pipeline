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
from streamlit_folium import folium_static

from src.config import DB_FILE
from src.db import get_db_engine
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
)

# Page Configuration
st.set_page_config(
    page_title="NYC Urban Mobility & Surge Pricing",
    page_icon="🚕",
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


def main():
    engine = get_cached_engine()

    # Sidebar Controls
    with st.sidebar:
        st.title("🚕 NYC TLC Pipeline")
        st.markdown("**Urban Mobility & Surge Pricing Analytics**")
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

        st.markdown("---")
        st.markdown("### ⚙️ Pipeline Specifications")
        st.markdown("- **Processing Engine**: Apache Spark 3.5.1")
        st.markdown("- **Storage Layer**: Local Data Lake Parquet")
        st.markdown("- **Serving Database**: SQLite (WAL mode)")
        st.markdown("- **Percentile Tiers**: 50th, 75th, 90th")

        if st.button("🔄 Refresh Data Cache"):
            st.cache_data.clear()
            st.rerun()

    # Header Title
    st.markdown("## 🚕 NYC Urban Mobility & Dynamic Surge Pricing Dashboard")
    st.caption(f"Currently displaying metrics for: **{selected_borough}**")

    # Fetch Top-level KPIs
    kpis = get_kpi_metrics(engine, borough=selected_borough)
    render_kpi_cards(kpis)

    st.markdown("<br>", unsafe_allow_html=True)

    # Main Tabs
    tab1, tab2, tab3, tab4 = st.tabs([
        "📈 Demand & Congestion",
        "📍 Pickup Hotspots & Map",
        "⚡ Surge Pricing Simulator",
        "📅 Macro Daily Trends"
    ])

    # TAB 1: DEMAND & CONGESTION
    with tab1:
        st.markdown("### 🗓️ Weekly Demand Distribution (Hour of Day vs. Day of Week)")
        heatmap_df = get_hourly_heatmap_data(engine, borough=selected_borough)

        if not heatmap_df.empty:
            fig_heatmap = px.imshow(
                heatmap_df,
                labels=dict(x="Hour of Day (0–23)", y="Day of Week", color="Ride Volume"),
                x=list(range(24)),
                y=heatmap_df.index,
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
            st.plotly_chart(fig_heatmap, use_container_width=True)
        else:
            st.info("No demand data available for the selected borough.")

        st.markdown("### 🚗 Traffic Velocity & Congestion Profile")
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
            st.plotly_chart(fig_speed, use_container_width=True)

    # TAB 2: PICKUP HOTSPOTS & GEOSPATIAL MAP
    with tab2:
        col_chart, col_map = st.columns([1, 1])

        hotspots_df = get_top_hotspots(engine, borough=selected_borough, limit=15)

        with col_chart:
            st.markdown("### 🏆 Top 15 Pickup Hotspots")
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
                st.plotly_chart(fig_hotspots, use_container_width=True)
            else:
                st.info("No zone data found.")

        with col_map:
            st.markdown("### 🗺️ NYC Geospatial Demand Map")
            m = build_folium_map(hotspots_df)
            folium_static(m, width=620, height=520)

    # TAB 3: SURGE PRICING SIMULATOR
    with tab3:
        st.markdown("### ⚡ Dynamic Surge Pricing Simulation Workbench")
        st.markdown("Inspect simulated price elasticity and dynamic multiplier tiers per zone, day, and hour.")

        col_sim_left, col_sim_right = st.columns([1, 2])

        with col_sim_left:
            st.markdown("#### 🎛️ Simulation Controls")
            
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
            else:
                st.warning(f"No trip data recorded for {sim_zone_name} on {DAYS_OF_WEEK[sim_day]} at {sim_hour:02d}:00.")

        with col_sim_right:
            st.markdown("#### 📊 Surge Pricing Distribution & Tier Breakdown")
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
                st.plotly_chart(fig_donut, use_container_width=True)

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
                    use_container_width=True,
                    hide_index=True
                )

    # TAB 4: DAILY TRENDS
    with tab4:
        st.markdown("### 📅 Macro Time-Series: Daily Ride Volume & Revenue")
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
            st.plotly_chart(fig_daily, use_container_width=True)
        else:
            st.info("No daily trend data available.")


if __name__ == "__main__":
    main()
