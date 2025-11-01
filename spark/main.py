from __future__ import annotations
from pathlib import Path
from typing import List, Tuple
from datetime import datetime
import os
from urllib.parse import urlparse

from pyspark.sql import SparkSession, functions as F, types as T
from sqlalchemy import text, bindparam

# shared DB helper
from earthquakes_common import get_session
# spark-only loaders that still use shared DB
from app.geo.country_sea_manager import CountrySeaManager
from app.location.location_manager import LocationManager


# -----------------------------------------------------------------------------
# Config
# -----------------------------------------------------------------------------
DATA_DIR = Path("/data/usgs_earthquakes")
STAGING_TABLE = "stg_quake"  # created automatically by Spark write (mode=append)
POSTGRES_JDBC_JAR = "/opt/jars/postgresql.jar"

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


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------
def _to_jdbc_url(db_url: str) -> tuple[str, dict]:
    """Convert DATABASE_URL (postgresql://user:pass@host:5432/db) to Spark JDBC url & props."""
    u = urlparse(db_url)
    jdbc = f"jdbc:postgresql://{u.hostname}:{u.port or 5432}{u.path}"
    props = {
        "user": u.username or "",
        "password": u.password or "",
        "driver": "org.postgresql.Driver",
        "stringtype": "unspecified",
    }
    return jdbc, props


def create_spark() -> SparkSession:
    """Create a Spark session with the Postgres JDBC jar on driver & executors."""
    spark = (
        SparkSession.builder
        .appName("EarthquakesTransform")
        .config("spark.jars", POSTGRES_JDBC_JAR)
        .config("spark.driver.extraClassPath", POSTGRES_JDBC_JAR)
        .config("spark.executor.extraClassPath", POSTGRES_JDBC_JAR)
        .getOrCreate()
    )
    print("🚀 Spark started:", spark.version)
    return spark


def months_to_process() -> list[tuple[str, datetime]]:
    """
    Return months [(ym, month_start)] in status='loaded' that have their parquet present.
    """
    with get_session() as s:
        rows = s.execute(text("""
            SELECT to_char(month_start AT TIME ZONE 'UTC', 'YYYY-MM') AS ym,
                   month_start
            FROM monthly_loads
            WHERE status = 'loaded'
            ORDER BY month_start
        """)).all()
    out: list[tuple[str, datetime]] = []
    for r in rows:
        ym = r.ym
        path = DATA_DIR / ym / f"{ym}.parquet"
        if path.exists():
            out.append((ym, r.month_start))
        else:
            print(f"⚠️  Skipping {ym}: missing {path}")
    return out


def build_quake_df(spark: SparkSession, months: list[tuple[str, datetime]]):
    """Read monthly parquet, parse GeoJSON Feature, project to target quake columns."""
    paths = [str(DATA_DIR / ym / f"{ym}.parquet") for ym, _ in months]
    raw = spark.read.parquet(*paths)  # json column
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
    return df


def write_staging(df, spark: SparkSession):
    """Parallel JDBC write → staging table."""
    jdbc_url, jdbc_props = _to_jdbc_url(os.environ["DATABASE_URL"])
    target_partitions = max(8, spark.sparkContext.defaultParallelism)
    (
        df.repartition(target_partitions)
          .write
          .format("jdbc")
          .option("url", jdbc_url)
          .option("dbtable", STAGING_TABLE)
          .option("batchsize", 5000)
          .option("isolationLevel", "READ_COMMITTED")
          .options(**jdbc_props)
          .mode("append")
          .save()
    )
    print(f"🧾 Wrote {STAGING_TABLE} via JDBC (parallel).")


def merge_and_truncate():
    """Server-side MERGE from staging → quake, then TRUNCATE staging."""
    with get_session() as s:
        s.execute(MERGE_SQL)
        s.execute(TRUNCATE_STAGING)
        s.commit()
    print("🔀 MERGE done; staging truncated.")


def fetch_month_bounds(month_starts: list[datetime]) -> dict[datetime, datetime]:
    """Return {month_start -> month_end} for the given month_starts."""
    if not month_starts:
        return {}
    stmt = (
        text("""
            SELECT month_start, month_end
            FROM monthly_loads
            WHERE month_start IN :arr
        """).bindparams(bindparam("arr", expanding=True))
    )
    with get_session() as s:
        rows = s.execute(stmt, {"arr": month_starts}).fetchall()
    return {r.month_start: r.month_end for r in rows}


def update_locations_for_months(months: list[tuple[str, datetime]], month_bounds: dict[datetime, datetime]) -> int:
    """Resolve & upsert locations per processed month; returns total upserts."""
    loc_mgr = LocationManager()
    total = 0
    for _, mstart in months:
        mend_inclusive = month_bounds.get(mstart)
        if mend_inclusive is None:
            continue
        up = loc_mgr.upsert_locations_for_month(mstart, mend_inclusive)
        total += up
        print(f"🌍 Locations upserted for {mstart.date()}: {up}")
    print(f"🌍 Total locations upserted this run: {total}")
    return total


def mark_transformed(month_starts: list[datetime]) -> None:
    """Flip monthly_loads.status to 'transformed' for processed months."""
    if not month_starts:
        return
    stmt = (
        text("""
            UPDATE monthly_loads
               SET status = 'transformed', updated_at = NOW()
             WHERE month_start IN :arr
        """).bindparams(bindparam("arr", expanding=True))
    )
    with get_session() as s:
        s.execute(stmt, {"arr": month_starts})
        s.commit()
    print(f"🏁 Marked {len(month_starts)} month(s) as transformed.")


# -----------------------------------------------------------------------------
# Orchestration
# -----------------------------------------------------------------------------
def main():
    # Step 0) Transform-setup: load lookup tables (country, sea)
    c, s = CountrySeaManager().fill_all()
    print(f"✅ Lookups loaded: countries={c}, seas={s}")

    # Step 1) Start Spark
    spark = create_spark()

    # Step 2) Determine months to process (status='loaded' & parquet present)
    months = months_to_process()
    if not months:
        print("ℹ️ No months to process.")
        spark.stop()
        return

    # Step 3) Build normalized DataFrame
    df = build_quake_df(spark, months)

    # Step 4) Write to staging via JDBC (parallel)
    write_staging(df, spark)

    # Step 5) Server-side MERGE → quake; TRUNCATE staging
    merge_and_truncate()

    # Step 6) Update locations per processed month
    month_starts = [ms for _, ms in months]
    bounds = fetch_month_bounds(month_starts)
    update_locations_for_months(months, bounds)

    # Step 7) Mark months as transformed
    mark_transformed(month_starts)

    # Done
    spark.stop()
    print("🎉 Transform complete.")


if __name__ == "__main__":
    main()
