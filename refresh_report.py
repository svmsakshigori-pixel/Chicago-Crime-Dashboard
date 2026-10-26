
from pathlib import Path
from datetime import datetime
import subprocess
import sys
import pandas as pd

BASE = Path(__file__).resolve().parent
CSV_FILE = BASE / "data" / "processed" / "chicago_crime_cleaned.csv"
REPORT_SCRIPT = BASE / "smart_dashboard.py"
LOG_FILE = BASE / "refresh_log.txt"

def log(message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {message}"
    print(line)
    with LOG_FILE.open("a", encoding="utf-8") as file:
        file.write(line + "\n")

def main():
    log("Starting Chicago Crime report refresh.")

    if not CSV_FILE.exists():
        log(f"ERROR: CSV not found: {CSV_FILE}")
        sys.exit(1)

    if not REPORT_SCRIPT.exists():
        log(f"ERROR: Script not found: {REPORT_SCRIPT}")
        sys.exit(1)

    # Validate the CSV before generating a report.
    try:
        df = pd.read_csv(CSV_FILE, low_memory=False)
    except Exception as error:
        log(f"ERROR: Could not read CSV: {error}")
        sys.exit(1)

    if df.empty:
        log("ERROR: CSV contains no rows.")
        sys.exit(1)

    if "Date" not in df.columns or "Primary Type" not in df.columns:
        log("ERROR: Required columns Date and Primary Type are missing.")
        sys.exit(1)

    log(f"Validation successful: {len(df):,} rows, {len(df.columns)} columns.")

    # Run the Excel report generator with the current Python interpreter.
    result = subprocess.run(
        [sys.executable, str(REPORT_SCRIPT)],
        cwd=str(BASE),
        capture_output=True,
        text=True
    )

    if result.stdout:
        print(result.stdout)

    if result.returncode != 0:
        log("ERROR: Report generation failed.")
        if result.stderr:
            print(result.stderr)
        sys.exit(result.returncode)

    log("Excel report refresh completed successfully.")

if __name__ == "__main__":
    main()
