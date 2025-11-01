from __future__ import annotations
from pathlib import Path
from typing import List, Tuple
import os
from urllib.parse import urlparse

from pyspark.sql import SparkSession, functions as F, types as T
from sqlalchemy import text, bindparam

# shared DB helper
from earthquakes_common import get_session
# spark-only loaders that still use shared DB
from app.geo.country_sea_manager import CountrySeaManager

DATA_DIR = Path("/data/usgs_earthquakes")
STAGING_TABLE = "stg_quake"  # created automatically by Spark write (mode=append)

# GeoJSON Feature schema (USGS)
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

MERGE_SQL = text("""
MERGE INTO quake AS q
USING (
  SELECT
    usgs_id, mag, place, time_utc, updated_utc, url, detail_url, tsunami, sig,
    mag_type, typ, title, net, code, depth_km, lon, lat
  FROM stg_quake
) AS s
ON (q.usgs_id = s.usgs_id)
WHEN MATCHED THEN UPDATE SET
  mag = s.mag,
  place = s.place,
  time_utc = s.time_utc,
  updated_utc = s.updated_utc,
  url = s.url,
  detail_url = s.detail_url,
  tsunami = s.tsunami,
  sig = s.sig,
  mag_type = s.mag_type,
  typ = s.typ,
  title = s.title,
  net = s.net,
  code = s.code,
  depth_km = s.depth_km,
  lon = s.lon,
  lat = s.lat,
  geom = CASE
           WHEN s.lon IS NOT NULL AND s.lat IS NOT NULL
             THEN ST_SetSRID(ST_MakePoint(s.lon, s.lat), 4326)
           ELSE NULL
         END
WHEN NOT MATCHED THEN INSERT (
  usgs_id, mag, place, time_utc, updated_utc, url, detail_url, tsunami, sig,
  mag_type, typ, title, net, code, depth_km, lon, lat, geom
) VALUES (
  s.usgs_id, s.mag, s.place, s.time_utc, s.updated_utc, s.url, s.detail_url, s.tsunami, s.sig,
  s.mag_type, s.typ, s.title, s.net, s.code, s.depth_km, s.lon, s.lat,
  CASE
    WHEN s.lon IS NOT NULL AND s.lat IS NOT NULL
      THEN ST_SetSRID(ST_MakePoint(s.lon, s.lat), 4326)
    ELSE NULL
  END
);
""")

TRUNCATE_STAGING = text("TRUNCATE TABLE stg_quake;")

def _to_jdbc_url(db_url: str) -> tuple[str, dict]:
    """
    Convert DATABASE_URL (postgresql://user:pass@host:5432/db) to Spark JDBC url & props.
    """
    u = urlparse(db_url)
    jdbc = f"jdbc:postgresql://{u.hostname}:{u.port or 5432}{u.path}"
    props = {
        "user": u.username or "",
        "password": u.password or "",
        "driver": "org.postgresql.Driver",
        "stringtype": "unspecified",  # helps with text/varchar coercion
    }
    return jdbc, props

def months_to_process() -> list[tuple[str, "datetime"]]:
    with get_session() as s:
        rows = s.execute(text("""
            SELECT to_char(month_start AT TIME ZONE 'UTC', 'YYYY-MM') AS ym,
                   month_start
            FROM monthly_loads
            WHERE status = 'loaded'
            ORDER BY month_start
        """)).all()
    out = []
    for r in rows:
        ym = r.ym
        path = DATA_DIR / ym / f"{ym}.parquet"
        if path.exists():
            out.append((ym, r.month_start))   # <- keep as datetime, not ISO string
        else:
            print(f"⚠️  Skipping {ym}: missing {path}")
    return out

def mark_transformed(month_starts: list["datetime"]) -> None:
    if not month_starts:
        return
    stmt = (
        text("""
            UPDATE monthly_loads
               SET status = 'transformed', updated_at = NOW()
             WHERE month_start IN :arr
        """)
        .bindparams(bindparam("arr", expanding=True))   # <- expanding list
    )
    with get_session() as s:
        s.execute(stmt, {"arr": month_starts})
        s.commit()

def main():
    # 0) Fill reference lookups first (transform step)
    c, s = CountrySeaManager().fill_all()
    print(f"✅ Lookups loaded: countries={c}, seas={s}")

    # 1) Spark session (JDBC driver jar path is set via spark.jars)
    spark = (
        SparkSession.builder
        .appName("EarthquakesTransform")
        .config("spark.jars", "/opt/jars/postgresql.jar")
        .config("spark.driver.extraClassPath", "/opt/jars/postgresql.jar")
        .config("spark.executor.extraClassPath", "/opt/jars/postgresql.jar")
        .getOrCreate()
    )
    print("🚀 Spark started:", spark.version)

    # 2) Decide which months to process
    months = months_to_process()
    if not months:
        print("ℹ️ No months in status='loaded' with parquet present.")
        spark.stop()
        return

    # 3) Read ALL monthly parquet files in parallel
    paths = [str(DATA_DIR / ym / f"{ym}.parquet") for ym, _ in months]
    raw = spark.read.parquet(*paths)  # column: json (string)
    # Parse GeoJSON → structured cols
    parsed = raw.select(F.from_json("json", FEATURE_SCHEMA).alias("f")).select("f.*")
    df = parsed.select(
        F.col("id").alias("usgs_id"),
        F.col("properties.mag").alias("mag"),
        F.col("properties.place").alias("place"),
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
    ).filter(F.col("usgs_id").isNotNull())

    # 4) Parallel JDBC write to a staging table
    db_url = os.environ["DATABASE_URL"]
    jdbc_url, jdbc_props = _to_jdbc_url(db_url)

    target_partitions = max(8, spark.sparkContext.defaultParallelism)
    (
        df.repartition(target_partitions)
        .write
        .format("jdbc")
        .option("url", jdbc_url)
        .option("dbtable", STAGING_TABLE)
        .option("batchsize", 5000)
        .option("isolationLevel", "READ_COMMITTED")
        .options(**jdbc_props)  # <-- add this (user, password, driver, stringtype)
        .mode("append")
        .save()
    )
    print(f"🧾 Wrote {STAGING_TABLE} via JDBC (parallel).")

    # 5) Server-side MERGE into quake + TRUNCATE staging
    with get_session() as s:
        s.execute(MERGE_SQL)
        s.execute(TRUNCATE_STAGING)
        s.commit()
    print("🔀 MERGE done; staging truncated.")

    # 6) Mark all processed months as transformed
    month_starts = [ms for _, ms in months]  # these are datetime objects
    mark_transformed(month_starts)
    print(f"🏁 Marked {len(month_starts)} month(s) as transformed.")

    spark.stop()
    print("🎉 Transform complete.")

if __name__ == "__main__":
    main()
