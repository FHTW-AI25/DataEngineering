import os
import pyarrow.parquet as pq
import pandas as pd

DATA_DIR = "../data/usgs_earthquakes"

def load_month(year_month: str):
    """Load the Parquet file for a given year-month (e.g. '2025-11')."""
    path = os.path.join(DATA_DIR, year_month, f"{year_month}.parquet")
    if not os.path.exists(path):
        raise FileNotFoundError(f"No Parquet file found for {year_month} at {path}")
    table = pq.read_table(path)
    df = table.to_pandas()
    print(f"Loaded {len(df):,} rows from {path}")
    return df

# Example usage:
df = load_month("2025-10")
print(df.head())
