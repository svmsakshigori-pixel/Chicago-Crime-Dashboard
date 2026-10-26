
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

k1, k2, k3 = st.columns(3)
k1.metric("Total Incident Records", f"{total:,}")
k2.metric("Crime Categories", f"{categories:,}")
k3.metric("Recorded Arrest Rate", f"{arrest_rate:.1f}%")

st.divider()

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
