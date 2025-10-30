# extractor/autorun.py
from __future__ import annotations

import os
import time
import datetime as dt
from datetime import timezone, timedelta
from typing import Iterable, Tuple

import requests
import pandas as pd
import psycopg2


# ----------------------------
# Config (env-driven defaults)
# ----------------------------
DB = dict(
    db=os.getenv("POSTGRES_DB", "db"),
    user=os.getenv("POSTGRES_USER", "admin"),
    pwd=os.getenv("POSTGRES_PASSWORD", "password"),
    host=os.getenv("POSTGRES_HOST", "localhost"),
    port=int(os.getenv("POSTGRES_PORT", "5432")),
)

LAKE = os.getenv("LAKE_ROOT", "/lake/quakes")

MONTHS_BACK = int(os.getenv("EXTRACTOR_MONTHS", "12"))       # how many full past months to land (excl current)
SLEEP_S     = float(os.getenv("EXTRACTOR_SLEEP_SECONDS", "1"))
RETRIES     = int(os.getenv("EXTRACTOR_MAX_RETRIES", "3"))
TIMEOUT_S   = int(os.getenv("EXTRACTOR_TIMEOUT_SECONDS", "120"))
BOOTSTRAP   = os.getenv("EXTRACTOR_BOOTSTRAP", "true").lower() == "true"

LOCK_KEY = 2025103001  # app-wide advisory lock id (arbitrary but stable)


# -------------
# DB utilities
# -------------
def pg():
    return psycopg2.connect(
        dbname=DB["db"],
        user=DB["user"],
        password=DB["pwd"],
        host=DB["host"],
        port=DB["port"],
    )


def try_lock(conn) -> bool:
    with conn.cursor() as cur:
        cur.execute("SELECT pg_try_advisory_lock(%s)", (LOCK_KEY,))
        return cur.fetchone()[0] is True


def unlock(conn):
    with conn.cursor() as cur:
        cur.execute("SELECT pg_advisory_unlock(%s)", (LOCK_KEY,))


def catalog_get(ms: dt.date):
    """Return row for month_start or None."""
    with pg() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT status, finalized, rows, coverage_start_utc, coverage_end_utc, updated_at, error
            FROM data_catalog
            WHERE month_start = %s
            """,
            (ms,),
        )
        return cur.fetchone()


def catalog_upsert(
    ms: dt.date,
    *,
    status: str,
    rows: int = 0,
    finalized: bool = False,
    coverage_start_utc: dt.datetime,
    coverage_end_utc: dt.datetime,
    error: str | None = None,
):
    """Idempotent upsert into data_catalog (matches your schema)."""
    with pg() as conn, conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO data_catalog
              (month_start, status, rows, finalized, coverage_start_utc, coverage_end_utc, error, updated_at)
            VALUES
              (%s, %s, %s, %s, %s, %s, %s, now())
            ON CONFLICT (month_start) DO UPDATE SET
              status = EXCLUDED.status,
              rows = EXCLUDED.rows,
              finalized = EXCLUDED.finalized,
              coverage_start_utc = EXCLUDED.coverage_start_utc,
              coverage_end_utc = EXCLUDED.coverage_end_utc,
              error = EXCLUDED.error,
              updated_at = now()
            """,
            (ms, status, rows, finalized, coverage_start_utc, coverage_end_utc, error),
        )
        conn.commit()


# -------------------------
# Month helpers (UTC-aware)
# -------------------------
def month_start(d: dt.date) -> dt.date:
    return d.replace(day=1)


def month_bounds_utc(ms: dt.date) -> Tuple[dt.datetime, dt.datetime]:
    """Return [start,end] as UTC-aware datetimes where end is last second of the month."""
    start = dt.datetime(ms.year, ms.month, 1, tzinfo=timezone.utc)
    if ms.month == 12:
        nxt = dt.datetime(ms.year + 1, 1, 1, tzinfo=timezone.utc)
    else:
        nxt = dt.datetime(ms.year, ms.month + 1, 1, tzinfo=timezone.utc)
    end = nxt - timedelta(seconds=1)
    return start, end


def list_target_months() -> list[dt.date]:
    """Return the last N full months (excluding current) + the current month."""
    now = dt.datetime.now(timezone.utc)
    first_of_curr = month_start(now.date())
    months: list[dt.date] = []
    d = first_of_curr
    for _ in range(MONTHS_BACK):
        d = (d - dt.timedelta(days=1)).replace(day=1)
        months.append(d)
    months.append(first_of_curr)
    months.sort()
    return months


# -------------------------
# USGS fetch (retry w/backoff)
# -------------------------
def fetch_range(start_utc: dt.datetime, end_utc: dt.datetime) -> pd.DataFrame:
    assert start_utc.tzinfo is not None and end_utc.tzinfo is not None, "Use UTC-aware datetimes"
    base = "https://earthquake.usgs.gov/fdsnws/event/1/query"
    url = (
        f"{base}?format=geojson"
        f"&starttime={start_utc:%Y-%m-%dT%H:%M:%SZ}"
        f"&endtime={end_utc:%Y-%m-%dT%H:%M:%SZ}"
    )

    s = requests.Session()
    for attempt in range(1, RETRIES + 1):
        try:
            r = s.get(url, timeout=TIMEOUT_S)
            r.raise_for_status()
            features = r.json().get("features", [])
            rows = []
            for f in features:
                p = f.get("properties") or {}
                g = f.get("geometry") or {}
                c = (g.get("coordinates") or [None, None, None])

                # Build a stable usgs_id (net+code when net exists; else code)
                net, code = p.get("net"), p.get("code")
                usgs_id = f"{net}{code}" if net else code

                # properties.time/updated are ms since epoch
                def ts_ms_to_utc(v):
                    if v is None:
                        return None
                    return dt.datetime.fromtimestamp(v / 1000.0, tz=timezone.utc)

                rows.append(
                    dict(
                        usgs_id=usgs_id,
                        mag=p.get("mag"),
                        place=p.get("place"),
                        time_utc=ts_ms_to_utc(p.get("time")),
                        updated_utc=ts_ms_to_utc(p.get("updated")),
                        url=p.get("url"),
                        detail_url=p.get("detail"),
                        tsunami=p.get("tsunami") or 0,
                        sig=p.get("sig"),
                        mag_type=p.get("magType"),
                        typ=p.get("type"),
                        title=p.get("title"),
                        net=p.get("net"),
                        code=p.get("code"),
                        depth_km=(c[2] if len(c) > 2 else None),
                        lon=(c[0] if len(c) > 0 else None),
                        lat=(c[1] if len(c) > 1 else None),
                    )
                )
            return pd.DataFrame(rows)
        except requests.RequestException:
            if attempt == RETRIES:
                raise
            time.sleep(min(2**attempt, 10))  # simple backoff


# -------------------------
# Landing one month (parquet + catalog row)
# -------------------------
def land_month(ms: dt.date):
    start_utc, month_end_utc = month_bounds_utc(ms)
    now_utc = dt.datetime.now(timezone.utc).replace(microsecond=0)

    is_current = (now_utc.year == ms.year and now_utc.month == ms.month)
    end_actual = now_utc if is_current else month_end_utc
    finalized = not is_current

    # Pre-mark as landing with intended coverage window
    catalog_upsert(
        ms,
        status="landing",
        rows=0,
        finalized=False,
        coverage_start_utc=start_utc,
        coverage_end_utc=end_actual,
        error=None,
    )

    df = fetch_range(start_utc, end_actual)

    outdir = os.path.join(LAKE, f"date={ms:%Y-%m}")
    os.makedirs(outdir, exist_ok=True)
    df.to_parquet(os.path.join(outdir, "part-00000.parquet"), index=False)

    catalog_upsert(
        ms,
        status="landed",
        rows=len(df),
        finalized=finalized,
        coverage_start_utc=start_utc,
        coverage_end_utc=end_actual,
        error=None,
    )
    print(f"✅ {ms:%Y-%m}: landed {len(df)} rows (finalized={finalized})")


# -------------------------
# Main autorun
# -------------------------
def main():
    if not BOOTSTRAP:
        print("EXTRACTOR_BOOTSTRAP=false → skip autorun.")
        return

    # Expect table to be created by db/init/01_data_catalog.sql
    # Fail fast if missing:
    try:
        with pg() as conn, conn.cursor() as cur:
            cur.execute("SELECT 1 FROM data_catalog LIMIT 1;")
    except Exception as e:
        raise RuntimeError(
            "data_catalog table not found. Did you mount db/init and start with a fresh volume?"
        ) from e

    with pg() as conn:
        if not try_lock(conn):
            print("Another extractor instance is running. Exiting.")
            return
        try:
            targets = list_target_months()
            now_utc = dt.datetime.now(timezone.utc)

            # Decide which months still need work
            todo: list[dt.date] = []
            for ms in targets:
                row = catalog_get(ms)
                is_current = (ms.year == now_utc.year and ms.month == now_utc.month)

                if row is None:
                    # never landed → do it
                    todo.append(ms)
                else:
                    status, finalized, _, cov_start, cov_end, _, _ = row
                    if status != "landed":
                        todo.append(ms)
                    elif (not finalized) and is_current:
                        # current month should be refreshed to "now"
                        todo.append(ms)
                    elif (not is_current) and (not finalized):
                        # past month but not finalized → (re)land to month end and finalize
                        todo.append(ms)
                    # else landed & finalized → nothing to do

            if not todo:
                print("All target months are already in good shape. Exiting.")
                return

            for i, ms in enumerate(todo, 1):
                try:
                    print(f"[{i}/{len(todo)}] Landing {ms:%Y-%m} …")
                    land_month(ms)
                except Exception as e:
                    # best-effort error upsert with last known coverage window
                    start_utc, end_utc = month_bounds_utc(ms)
                    catalog_upsert(
                        ms,
                        status="error",
                        rows=0,
                        finalized=False,
                        coverage_start_utc=start_utc,
                        coverage_end_utc=start_utc,  # minimal placeholder
                        error=str(e),
                    )
                    print(f"❌ {ms:%Y-%m}: {e}")
                time.sleep(SLEEP_S)
        finally:
            unlock(conn)


if __name__ == "__main__":
    main()
