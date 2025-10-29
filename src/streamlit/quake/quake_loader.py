# src/data/quake_loader.py
from datetime import datetime, timedelta
import requests
import pandas as pd
from sqlalchemy import text
from data.db import get_session

USGS_BASE = "https://earthquake.usgs.gov/fdsnws/event/1/query?format=geojson"

def fetch_usgs_batch(start: datetime, end: datetime) -> list[dict]:
    """Fetch earthquakes between start and end (inclusive). Split recursively on 400 errors."""
    params = {
        "starttime": start.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "endtime": end.strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    url = USGS_BASE
    try:
        resp = requests.get(url, params=params, timeout=60)
        if resp.status_code == 400:
            # Too many events — split in half recursively
            midpoint = start + (end - start) / 2
            left = fetch_usgs_batch(start, midpoint)
            right = fetch_usgs_batch(midpoint + timedelta(seconds=1), end)
            return left + right
        resp.raise_for_status()
        data = resp.json()
        feats = data.get("features", [])
        return feats
    except Exception as e:
        print(f"Error fetching {start} to {end}: {e}")
        return []

def load_into_db(records: list[dict]):
    """Insert GeoJSON features into quake table."""
    if not records:
        return 0

    rows = []
    for f in records:
        p = f.get("properties", {})
        g = f.get("geometry", {})
        coords = g.get("coordinates", [None, None, None])

        rows.append({
            "usgs_id": f.get("id"),
            "mag": p.get("mag"),
            "place": p.get("place"),
            "time_utc": datetime.utcfromtimestamp(p["time"]/1000.0) if p.get("time") else None,
            "updated_utc": datetime.utcfromtimestamp(p["updated"]/1000.0) if p.get("updated") else None,
            "url": p.get("url"),
            "detail_url": p.get("detail"),
            "tsunami": p.get("tsunami"),
            "sig": p.get("sig"),
            "mag_type": p.get("magType"),
            "typ": p.get("type"),
            "title": p.get("title"),
            "net": p.get("net"),
            "code": p.get("code"),
            "depth_km": coords[2],
            "lon": coords[0],
            "lat": coords[1],
        })

    with get_session() as session:
        session.execute(
            text("""
                INSERT INTO quake (
                    usgs_id, mag, place, time_utc, updated_utc, url, detail_url,
                    tsunami, sig, mag_type, typ, title, net, code,
                    depth_km, lon, lat, geom
                )
                VALUES (
                    :usgs_id, :mag, :place, :time_utc, :updated_utc, :url, :detail_url,
                    :tsunami, :sig, :mag_type, :typ, :title, :net, :code,
                    :depth_km, :lon, :lat,
                    ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)
                )
                ON CONFLICT (usgs_id) DO NOTHING
            """),
            rows,
        )
        session.commit()
    return len(rows)

def log_load(start: datetime, end: datetime, rows: int):
    with get_session() as session:
        session.execute(
            text("""
                INSERT INTO data_load_log (start_time_utc, end_time_utc, rows_inserted)
                VALUES (:start_time_utc, :end_time_utc, :rows_inserted)
            """),
            {"start_time_utc": start, "end_time_utc": end, "rows_inserted": rows},
        )
        session.commit()

def load_last_year():
    """Run initial load for last 12 months in monthly chunks."""
    end = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    start = end - timedelta(days=365)

    curr = start
    while curr < end:
        month_end = (curr + timedelta(days=32)).replace(day=1) - timedelta(seconds=1)
        print(f"Fetching {curr:%Y-%m-%d} to {month_end:%Y-%m-%d}")
        feats = fetch_usgs_batch(curr, month_end)
        rows = load_into_db(feats)
        log_load(curr, month_end, rows)
        print(f"Inserted {rows} rows")
        curr = month_end + timedelta(seconds=1)

def load_last_30_days():
    """
    Load quakes for the last 30 days in one request.
    If USGS returns 400 (too many events), fetch_usgs_batch()
    will recursively split into smaller ranges as needed.
    """
    end = datetime.utcnow().replace(microsecond=0)
    start = end - timedelta(days=30)

    print(f"Fetching {start:%Y-%m-%d %H:%M:%S} to {end:%Y-%m-%d %H:%M:%S}")
    feats = fetch_usgs_batch(start, end)
    rows = load_into_db(feats)
    log_load(start, end, rows)
    print(f"Inserted {rows} rows total for last 30 days")