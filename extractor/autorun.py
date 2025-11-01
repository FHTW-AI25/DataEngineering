import os, json, time
from datetime import datetime, timedelta, timezone
from dateutil.relativedelta import relativedelta
from urllib.parse import urlencode

import requests
import pyarrow as pa
import pyarrow.parquet as pq
import psycopg2

# ---------------------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------------------
DATA_DIR = os.environ.get("DATA_DIR", "data/usgs_earthquakes")
USGS_BASE_URL = os.environ.get("USGS_BASE_URL", "https://earthquake.usgs.gov/fdsnws/event/1/query")
DATABASE_URL = os.environ.get("DATABASE_URL", "")

MONTHS_BEFORE_CURRENT   = int(os.environ.get("MONTHS_BEFORE_CURRENT", "12"))
REQUEST_TIMEOUT_SECONDS = float(os.environ.get("REQUEST_TIMEOUT_SECONDS", "60"))
REQUEST_SLEEP_SECONDS   = float(os.environ.get("REQUEST_SLEEP_SECONDS", "0.2"))
MAX_SPLIT_RETRIES       = int(os.environ.get("MAX_SPLIT_RETRIES", "20"))

# ---------------------------------------------------------------------
# DATABASE
# ---------------------------------------------------------------------
def _conn():
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL is not set")
    return psycopg2.connect(DATABASE_URL)

def upsert_loaded(month_start, month_end):
    with _conn() as conn, conn.cursor() as cur:
        cur.execute("""
            INSERT INTO monthly_loads (month_start, month_end, status)
            VALUES (%s, %s, 'loaded')
            ON CONFLICT (month_start) DO UPDATE SET
              month_end  = EXCLUDED.month_end,
              status     = 'loaded',
              updated_at = NOW();
        """, (month_start, month_end))
        conn.commit()

# ---------------------------------------------------------------------
# FETCH
# ---------------------------------------------------------------------
class BadRequest400(Exception): pass

def _url(s, e):
    return (
        f"{USGS_BASE_URL}"
        f"?format=geojson"
        f"&starttime={s.strftime('%Y-%m-%dT%H:%M:%SZ')}"
        f"&endtime={e.strftime('%Y-%m-%dT%H:%M:%SZ')}"
    )

def fetch_geojson(s, e):
    r = requests.get(_url(s, e), timeout=REQUEST_TIMEOUT_SECONDS)
    time.sleep(REQUEST_SLEEP_SECONDS)
    if r.status_code == 400:
        raise BadRequest400(r.text)
    r.raise_for_status()
    return r.json()

# ---------------------------------------------------------------------
# WRITE
# ---------------------------------------------------------------------
def write_parquet(features, month_start):
    """Write all features for a month into a single Parquet file."""
    if not features:
        return None

    month_folder = month_start.strftime("%Y-%m")
    outdir = os.path.join(DATA_DIR, month_folder)
    os.makedirs(outdir, exist_ok=True)

    fname = f"{month_folder}.parquet"
    fpath = os.path.join(outdir, fname)

    rows = [json.dumps(f, separators=(",", ":"), ensure_ascii=False) for f in features]
    table = pa.Table.from_arrays([pa.array(rows, type=pa.large_string())], names=["json"])
    pq.write_table(table, fpath)
    return fpath

def process_with_split(month_start, start_ts, end_ts, min_chunk=timedelta(hours=1), retries_left=MAX_SPLIT_RETRIES):
    try:
        geo = fetch_geojson(start_ts, end_ts)
        feats = geo.get("features", []) or []
        return feats
    except BadRequest400:
        if (end_ts - start_ts) <= min_chunk or retries_left <= 0:
            return []
        mid = start_ts + (end_ts - start_ts) / 2
        left = process_with_split(month_start, start_ts, mid, min_chunk, retries_left-1)
        right = process_with_split(month_start, mid, end_ts, min_chunk, retries_left-1)
        return left + right

# ---------------------------------------------------------------------
# HELPERS
# ---------------------------------------------------------------------
def month_bounds_utc(dt: datetime):
    start = dt.replace(day=1, hour=0, minute=0, second=0, microsecond=0, tzinfo=timezone.utc)
    end_exclusive = start + relativedelta(months=1)
    end_inclusive = end_exclusive - timedelta(milliseconds=1)
    return start, end_inclusive, end_exclusive

def months_to_process(now_utc: datetime, months_before_current: int):
    cur_start, cur_end_inclusive, cur_end_exclusive = month_bounds_utc(now_utc)
    # Include current month (partial) — end_ts is "now"
    yield cur_start, now_utc, now_utc
    # Include previous full months
    for i in range(1, months_before_current + 1):
        mstart = cur_start - relativedelta(months=i)
        mend_inclusive = (mstart + relativedelta(months=1)) - timedelta(milliseconds=1)
        mend_exclusive = mstart + relativedelta(months=1)
        yield mstart, mend_inclusive, mend_exclusive

# ---------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------
def main():
    now = datetime.now(timezone.utc)
    for mstart, mend_inclusive, mend_exclusive in months_to_process(now, MONTHS_BEFORE_CURRENT):
        ym = mstart.strftime("%Y-%m")
        print(f"[{ym}] fetching data from {mstart} to {mend_exclusive}")

        features = process_with_split(mstart, mstart, mend_exclusive)
        fpath = write_parquet(features, mstart)
        upsert_loaded(mstart, mend_inclusive)

        print(f"[{ym}] loaded {len(features)} features → {fpath}")

if __name__ == "__main__":
    main()
