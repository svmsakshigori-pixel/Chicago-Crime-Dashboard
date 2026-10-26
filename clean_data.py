import pandas as pd
from pathlib import Path

input_file = Path("data/raw/chicago_crime.csv")
output_dir = Path("data/processed")
output_file = output_dir / "chicago_crime_cleaned.csv"

def main():
    if not input_file.exists():
        print(f"ERROR: Dataset not found: {input_file.resolve()}")
        return

    output_dir.mkdir(parents=True, exist_ok=True)

    print("Loading Chicago crime dataset...", flush=True)
    df = pd.read_csv(input_file, low_memory=False)
    original_rows = len(df)
    print(f"Original rows: {original_rows:,}", flush=True)

    duplicates_removed = 0
    if "ID" in df.columns:
        before = len(df)
        df = df.drop_duplicates(subset=["ID"], keep="first")
        duplicates_removed = before - len(df)

    df["Date"] = pd.to_datetime(
        df["Date"],
        format="%m/%d/%Y %I:%M:%S %p",
        errors="coerce"
    )

    invalid_dates = int(df["Date"].isna().sum())
    df = df.dropna(subset=["Date"]).copy()

    missing_latitude = int(df["Latitude"].isna().sum())
    missing_longitude = int(df["Longitude"].isna().sum())

    if "Location Description" in df.columns:
        df["Location Description"] = (
            df["Location Description"].fillna("Unknown")
        )

    df.to_csv(output_file, index=False)

    print("\n--- CLEANING SUMMARY ---")
    print(f"Original rows: {original_rows:,}")
    print(f"Duplicate IDs removed: {duplicates_removed:,}")
    print(f"Invalid-date rows removed: {invalid_dates:,}")
    print(f"Rows with missing latitude: {missing_latitude:,}")
    print(f"Rows with missing longitude: {missing_longitude:,}")
    print(f"Cleaned rows: {len(df):,}")
    print(f"Saved file: {output_file.resolve()}")
    print("Cleaning complete!")

if __name__ == "__main__":
    main()
