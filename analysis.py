
from pathlib import Path
import pandas as pd

# ---------- 1. LOAD DATA ----------
source = Path("data/processed/chicago_crime_cleaned.csv")
output = Path("chicago_crime_analysis.xlsx")

if not source.exists():
    raise FileNotFoundError(f"Dataset not found: {source.resolve()}")

df = pd.read_csv(source, low_memory=False)
df.columns = df.columns.str.strip()

required = ["Date", "Primary Type", "District", "Arrest"]
missing = [col for col in required if col not in df.columns]
if missing:
    raise ValueError(f"Missing required columns: {missing}")

df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
df["Primary Type"] = df["Primary Type"].fillna("Unknown")
df["District"] = df["District"].fillna("Unknown").astype(str)
df["Arrest Recorded"] = (
    df["Arrest"].astype(str).str.strip().str.lower()
    .isin(["true", "1", "yes"])
)

# ---------- 2. ANALYSIS TABLES ----------
total = len(df)
crime_count = df["Primary Type"].nunique()
district_count = df.loc[df["District"] != "Unknown", "District"].nunique()
arrest_count = int(df["Arrest Recorded"].sum())
arrest_rate = round(arrest_count / total * 100, 2) if total else 0

summary = pd.DataFrame({
    "Metric": [
        "Total reported incidents", "Crime categories",
        "Districts represented", "Recorded arrests",
        "Recorded arrest rate (%)"
    ],
    "Value": [total, crime_count, district_count, arrest_count, arrest_rate]
})

top_crimes = (
    df["Primary Type"].value_counts().head(10)
    .rename_axis("Crime Type").reset_index(name="Incidents")
)

dated = df.dropna(subset=["Date"]).copy()
monthly = (
    dated.set_index("Date").resample("ME").size()
    .rename("Incidents").reset_index()
)
monthly["Month"] = monthly["Date"].dt.strftime("%Y-%m")
monthly = monthly[["Month", "Incidents"]]

arrest_report = df.groupby("Primary Type").agg(
    Incidents=("Arrest Recorded", "size"),
    Arrests=("Arrest Recorded", "sum")
).reset_index()
arrest_report["Not Recorded as Arrest"] = (
    arrest_report["Incidents"] - arrest_report["Arrests"]
)
arrest_report["Arrest Rate (%)"] = (
    arrest_report["Arrests"] /
    arrest_report["Incidents"].replace(0, float("nan")) * 100
).round(2)
arrest_report = arrest_report.sort_values("Incidents", ascending=False)

district_report = pd.crosstab(df["District"], df["Primary Type"])
district_report.index.name = "District"

# ---------- 3. CREATE EXCEL WORKBOOK ----------
with pd.ExcelWriter(output, engine="xlsxwriter",
                    datetime_format="yyyy-mm-dd") as writer:
    book = writer.book

    # Theme and formatting
    title_fmt = book.add_format({
        "bold": True, "font_size": 22, "font_color": "white",
        "bg_color": "#17365D", "align": "center", "valign": "vcenter"
    })
    subtitle_fmt = book.add_format({
        "font_size": 10, "font_color": "#555555", "italic": True
    })
    card_label = book.add_format({
        "bold": True, "font_color": "white", "bg_color": "#4472C4",
        "align": "center", "valign": "vcenter", "text_wrap": True,
        "border": 1
    })
    card_value = book.add_format({
        "bold": True, "font_size": 19, "font_color": "#17365D",
        "bg_color": "#D9EAF7", "align": "center", "valign": "vcenter",
        "border": 1, "num_format": "#,##0"
    })
    header_fmt = book.add_format({
        "bold": True, "font_color": "white", "bg_color": "#17365D",
        "border": 1, "text_wrap": True
    })

    # Write data and report sheets
    summary.to_excel(writer, sheet_name="Summary", index=False)
    top_crimes.to_excel(writer, sheet_name="Top Crimes", index=False)
    monthly.to_excel(writer, sheet_name="Monthly Trend", index=False)
    arrest_report.to_excel(writer, sheet_name="Arrest Analysis", index=False)
    district_report.to_excel(writer, sheet_name="District Heatmap")
    df.to_excel(writer, sheet_name="Cleaned Data", index=False)

    for name, data in [
        ("Summary", summary), ("Top Crimes", top_crimes),
        ("Monthly Trend", monthly), ("Arrest Analysis", arrest_report),
        ("District Heatmap", district_report), ("Cleaned Data", df)
    ]:
        ws = writer.sheets[name]
        ws.freeze_panes(1, 0)
        ws.set_row(0, 28, header_fmt)
        if name != "District Heatmap":
            ws.autofilter(0, 0, len(data), len(data.columns) - 1)
        ws.set_column(0, min(max(len(data.columns) - 1, 0), 30), 18)

    # Color-scale heatmap in the district worksheet
    heat_ws = writer.sheets["District Heatmap"]
    if len(district_report) and len(district_report.columns):
        heat_ws.conditional_format(
            1, 1, len(district_report), len(district_report.columns),
            {"type": "3_color_scale", "min_color": "#FFFFFF",
             "mid_color": "#FFE699", "max_color": "#C00000"}
        )

    # ---------- 4. DASHBOARD SHEET ----------
    dash = book.add_worksheet("Dashboard")
    writer.sheets["Dashboard"] = dash
    dash.hide_gridlines(2)
    dash.set_column("A:L", 14)
    dash.set_row(0, 38)
    dash.merge_range("A1:L1", "CHICAGO CRIME ANALYTICS DASHBOARD", title_fmt)
    dash.merge_range(
        "A2:L2",
        "Reported incidents in the supplied dataset | Use detail sheets to explore the data",
        subtitle_fmt
    )

    # Four KPI cards
    cards = [
        ("A4:C4", "A5:C6", "TOTAL INCIDENTS", total),
        ("D4:F4", "D5:F6", "CRIME CATEGORIES", crime_count),
        ("G4:I4", "G5:I6", "RECORDED ARRESTS", arrest_count),
        ("J4:L4", "J5:L6", "DISTRICTS", district_count)
    ]
    for label_range, value_range, label, value in cards:
        dash.merge_range(label_range, label, card_label)
        dash.merge_range(value_range, value, card_value)

    # Chart: top 10 crimes
    chart1 = book.add_chart({"type": "bar"})
    chart1.add_series({
        "name": "Incidents",
        "categories": ["Top Crimes", 1, 0, len(top_crimes), 0],
        "values": ["Top Crimes", 1, 1, len(top_crimes), 1],
        "fill": {"color": "#4472C4"},
        "border": {"none": True}
    })
    chart1.set_title({"name": "Top 10 Crime Categories"})
    chart1.set_x_axis({"name": "Incidents"})
    chart1.set_legend({"none": True})
    chart1.set_size({"width": 570, "height": 320})
    chart1.set_style(10)
    dash.insert_chart("A8", chart1)

    # Chart: monthly trend
    chart2 = book.add_chart({"type": "line"})
    if len(monthly):
        chart2.add_series({
            "name": "Incidents",
            "categories": ["Monthly Trend", 1, 0, len(monthly), 0],
            "values": ["Monthly Trend", 1, 1, len(monthly), 1],
            "line": {"color": "#ED7D31", "width": 2}
        })
    chart2.set_title({"name": "Monthly Crime Trend"})
    chart2.set_x_axis({"name": "Month", "label_position": "low"})
    chart2.set_y_axis({"name": "Incidents"})
    chart2.set_size({"width": 570, "height": 320})
    chart2.set_style(10)
    dash.insert_chart("G8", chart2)

    # Chart: incidents vs arrests for leading categories
    chart3 = book.add_chart({"type": "bar"})
    leading = arrest_report.head(10)
    if len(leading):
        chart3.add_series({
            "name": "Incidents",
            "categories": ["Arrest Analysis", 1, 0, len(leading), 0],
            "values": ["Arrest Analysis", 1, 1, len(leading), 1],
            "fill": {"color": "#4472C4"}
        })
        chart3.add_series({
            "name": "Recorded arrests",
            "categories": ["Arrest Analysis", 1, 0, len(leading), 0],
            "values": ["Arrest Analysis", 1, 2, len(leading), 2],
            "fill": {"color": "#70AD47"}
        })
    chart3.set_title({"name": "Incidents vs Recorded Arrests"})
    chart3.set_x_axis({"name": "Count"})
    chart3.set_size({"width": 570, "height": 320})
    chart3.set_style(10)
    dash.insert_chart("A25", chart3)

    # Chart: arrest rate by leading categories
    chart4 = book.add_chart({"type": "bar"})
    if len(leading):
        chart4.add_series({
            "name": "Arrest rate (%)",
            "categories": ["Arrest Analysis", 1, 0, len(leading), 0],
            "values": ["Arrest Analysis", 1, 4, len(leading), 4],
            "fill": {"color": "#70AD47"}
        })
    chart4.set_title({"name": "Recorded Arrest Rate by Crime Type"})
    chart4.set_x_axis({"name": "Percent"})
    chart4.set_size({"width": 570, "height": 320})
    chart4.set_style(10)
    dash.insert_chart("G25", chart4)

    dash.merge_range(
        "A43:L44",
        "Note: These charts summarize reported incidents in the dataset. "
        "Recorded arrests are not convictions. The district heatmap is on the "
        "'District Heatmap' sheet. Charts are embedded Excel charts; filtering "
        "the detail tables does not automatically recalculate every dashboard chart.",
        subtitle_fmt
    )

print("SUCCESS! Excel dashboard created:")
print(output.resolve())

