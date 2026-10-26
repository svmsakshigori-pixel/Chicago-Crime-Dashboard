
import streamlit as st
import pandas as pd
import plotly.express as px
from pathlib import Path

st.set_page_config(
    page_title="Chicago Crime Dashboard",
    page_icon="📊",
    layout="wide"
)

DATA_FILE = Path("data/processed/chicago_crime_cleaned.csv")


@st.cache_data
def load_data(path):
    df = pd.read_csv(path, low_memory=False)
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df = df.dropna(subset=["Date"])
    df["Month"] = df["Date"].dt.to_period("M").astype(str)
    return df


st.title("📊 Chicago Crime Analysis Dashboard")
st.caption("Explore reported crime patterns, trends, and arrest data.")

if not DATA_FILE.exists():
    st.error(f"Dataset not found: {DATA_FILE.resolve()}")
    st.stop()

with st.spinner("Loading crime data..."):
    df = load_data(str(DATA_FILE))

# Sidebar filters
st.sidebar.header("Dashboard Filters")

min_date = df["Date"].min().date()
max_date = df["Date"].max().date()

date_range = st.sidebar.date_input(
    "Select date range",
    value=(min_date, max_date),
    min_value=min_date,
    max_value=max_date
)

crime_types = sorted(df["Primary Type"].dropna().unique())

selected_types = st.sidebar.multiselect(
    "Crime categories",
    options=crime_types,
    default=[]
)

filtered = df.copy()

if isinstance(date_range, (tuple, list)) and len(date_range) == 2:
    start_date, end_date = date_range
    filtered = filtered[
        filtered["Date"].dt.date.between(start_date, end_date)
    ]

if selected_types:
    filtered = filtered[
        filtered["Primary Type"].isin(selected_types)
    ]

# KPI cards
total = len(filtered)
arrest_rate = (
    filtered["Arrest"].fillna(False).astype(bool).mean() * 100
    if total else 0
)

col1, col2, col3 = st.columns(3)
col1.metric("Reported Incidents", f"{total:,}")
col2.metric("Crime Categories", f"{filtered['Primary Type'].nunique():,}")
col3.metric("Recorded Arrest Rate", f"{arrest_rate:.1f}%")

st.divider()

# Monthly trends
st.subheader("📈 Crime Trends Over Time")

monthly = (
    filtered.set_index("Date")
    .resample("MS")
    .size()
    .reset_index(name="Incidents")
)

fig = px.line(
    monthly,
    x="Date",
    y="Incidents",
    markers=True,
    title="Monthly Reported Incidents"
)
st.plotly_chart(fig, use_container_width=True)

# Crime categories
st.subheader("🚨 Most Frequently Reported Crime Types")

top_crimes = filtered["Primary Type"].value_counts().head(15)
top_crimes = top_crimes.sort_values().reset_index()
top_crimes.columns = ["Crime Type", "Incidents"]

fig2 = px.bar(
    top_crimes,
    x="Incidents",
    y="Crime Type",
    orientation="h",
    title="Top 15 Crime Categories"
)
st.plotly_chart(fig2, use_container_width=True)

# Arrest analysis
st.subheader("👮 Arrest Analysis")

if "Arrest" in filtered.columns:
    arrest_counts = (
        filtered["Arrest"].fillna(False)
        .map({True: "Arrest recorded", False: "No arrest recorded"})
        .value_counts()
        .rename_axis("Outcome")
        .reset_index(name="Incidents")
    )

    fig3 = px.pie(
        arrest_counts,
        names="Outcome",
        values="Incidents",
        title="Recorded Arrest Outcomes",
        hole=0.4
    )
    st.plotly_chart(fig3, use_container_width=True)

# Geographic analysis
st.subheader("📍 Incident Locations")

if {"Latitude", "Longitude"}.issubset(filtered.columns):
    map_data = filtered[["Latitude", "Longitude"]].dropna()

    # Rename columns so Streamlit recognizes them
    map_data = map_data.rename(columns={
        "Latitude": "latitude",
        "Longitude": "longitude"
    })

    if not map_data.empty:
        st.caption(
            f"Showing up to 5,000 mapped records out of "
            f"{len(map_data):,} records with coordinates."
        )
        st.map(map_data.head(5000))
    else:
        st.info("No usable coordinates in the selected records.")

# Data preview
with st.expander("View dataset preview"):
    st.dataframe(filtered.head(100), use_container_width=True)

st.caption(
    "These are reported incident counts, not population-adjusted crime rates. "
    "An arrest recorded does not by itself indicate guilt."
)
