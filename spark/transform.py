from __future__ import annotations
import os
from pathlib import Path

from pyspark.sql import SparkSession, functions as F, types as T
from sqlalchemy import text

# shared package (baked into images)
from earthquakes_common import get_session

DATA_DIR = Path("/data/usgs_earthquakes")

# GeoJSON Feature schema for USGS feed
FEATURE_SCHEMA = T.StructType([
    T.StructField("type", T.StringType()),
    T.StructField("properties", T.StructType([
        T.StructField("mag", T.DoubleType()),
        T.StructField("place", T.StringType()),
        T.StructField("time", T.LongType()),
        T.StructField("updated", T.LongType()),
        T.StructField("tz", T.StringType()),
        T.StructField("url", T.StringType()),
        T.StructField("detail", T.StringType()),
        T.StructField("felt", T.IntegerType()),
        T.StructField("cdi", T.DoubleType()),
        T.StructField("mmi", T.DoubleType()),
        T.StructField("alert", T.StringType()),
        T.StructField("status", T.StringType()),
        T.StructField("tsunami", T.IntegerType()),
        T.StructField("sig", T.IntegerType()),
        T.StructField("net", T.StringType()),
        T.StructField("code", T.StringType()),
        T.StructField("ids", T.StringType()),
        T.StructField("sources", T.StringType()),
        T.StructField("types", T.StringType()),
        T.StructField("nst", T.IntegerType()),
        T.StructField("dmin", T.DoubleType()),
        T.StructField("rms", T.DoubleType()),
        T.StructField("gap", T.DoubleType()),
        T.StructField("magType", T.StringType()),
        T.StructField("type", T.StringType()),
        T.StructField("title", T.StringType()),
    ])),
    T.StructField("geometry", T.StructType([
        T.StructField("type", T.StringType()),
        T.StructField("coordinates", T.ArrayType(T.DoubleType())),
    ])),
    T.StructField("id", T.StringType()),
])

def months_to_process():
    """Return list of (year_month, month_start, month_end) with status='loaded'."""
    sql = text("""
        SELECT to_char(month_start AT TIME ZONE 'UTC', 'YYYY-MM') AS ym,
               month_start, month_end
          FROM monthly_loads
         WHERE status = 'loaded'
         ORDER BY month_start
    """)
    with get_session() as s:
        rows = s.execute(sql).all()
    return [(r.ym, r.month_start, r.month_end) for r in rows]

def load_month_df(spark: SparkSession, ym: str):
    """Read the monthly parquet with the 'json' column and parse Features."""
    path = DATA_DIR / ym / f"{ym}.parquet"
    if not path.exists():
        print(f"⚠️  Missing parquet for {ym}: {path}")
        return None

    raw = spark.read.parquet(str(path))  # column: json (string)
    parsed = raw.select(F.from_json("json", FEATURE_SCHEMA).alias("f")).select("f.*")

    # Map GeoJSON → quake columns
    df = parsed.select(
        F.col("id").alias("usgs_id"),
        F.col("properties.mag").alias("mag"),
        F.col("properties.place").alias("place"),
        # millis → seconds → timestamp
        F.to_timestamp((F.col("properties.time") / F.lit(1000)).cast("double")).alias("time_utc"),
        F.to_timestamp((F.col("properties.updated") / F.lit(1000)).cast("double")).alias("updated_utc"),
        F.col("properties.url").alias("url"),
        F.col("properties.detail").alias("detail_url"),
        F.col("properties.tsunami").alias("tsunami"),
        F.col("properties.sig").alias("sig"),
        F.col("properties.magType").alias("mag_type"),
        F.col("properties.type").alias("typ"),
        F.col("properties.title").alias("title"),
        F.col("properties.net").alias("net"),
        F.col("properties.code").alias("code"),
        F.col("geometry.coordinates").getItem(2).alias("depth_km"),
        F.col("geometry.coordinates").getItem(0).alias("lon"),
        F.col("geometry.coordinates").getItem(1).alias("lat"),
    )
    # (Optional) drop null usgs_id rows defensively
    df = df.filter(F.col("usgs_id").isNotNull())
    return df

def upsert_quakes(rows: list[dict]):
    """
    Bulk upsert into quake by usgs_id.
    Uses PostGIS for geometry from lon/lat; skips rows with null lon/lat.
    """
    if not rows:
        return

    sql = text("""
        INSERT INTO quake (
            usgs_id, mag, place, time_utc, updated_utc, url, detail_url,
            tsunami, sig, mag_type, typ, title, net, code, depth_km, lon, lat, geom
        )
        VALUES (
            :usgs_id, :mag, :place, :time_utc, :updated_utc, :url, :detail_url,
            :tsunami, :sig, :mag_type, :typ, :title, :net, :code, :depth_km, :lon, :lat,
            CASE
              WHEN :lon IS NOT NULL AND :lat IS NOT NULL
              THEN ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)
              ELSE NULL
            END
        )
        ON CONFLICT (usgs_id) DO UPDATE SET
            mag = EXCLUDED.mag,
            place = EXCLUDED.place,
            time_utc = EXCLUDED.time_utc,
            updated_utc = EXCLUDED.updated_utc,
            url = EXCLUDED.url,
            detail_url = EXCLUDED.detail_url,
            tsunami = EXCLUDED.tsunami,
            sig = EXCLUDED.sig,
            mag_type = EXCLUDED.mag_type,
            typ = EXCLUDED.typ,
            title = EXCLUDED.title,
            net = EXCLUDED.net,
            code = EXCLUDED.code,
            depth_km = EXCLUDED.depth_km,
            lon = EXCLUDED.lon,
            lat = EXCLUDED.lat,
            geom = EXCLUDED.geom;
    """)
    with get_session() as s:
        s.execute(sql, params=rows)  # executemany when list of dicts
        s.commit()

def mark_month_transformed(month_start):
    sql = text("""
        UPDATE monthly_loads
           SET status = 'transformed', updated_at = NOW()
         WHERE month_start = :ms
    """)
    with get_session() as s:
        s.execute(sql, {"ms": month_start})
        s.commit()

def main():
    spark = SparkSession.builder.appName("EarthquakesTransform").getOrCreate()
    print("🚀 Spark started:", spark.version)

    months = months_to_process()
    if not months:
        print("ℹ️ No months in status='loaded'. Nothing to do.")
        spark.stop()
        return

    for ym, mstart, _mend in months:
        print(f"🔎 Processing month {ym}")
        df = load_month_df(spark, ym)
        if df is None:
            print(f"⚠️ Skipping {ym}, parquet not found.")
            continue

        # Convert Spark rows → list[dict] in manageable chunks to avoid huge collects
        batch_size = 5000
        total = 0
        buffer: list[dict] = []

        for row in df.toLocalIterator():  # streams rows from executors to driver
            rec = {
                "usgs_id": row["usgs_id"],
                "mag": row["mag"],
                "place": row["place"],
                "time_utc": row["time_utc"],
                "updated_utc": row["updated_utc"],
                "url": row["url"],
                "detail_url": row["detail_url"],
                "tsunami": row["tsunami"],
                "sig": row["sig"],
                "mag_type": row["mag_type"],
                "typ": row["typ"],
                "title": row["title"],
                "net": row["net"],
                "code": row["code"],
                "depth_km": row["depth_km"],
                "lon": row["lon"],
                "lat": row["lat"],
            }
            buffer.append(rec)
            if len(buffer) >= batch_size:
                upsert_quakes(buffer)
                total += len(buffer)
                buffer.clear()

        if buffer:
            upsert_quakes(buffer)
            total += len(buffer)

        print(f"✅ {ym}: upserted {total} rows into quake")
        # Mark transformed
        mark_month_transformed(mstart)

    spark.stop()
    print("🎉 Transform complete.")

if __name__ == "__main__":
    main()
