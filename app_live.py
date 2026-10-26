from pathlib import Path
from datetime import datetime
import pandas as pd
import plotly.express as px
import streamlit as st
from streamlit_autorefresh import st_autorefresh

ROOT = Path(__file__).resolve().parent
LIVE = ROOT / "data" / "processed" / "chicago_crime_live.csv"
BASE = ROOT / "data" / "processed" / "chicago_crime_cleaned.csv"
STATUS = ROOT / "data" / "live_refresh_status.txt"
st.set_page_config(page_title="Chicago Crime Live Dashboard", page_icon="📊", layout="wide")
st_autorefresh(interval=300000, key="auto_refresh_5min")
st.title("Chicago Crime — Interactive Dashboard")
st.caption("Page refresh: every 5 minutes. The official source updates periodically and excludes the most recent 7 days.")
source = LIVE if LIVE.exists() else BASE
if not source.exists():
    st.error("CSV not found. Run `python live_sync.py` first.")
    st.stop()
@st.cache_data(ttl=300)
def load(path, mtime):
    d = pd.read_csv(path, low_memory=False)
    if "Date" in d: d["Date"] = pd.to_datetime(d["Date"], errors="coerce")
    for c in ["Year","District","Ward","Community Area"]:
        if c in d: d[c] = pd.to_numeric(d[c], errors="coerce")
    for c in ["Arrest","Domestic"]:
        if c in d:
            d[c] = d[c].astype("string").str.lower().map({"true":True,"false":False,"1":True,"0":False}).fillna(False)
    return d
df = load(str(source), source.stat().st_mtime)
with st.sidebar:
    st.header("Filters")
    years = sorted(df["Year"].dropna().astype(int).unique().tolist(), reverse=True) if "Year" in df else []
    ys = st.multiselect("Year", years, default=years[:3])
    types = sorted(df["Primary Type"].dropna().astype(str).unique()) if "Primary Type" in df else []
    ts = st.multiselect("Crime type", types)
    districts = sorted(df["District"].dropna().astype(int).unique().tolist()) if "District" in df else []
    ds = st.multiselect("District", districts)
    arrest = st.selectbox("Arrest status", ["All","Arrest made","No arrest"])
f = df.copy()
if ys and "Year" in f: f = f[f["Year"].isin(ys)]
if ts and "Primary Type" in f: f = f[f["Primary Type"].astype(str).isin(ts)]
if ds and "District" in f: f = f[f["District"].isin(ds)]
if arrest == "Arrest made" and "Arrest" in f: f = f[f["Arrest"] == True]
if arrest == "No arrest" and "Arrest" in f: f = f[f["Arrest"] == False]
a,b,c,d = st.columns(4)
a.metric("Incidents", f"{len(f):,}")
b.metric("Arrests", f"{int(f['Arrest'].sum()):,}" if "Arrest" in f else "N/A")
c.metric("Domestic incidents", f"{int(f['Domestic'].sum()):,}" if "Domestic" in f else "N/A")
cdate = f["Date"].max() if "Date" in f and f["Date"].notna().any() else None
d.metric("Latest incident date", cdate.strftime("%Y-%m-%d") if cdate is not None else "N/A")
left,right = st.columns(2)
with left:
    st.subheader("Top crime types")
    if "Primary Type" in f and not f.empty:
        x=f["Primary Type"].value_counts().head(15).rename_axis("Crime type").reset_index(name="Incidents")
        st.plotly_chart(px.bar(x,x="Incidents",y="Crime type",orientation="h"),use_container_width=True)
with right:
    st.subheader("Monthly trend")
    if "Date" in f and f["Date"].notna().any():
        x=f.dropna(subset=["Date"]).assign(Month=lambda z:z["Date"].dt.to_period("M").astype(str)).groupby("Month").size().reset_index(name="Incidents")
        st.plotly_chart(px.line(x,x="Month",y="Incidents",markers=True),use_container_width=True)
left,right = st.columns(2)
with left:
    st.subheader("Incidents by district")
    if "District" in f and not f.empty:
        x=f["District"].dropna().astype(int).value_counts().sort_index().rename_axis("District").reset_index(name="Incidents")
        st.plotly_chart(px.bar(x,x="District",y="Incidents"),use_container_width=True)
with right:
    st.subheader("Arrest breakdown")
    if "Arrest" in f and not f.empty:
        x=f["Arrest"].map({True:"Arrest made",False:"No arrest"}).value_counts().rename_axis("Status").reset_index(name="Incidents")
        st.plotly_chart(px.pie(x,names="Status",values="Incidents"),use_container_width=True)
st.subheader("Filtered records (preview)")
cols=[c for c in ["ID","Date","Primary Type","Description","District","Arrest","Domestic","Block","Location Description"] if c in f]
st.dataframe(f[cols].head(500),use_container_width=True,hide_index=True)
st.download_button("Download all filtered rows as CSV", f.to_csv(index=False).encode("utf-8"), "chicago_crime_filtered.csv", "text/csv")
st.subheader("Refresh status")
st.code(STATUS.read_text(encoding="utf-8") if STATUS.exists() else "No sync yet. Run python live_sync.py")
st.caption("Dashboard page refreshed at "+datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %Z"))
