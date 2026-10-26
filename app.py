
import streamlit as st
import pandas as pd
import plotly.express as px
from pathlib import Path


# ---------- PROFESSIONAL LIGHT THEME ----------
st.markdown("""
<style>
.stApp {
    background-color: #f5f7fb;
    color: #1e293b;
}

[data-testid="stHeader"] {
    background-color: #f5f7fb;
}

[data-testid="stSidebar"] {
    background-color: #ffffff;
    border-right: 1px solid #e2e8f0;
}

[data-testid="stMetric"] {
    background-color: #ffffff;
    border: 1px solid #dbe5f1;
    padding: 20px;
    border-radius: 14px;
    box-shadow: 0 2px 8px rgba(15, 23, 42, 0.05);
}

[data-testid="stMetricLabel"] {
    color: #64748b;
}

[data-testid="stMetricValue"] {
    color: #2563eb;
}

h1, h2, h3 {
    color: #0f172a;
}

[data-testid="stPlotlyChart"] {
    background-color: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 14px;
    padding: 10px;
}

.stCaption {
    color: #64748b;
}
</style>
""", unsafe_allow_html=True)

# ---------- PROFESSIONAL THEME ----------
st.markdown("""
<style>
.stApp {
    background-color: #0b1120;
    color: #e5e7eb;
}
[data-testid="stSidebar"] {
    background-color: #111827;
}
[data-testid="stMetric"] {
    background-color: #172033;
    border: 1px solid #29364d;
    padding: 20px;
    border-radius: 14px;
}
[data-testid="stMetricLabel"] {
    color: #a8b5ca;
}
[data-testid="stMetricValue"] {
    color: #60a5fa;
}
h1, h2, h3 {
    color: #f8fafc;
}
.stCaption {
    color: #a8b5ca;
}
div[data-testid="stPlotlyChart"] {
    background-color: #111827;
    border-radius: 14px;
    padding: 10px;
}
</style>
""", unsafe_allow_html=True)

# ---------- LOAD DATA ----------
DATA_FILE = Path("data/processed/chicago_crime_cleaned.csv")

@st.cache_data
def load_data(path):
    data = pd.read_csv(path, low_memory=False)
    data["Date"] = pd.to_datetime(data["Date"], errors="coerce")
    data = data.dropna(subset=["Date"])
    return data

st.sidebar.title("📊 Crime Intelligence")
st.sidebar.caption("Chicago • Data Analytics")
st.sidebar.divider()

if not DATA_FILE.exists():
    st.error(f"Dataset not found: {DATA_FILE}")
    st.stop()

df = load_data(str(DATA_FILE))

# ---------- HEADER ----------
st.title("Chicago Crime Intelligence")
st.markdown(
    "Explore reported incidents, crime patterns, and recorded arrest outcomes."
)
st.caption("Dataset: Chicago crime records • Interactive analytics dashboard")
st.divider()

# ---------- FILTERS ----------
st.sidebar.subheader("Filter records")

min_date = df["Date"].min().date()
max_date = df["Date"].max().date()

date_range = st.sidebar.date_input(
    "Date range",
    value=(min_date, max_date),
    min_value=min_date,
    max_value=max_date
)

all_types = sorted(df["Primary Type"].dropna().unique())
selected_types = st.sidebar.multiselect(
    "Crime categories",
    options=all_types,
    default=all_types
)

filtered = df.copy()

if isinstance(date_range, (tuple, list)) and len(date_range) == 2:
    start_date, end_date = date_range
    filtered = filtered[
        filtered["Date"].dt.date.between(start_date, end_date)
    ]

filtered = filtered[filtered["Primary Type"].isin(selected_types)]

if filtered.empty:
    st.warning("No records match these filters. Choose a wider date range or more categories.")
    st.stop()

# ---------- KPI CARDS ----------
total = len(filtered)
categories = filtered["Primary Type"].nunique()
arrest_rate = (
    filtered["Arrest"].astype(str).str.lower().eq("true").mean() * 100
)


# ---------- KPI CARDS ----------
total = len(filtered)
categories = filtered["Primary Type"].nunique()

arrest_values = filtered["Arrest"].astype(str).str.lower()
arrest_rate = arrest_values.eq("true").mean() * 100

most_common = (
    filtered["Primary Type"].mode().iloc[0]
    if not filtered["Primary Type"].mode().empty
    else "N/A"
)

k1, k2, k3, k4 = st.columns(4)

k1.metric("Total Incidents", f"{total:,}")
k2.metric("Crime Categories", f"{categories:,}")
k3.metric("Recorded Arrest Rate", f"{arrest_rate:.1f}%")
k4.metric("Most Common Crime", most_common)


# ---------- MONTHLY TREND ----------
st.subheader("📈 Crime Trends Over Time")

monthly = (
    filtered.set_index("Date")
    .resample("MS")
    .size()
    .reset_index(name="Incidents")
)
monthly.columns = ["Month", "Incidents"]

fig_monthly = px.area(
    monthly,
    x="Month",
    y="Incidents",
    template="plotly_dark",
    color_discrete_sequence=["#3b82f6"]
)
fig_monthly.update_layout(
    paper_bgcolor="#111827",
    plot_bgcolor="#111827",
    margin=dict(l=20, r=20, t=25, b=20),
    xaxis_title="Month",
    yaxis_title="Incident records"
)
st.plotly_chart(fig_monthly, use_container_width=True)

# ---------- COMPARISON CHARTS ----------
left, right = st.columns(2)

with left:
    st.subheader("Most Common Crime Types")
    top_crimes = filtered["Primary Type"].value_counts().head(12).sort_values()
    crime_fig = px.bar(
        x=top_crimes.values,
        y=top_crimes.index,
        orientation="h",
        template="plotly_dark",
        color=top_crimes.values,
        color_continuous_scale=["#1d4ed8", "#60a5fa"],
        labels={"x": "Incident records", "y": "Crime type", "color": "Records"}
    )
    crime_fig.update_layout(
        paper_bgcolor="#111827",
        plot_bgcolor="#111827",
        showlegend=False,
        coloraxis_showscale=False,
        margin=dict(l=10, r=10, t=20, b=20)
    )
    st.plotly_chart(crime_fig, use_container_width=True)

with right:
    st.subheader("Recorded Arrest Outcomes")
    arrest_labels = (
        filtered["Arrest"].astype(str).str.lower()
        .map({"true": "Arrest recorded", "false": "No arrest recorded"})
        .fillna("Unknown")
    )
    arrest_counts = arrest_labels.value_counts().rename_axis("Outcome").reset_index(name="Records")
    arrest_fig = px.pie(
        arrest_counts,
        names="Outcome",
        values="Records",
        hole=0.62,
        template="plotly_dark",
        color="Outcome",
        color_discrete_map={
            "Arrest recorded": "#34d399",
            "No arrest recorded": "#3b82f6",
            "Unknown": "#94a3b8"
        }
    )
    arrest_fig.update_layout(
        paper_bgcolor="#111827",
        margin=dict(l=10, r=10, t=20, b=20),
        legend_title_text=""
    )
    st.plotly_chart(arrest_fig, use_container_width=True)

# ---------- MAP ----------
st.divider()
st.subheader("📍 Incident Locations")
st.caption("Showing up to 5,000 records with usable coordinates.")

if {"Latitude", "Longitude"}.issubset(filtered.columns):
    map_data = filtered[["Latitude", "Longitude"]].dropna()
    map_data = map_data.rename(columns={
        "Latitude": "latitude",
        "Longitude": "longitude"
    })
    map_data = map_data[
        map_data["latitude"].between(41.6, 42.1)
        & map_data["longitude"].between(-88.0, -87.4)
    ]

    if not map_data.empty:
        st.map(map_data.head(5000))
    else:
        st.info("No usable coordinates for these filters.")

# ---------- DATA PREVIEW ----------
with st.expander("🔎 Explore the filtered dataset"):
    st.write(f"Showing up to 100 rows from {len(filtered):,} filtered records.")
    st.dataframe(filtered.head(100), use_container_width=True)

st.divider()
st.caption(
    "Note: These are reported incident counts, not population-adjusted crime rates. "
    "A recorded arrest does not establish guilt."
)

# ---------- ADVANCED CRIME ANALYTICS ----------
st.divider()
st.header("Advanced Crime Analytics")

# Prepare date and time fields
advanced_df = filtered.copy()
advanced_df["Date"] = pd.to_datetime(
    advanced_df["Date"], errors="coerce"
)
advanced_df = advanced_df.dropna(subset=["Date"])
advanced_df["Month"] = advanced_df["Date"].dt.to_period("M").astype(str)
advanced_df["Hour"] = advanced_df["Date"].dt.hour
advanced_df["Day"] = advanced_df["Date"].dt.day_name()

# 1. Monthly crime trend
monthly = (
    advanced_df.groupby("Month")
    .size()
    .reset_index(name="Incidents")
)

fig_monthly = px.line(
    monthly,
    x="Month",
    y="Incidents",
    markers=True,
    title="Monthly Crime Trend",
    template="plotly_white"
)
fig_monthly.update_layout(xaxis_title="Month", yaxis_title="Incidents")
st.plotly_chart(fig_monthly, use_container_width=True)

# 2. Crime by hour
hourly = (
    advanced_df.groupby("Hour")
    .size()
    .reindex(range(24), fill_value=0)
    .reset_index(name="Incidents")
)
hourly.columns = ["Hour", "Incidents"]

fig_hourly = px.bar(
    hourly,
    x="Hour",
    y="Incidents",
    title="Crime by Hour of Day",
    template="plotly_white"
)
st.plotly_chart(fig_hourly, use_container_width=True)

# 3. Crime by weekday
weekday_order = [
    "Monday", "Tuesday", "Wednesday", "Thursday",
    "Friday", "Saturday", "Sunday"
]
weekday = advanced_df["Day"].value_counts().reindex(
    weekday_order, fill_value=0
).reset_index()
weekday.columns = ["Day", "Incidents"]

fig_weekday = px.bar(
    weekday,
    x="Day",
    y="Incidents",
    title="Incidents by Day of Week",
    template="plotly_white"
)
st.plotly_chart(fig_weekday, use_container_width=True)

# 4. Crime categories by district
if "District" in advanced_df.columns:
    district_crime = pd.crosstab(
        advanced_df["District"],
        advanced_df["Primary Type"]
    )

    fig_heatmap = px.imshow(
        district_crime,
        aspect="auto",
        title="Crime Categories by District",
        labels=dict(x="Crime Type", y="District", color="Incidents"),
        template="plotly_white"
    )
    st.plotly_chart(fig_heatmap, use_container_width=True)

# ---------- INTERACTIVE CRIME MAP ----------
st.divider()
st.header("Interactive Crime Map")

map_df = advanced_df.dropna(subset=["Latitude", "Longitude"]).copy()

map_df = map_df[
    map_df["Latitude"].between(41.5, 42.1)
    & map_df["Longitude"].between(-88.0, -87.4)
]

# Limit displayed points for browser performance
map_df = map_df.tail(3000)

if map_df.empty:
    st.warning("No incidents with valid coordinates match these filters.")
else:
    import folium
    from streamlit_folium import st_folium

    crime_map = folium.Map(
        location=[41.8781, -87.6298],
        zoom_start=10,
        tiles="CartoDB positron"
    )

    for _, row in map_df.iterrows():
        folium.CircleMarker(
            location=[row["Latitude"], row["Longitude"]],
            radius=3,
            color="#dc2626",
            fill=True,
            fill_opacity=0.55,
            tooltip=str(row.get("Primary Type", "Crime")),
            popup=(
                f"Crime: {row.get('Primary Type', 'Unknown')}<br>"
                f"Date: {row['Date']}<br>"
                f"District: {row.get('District', 'Unknown')}<br>"
                f"Arrest: {row.get('Arrest', 'Unknown')}"
            )
        ).add_to(crime_map)

    st.caption(f"Showing {len(map_df):,} mapped incidents. Zoom and click markers for details.")
    st_folium(crime_map, width=None, height=600, key="chicago_crime_map")

























