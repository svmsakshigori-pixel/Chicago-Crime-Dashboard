from pathlib import Path
from datetime import datetime, timedelta, timezone
import os
import requests
import pandas as pd

ROOT = Path(__file__).resolve().parent
PROC = ROOT / "data" / "processed"
PROC.mkdir(parents=True, exist_ok=True)
BASE_CSV = PROC / "chicago_crime_cleaned.csv"
LIVE_CSV = PROC / "chicago_crime_live.csv"
STATUS = ROOT / "data" / "live_refresh_status.txt"
API = "https://data.cityofchicago.org/resource/ijzp-q8t2.json"
DAYS = 30
COLUMNS = {
    "id":"ID", "case_number":"Case Number", "date":"Date", "block":"Block",
    "iucr":"IUCR", "primary_type":"Primary Type", "description":"Description",
    "location_description":"Location Description", "arrest":"Arrest", "domestic":"Domestic",
    "beat":"Beat", "district":"District", "ward":"Ward", "community_area":"Community Area",
    "fbi_code":"FBI Code", "x_coordinate":"X Coordinate", "y_coordinate":"Y Coordinate",
    "year":"Year", "updated_on":"Updated On", "latitude":"Latitude",
    "longitude":"Longitude", "location":"Location"
}
def status(msg):
    stamp = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")
    STATUS.parent.mkdir(parents=True, exist_ok=True)
    STATUS.write_text(f"Last attempt: {stamp}\n{msg}\n", encoding="utf-8")
    print(f"[{stamp}] {msg}")
def main():
    status("Fetching recent records from the official Chicago crime API.")
    start = (datetime.now(timezone.utc)-timedelta(days=DAYS)).strftime("%Y-%m-%dT%H:%M:%S.000")
    params = {"$where": f"date >= '{start}'", "$order":"date DESC", "$limit":50000}
    r = requests.get(API, params=params, timeout=90,
                     headers={"User-Agent":"ChicagoCrimeStudentDashboard/1.0"})
    r.raise_for_status()
    records = r.json()
    if not isinstance(records, list):
        raise ValueError("Unexpected API response; expected a JSON list.")
    recent = pd.DataFrame(records).rename(columns=COLUMNS)
    for col in COLUMNS.values():
        if col not in recent.columns: recent[col] = pd.NA
    recent = recent[list(COLUMNS.values())]
    # On later runs, merge into the previous live output so records first seen
    # during an earlier sync are preserved. Fall back to the original cleaned CSV.
    if LIVE_CSV.exists():
        base = pd.read_csv(LIVE_CSV, low_memory=False)
    elif BASE_CSV.exists():
        base = pd.read_csv(BASE_CSV, low_memory=False)
    else:
        base = pd.DataFrame(columns=list(COLUMNS.values()))
    for col in COLUMNS.values():
        if col not in base.columns: base[col] = pd.NA
    merged = pd.concat([base, recent], ignore_index=True, sort=False)
    if "ID" in merged:
        merged["ID"] = merged["ID"].astype("string")
        merged = merged.drop_duplicates(subset=["ID"], keep="last")
    if "Date" in merged: merged["Date"] = pd.to_datetime(merged["Date"], errors="coerce")
    if "Year" in merged: merged["Year"] = pd.to_numeric(merged["Year"], errors="coerce")
    if "Date" in merged: merged = merged.sort_values("Date", ascending=False, na_position="last")
    temp = LIVE_CSV.with_suffix(".tmp")
    merged.to_csv(temp, index=False)
    os.replace(temp, LIVE_CSV)
    status(f"SUCCESS. API records fetched: {len(recent):,}. Combined rows: {len(merged):,}. Output: {LIVE_CSV}")
if __name__ == "__main__":
    try: main()
    except Exception as e:
        status(f"FAILED: {type(e).__name__}: {e}")
        raise
