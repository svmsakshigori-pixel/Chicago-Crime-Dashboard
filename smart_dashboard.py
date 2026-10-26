
from pathlib import Path
import pandas as pd

# ==========================================
# CHICAGO CRIME EXCEL DASHBOARD
# Compatible with Python 3.13 and Excel 365
# ==========================================

BASE_DIR = Path(__file__).resolve().parent

CSV_FILE = (
    BASE_DIR / "data" / "processed"
    / "chicago_crime_cleaned.csv"
)

OUTPUT_FILE = BASE_DIR / "chicago_crime_smart_dashboard_new.xlsx"

if not CSV_FILE.exists():
    raise FileNotFoundError(
        f"CSV file not found: {CSV_FILE}\n"
        "Check data/processed/chicago_crime_cleaned.csv"
    )

print("Loading cleaned Chicago crime data...")
df = pd.read_csv(CSV_FILE, low_memory=False)
df.columns = df.columns.str.strip()

# Find columns safely
def get_column(name):
    for col in df.columns:
        if col.strip().lower() == name.lower():
            return col
    return None

date_col = get_column("Date")
crime_col = get_column("Primary Type")
district_col = get_column("District")
arrest_col = get_column("Arrest")

if date_col is None or crime_col is None:
    raise ValueError(
        "The CSV must contain Date and Primary Type columns."
    )

# Prepare analysis fields
df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
df["Dashboard Year"] = df[date_col].dt.year
df["Dashboard Month"] = (
    df[date_col].dt.to_period("M").astype("string")
)

df["Dashboard Crime Type"] = (
    df[crime_col].fillna("Unknown").astype(str).str.strip()
)

if district_col:
    df["Dashboard District"] = (
        df[district_col].fillna("Unknown").astype(str).str.strip()
    )
else:
    df["Dashboard District"] = "Unknown"

if arrest_col:
    arrest_values = df[arrest_col]

    if pd.api.types.is_bool_dtype(arrest_values):
        df["Dashboard Arrest"] = arrest_values.fillna(False)
    else:
        df["Dashboard Arrest"] = (
            arrest_values.astype(str).str.strip().str.lower()
            .isin(["true", "1", "yes", "y"])
        )
else:
    df["Dashboard Arrest"] = False

# Calculate summary tables
total_incidents = len(df)
total_arrests = int(df["Dashboard Arrest"].sum())
arrest_rate = (
    total_arrests / total_incidents
    if total_incidents else 0
)

crime_summary = (
    df.groupby("Dashboard Crime Type")
    .size()
    .reset_index(name="Incidents")
    .sort_values("Incidents", ascending=False)
)

top_crimes = crime_summary.head(10).copy()

monthly_summary = (
    df.dropna(subset=[date_col])
    .groupby("Dashboard Month")
    .size()
    .reset_index(name="Incidents")
    .sort_values("Dashboard Month")
)

district_summary = (
    df.groupby("Dashboard District")
    .size()
    .reset_index(name="Incidents")
    .sort_values("Incidents", ascending=False)
)

arrest_summary = pd.DataFrame({
    "Arrest Status": ["Arrest recorded", "No arrest recorded"],
    "Incidents": [
        total_arrests,
        total_incidents - total_arrests
    ]
})

# Monthly crime by category and district
crime_district = pd.pivot_table(
    df,
    index="Dashboard District",
    columns="Dashboard Crime Type",
    values=crime_col,
    aggfunc="count",
    fill_value=0
)

# Build workbook
print("Creating Excel workbook...")

with pd.ExcelWriter(
    OUTPUT_FILE,
    engine="xlsxwriter",
    datetime_format="yyyy-mm-dd hh:mm:ss"
) as writer:

    workbook = writer.book

    # Formatting
    title_fmt = workbook.add_format({
        "bold": True,
        "font_size": 22,
        "font_color": "white",
        "bg_color": "#17365D",
        "align": "left",
        "valign": "vcenter"
    })

    subtitle_fmt = workbook.add_format({
        "font_size": 10,
        "font_color": "#666666"
    })

    label_fmt = workbook.add_format({
        "bold": True,
        "font_color": "white",
        "bg_color": "#4472C4",
        "align": "center",
        "valign": "vcenter",
        "border": 1
    })

    number_fmt = workbook.add_format({
        "bold": True,
        "font_size": 20,
        "font_color": "#17365D",
        "bg_color": "#D9EAF7",
        "align": "center",
        "valign": "vcenter",
        "num_format": "#,##0"
    })

    percent_fmt = workbook.add_format({
        "bold": True,
        "font_size": 20,
        "font_color": "#17365D",
        "bg_color": "#D9EAF7",
        "align": "center",
        "valign": "vcenter",
        "num_format": "0.0%"
    })

    header_fmt = workbook.add_format({
        "bold": True,
        "font_color": "white",
        "bg_color": "#17365D",
        "text_wrap": True,
        "valign": "vcenter"
    })

    # Export detail data
    df.to_excel(writer, sheet_name="Crime Data", index=False)
    data_ws = writer.sheets["Crime Data"]

    data_ws.freeze_panes(1, 0)
    data_ws.set_default_row(18)
    data_ws.set_row(0, 30, header_fmt)
    data_ws.set_column(0, len(df.columns) - 1, 18)

    # Excel table with filter dropdowns
    data_ws.add_table(
        0, 0, len(df), len(df.columns) - 1,
        {
            "name": "CrimeData",
            "style": "Table Style Medium 2",
            "columns": [
                {"header": str(c)} for c in df.columns
            ],
            "autofilter": True
        }
    )

    # Export analysis sheets
    crime_summary.to_excel(
        writer, sheet_name="Crime Summary", index=False
    )
    top_crimes.to_excel(
        writer, sheet_name="Top Crimes", index=False
    )
    monthly_summary.to_excel(
        writer, sheet_name="Monthly Trend", index=False
    )
    district_summary.to_excel(
        writer, sheet_name="District Analysis", index=False
    )
    arrest_summary.to_excel(
        writer, sheet_name="Arrest Analysis", index=False
    )
    crime_district.to_excel(
        writer, sheet_name="District Heatmap"
    )

    for name in [
        "Crime Summary", "Top Crimes", "Monthly Trend",
        "District Analysis", "Arrest Analysis"
    ]:
        ws = writer.sheets[name]
        ws.freeze_panes(1, 0)
        ws.set_row(0, 28, header_fmt)
        ws.set_column(0, 0, 28)
        ws.set_column(1, 5, 18)

    # Heatmap formatting
    heat_ws = writer.sheets["District Heatmap"]
    heat_ws.freeze_panes(1, 1)
    heat_ws.set_column(0, 0, 20)
    heat_ws.set_column(1, max(1, len(crime_district.columns)), 14)

    if len(crime_district.index) and len(crime_district.columns):
        heat_ws.conditional_format(
            1, 1,
            len(crime_district.index),
            len(crime_district.columns),
            {
                "type": "3_color_scale",
                "min_color": "#E2F0D9",
                "mid_color": "#FFD966",
                "max_color": "#C00000"
            }
        )

    # Dashboard sheet
    dash = workbook.add_worksheet("Dashboard")
    writer.sheets["Dashboard"] = dash

    dash.hide_gridlines(2)
    dash.set_zoom(85)
    dash.set_column("A:N", 14)
    dash.set_row(0, 40)

    dash.merge_range(
        "A1:N1",
        "CHICAGO CRIME ANALYTICS DASHBOARD",
        title_fmt
    )
    dash.merge_range(
        "A2:N2",
        "Incident overview | Based on your cleaned dataset",
        subtitle_fmt
    )

    # KPI cards
    cards = [
        ("A4:C4", "A5:C6", "TOTAL INCIDENTS",
         total_incidents, number_fmt),
        ("D4:F4", "D5:F6", "RECORDED ARRESTS",
         total_arrests, number_fmt),
        ("G4:I4", "G5:I6", "ARREST RATE",
         arrest_rate, percent_fmt),
        ("J4:L4", "J5:L6", "DISTRICTS",
         int(df["Dashboard District"].nunique()), number_fmt)
    ]

    for label_range, value_range, label, value, fmt in cards:
        dash.merge_range(label_range, label, label_fmt)
        dash.merge_range(value_range, value, fmt)

    def make_chart(chart_type, sheet, title, rows):
        chart = workbook.add_chart({"type": chart_type})

        if rows > 0:
            chart.add_series({
                "name": title,
                "categories": [sheet, 1, 0, rows, 0],
                "values": [sheet, 1, 1, rows, 1],
                "fill": {"color": "#4472C4"},
                "border": {"none": True}
            })

        chart.set_title({"name": title})
        chart.set_legend({"none": True})
        chart.set_size({"width": 540, "height": 300})
        chart.set_style(10)
        return chart

    dash.insert_chart(
        "A8",
        make_chart(
            "bar", "Top Crimes", "Top 10 Crime Types",
            len(top_crimes)
        )
    )

    dash.insert_chart(
        "G8",
        make_chart(
            "line", "Monthly Trend", "Monthly Incident Trend",
            len(monthly_summary)
        )
    )

    dash.insert_chart(
        "A24",
        make_chart(
            "bar", "District Analysis", "Incidents by District",
            len(district_summary)
        )
    )

    dash.insert_chart(
        "G24",
        make_chart(
            "doughnut", "Arrest Analysis", "Arrest Status",
            len(arrest_summary)
        )
    )

    dash.merge_range(
        "A41:N42",
        "INTERACTIVITY: Use filters in Crime Data. For slicers that "
        "control multiple charts, create PivotTables and PivotCharts "
        "from the CrimeData Excel table, then connect them using "
        "PivotTable Analyze > Insert Slicer > Report Connections.",
        subtitle_fmt
    )

    dash.freeze_panes(3, 0)
    dash.set_landscape()
    dash.fit_to_pages(1, 2)
    dash.set_margins(0.25, 0.25, 0.5, 0.5)

print("\nSUCCESS!")
print(f"Excel dashboard saved to:\n{OUTPUT_FILE}")
print("\nOpen the file in Excel 365 to view the dashboard.")
