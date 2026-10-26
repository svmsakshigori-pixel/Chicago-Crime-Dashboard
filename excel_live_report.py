from pathlib import Path
from datetime import datetime
import pandas as pd

ROOT = Path(__file__).resolve().parent
LIVE = ROOT / "data" / "processed" / "chicago_crime_live.csv"
BASE = ROOT / "data" / "processed" / "chicago_crime_cleaned.csv"
OUTPUT = ROOT / "chicago_crime_live_dashboard.xlsx"
def main():
    src = LIVE if LIVE.exists() else BASE
    if not src.exists(): raise FileNotFoundError("Run python live_sync.py first.")
    print(f"Reading {src}")
    df = pd.read_csv(src, low_memory=False)
    if "Date" in df: df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    if "Year" not in df and "Date" in df: df["Year"] = df["Date"].dt.year
    if "Primary Type" not in df: raise ValueError("Column 'Primary Type' missing.")
    for col in ["Arrest","Domestic"]:
        if col in df: df[col] = df[col].astype("string").str.lower().map({"true":True,"false":False,"1":True,"0":False})
    types=df["Primary Type"].fillna("Unknown").value_counts().rename_axis("Primary Type").reset_index(name="Incidents")
    years=df.groupby("Year",dropna=True).size().reset_index(name="Incidents").sort_values("Year") if "Year" in df else pd.DataFrame()
    districts=df.groupby("District",dropna=True).size().reset_index(name="Incidents").sort_values("District") if "District" in df else pd.DataFrame()
    arrests=df["Arrest"].map({True:"Arrest made",False:"No arrest"}).value_counts().rename_axis("Status").reset_index(name="Incidents") if "Arrest" in df else pd.DataFrame()
    kpis=pd.DataFrame([["Total incidents",len(df)],["Crime types",int(df["Primary Type"].nunique())],["Report generated",datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")],["Source",str(src.relative_to(ROOT))]],columns=["Metric","Value"])
    try:
        with pd.ExcelWriter(OUTPUT,engine="xlsxwriter",datetime_format="yyyy-mm-dd hh:mm:ss") as w:
            kpis.to_excel(w,sheet_name="Dashboard",index=False,startrow=1)
            types.head(20).to_excel(w,sheet_name="Dashboard",index=False,startrow=8)
            years.to_excel(w,sheet_name="Year Trend",index=False)
            districts.to_excel(w,sheet_name="Districts",index=False)
            arrests.to_excel(w,sheet_name="Arrests",index=False)
            df.to_excel(w,sheet_name="Crime Data",index=False)
            wb=w.book; dash=w.sheets["Dashboard"]
            dash.write("A1","Chicago Crime Live Dashboard",wb.add_format({"bold":True,"font_size":18}))
            for s in w.sheets.values(): s.freeze_panes(1,0)
            if not years.empty:
                ch=wb.add_chart({"type":"line"})
                ch.add_series({"name":"Incidents","categories":["Year Trend",1,0,len(years),0],"values":["Year Trend",1,1,len(years),1]})
                ch.set_title({"name":"Incidents by year"}); dash.insert_chart("D2",ch)
            if not types.empty:
                n=min(20,len(types)); ch=wb.add_chart({"type":"bar"})
                ch.add_series({"name":"Incidents","categories":["Dashboard",9,0,8+n,0],"values":["Dashboard",9,1,8+n,1]})
                ch.set_title({"name":"Top crime types"}); ch.set_legend({"none":True}); dash.insert_chart("D18",ch)
            w.sheets["Crime Data"].autofilter(0,0,len(df),len(df.columns)-1)
    except PermissionError:
        stamp=datetime.now().strftime("%Y%m%d_%H%M%S")
        out=ROOT/f"chicago_crime_live_dashboard_{stamp}.xlsx"
        with pd.ExcelWriter(out,engine="xlsxwriter",datetime_format="yyyy-mm-dd hh:mm:ss") as w:
            kpis.to_excel(w,sheet_name="Dashboard",index=False)
            types.to_excel(w,sheet_name="Crime Types",index=False)
            years.to_excel(w,sheet_name="Year Trend",index=False)
            districts.to_excel(w,sheet_name="Districts",index=False)
            arrests.to_excel(w,sheet_name="Arrests",index=False)
            df.to_excel(w,sheet_name="Crime Data",index=False)
        print(f"Workbook was locked; saved separate copy instead: {out}")
        return
    print(f"SUCCESS: Excel report saved to {OUTPUT}")
if __name__=="__main__": main()
