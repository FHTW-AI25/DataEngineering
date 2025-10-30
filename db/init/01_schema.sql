-- Enable PostGIS (geometry types, spatial indexes, etc.)
CREATE EXTENSION IF NOT EXISTS postgis;

-- ============================================================================
-- Table: quake
-- Main earthquake event table (USGS-like feed)
-- ============================================================================

CREATE TABLE IF NOT EXISTS quake (
    id            bigserial PRIMARY KEY,
    usgs_id       text UNIQUE,
    mag           numeric,
    place         text,
    time_utc      timestamptz,
    updated_utc   timestamptz,
    url           text,
    detail_url    text,
    tsunami       smallint,
    sig           integer,
    mag_type      text,
    typ           text,
    title         text,
    net           text,
    code          text,
    depth_km      numeric,
    lon           double precision,
    lat           double precision,
    geom          geometry(Point, 4326)
);

CREATE INDEX IF NOT EXISTS quake_time_idx ON quake (time_utc DESC);
CREATE INDEX IF NOT EXISTS quake_mag_idx  ON quake (mag);
CREATE INDEX IF NOT EXISTS quake_geom_gix ON quake USING GIST (geom);

-- ============================================================================
-- Table: country
-- Countries, keyed by ISO3 code
-- (filled later by CountrySeaManager.fill_country) :contentReference[oaicite:3]{index=3}
-- ============================================================================

CREATE TABLE IF NOT EXISTS country (
    iso   TEXT PRIMARY KEY,      -- ISO3 code
    name  TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS country_name_idx ON country (name);

-- ============================================================================
-- Table: sea
-- Sea / waterbody lookup
-- (filled later by CountrySeaManager.fill_sea) :contentReference[oaicite:4]{index=4}
-- ============================================================================

CREATE TABLE IF NOT EXISTS sea (
    id    INTEGER PRIMARY KEY,   -- small stable ID like 0..9
    name  TEXT NOT NULL UNIQUE
);

CREATE INDEX IF NOT EXISTS sea_name_idx ON sea (name);

-- ============================================================================
-- Table: location
-- One row per quake, attaching geopolitical context:
-- - which country (if on land)
-- - which sea (if offshore)
-- Filled later by LocationManager.upsert_locations_for_quakes / ...for_all_quakes
-- :contentReference[oaicite:5]{index=5}
-- ============================================================================

CREATE TABLE IF NOT EXISTS location (
    quake_id     BIGINT PRIMARY KEY,  -- 1:1 with quake.id

    country_iso  TEXT,                -- FK to country.iso (nullable)
    sea_id       INTEGER              -- FK to sea.id (nullable)
);

-- Add foreign keys for data integrity (optional but recommended)
ALTER TABLE location
    ADD CONSTRAINT location_quake_fk
    FOREIGN KEY (quake_id)
    REFERENCES quake (id)
    ON DELETE CASCADE;

ALTER TABLE location
    ADD CONSTRAINT location_country_fk
    FOREIGN KEY (country_iso)
    REFERENCES country (iso)
    ON DELETE SET NULL;

ALTER TABLE location
    ADD CONSTRAINT location_sea_fk
    FOREIGN KEY (sea_id)
    REFERENCES sea (id)
    ON DELETE SET NULL;

-- Helpful index for joining/filtering by country or sea
CREATE INDEX IF NOT EXISTS location_country_idx ON location (country_iso);
CREATE INDEX IF NOT EXISTS location_sea_idx     ON location (sea_id);

-- Tracks what data ranges have been loaded
CREATE TABLE IF NOT EXISTS data_load_log (
    id SERIAL PRIMARY KEY,
    start_time_utc TIMESTAMPTZ NOT NULL,
    end_time_utc   TIMESTAMPTZ NOT NULL,
    rows_inserted  INTEGER,
    status         TEXT DEFAULT 'success',  -- success, partial, error
    created_at     TIMESTAMPTZ DEFAULT NOW()
);

-- Simple index to check latest coverage
CREATE INDEX IF NOT EXISTS data_load_log_start_idx ON data_load_log(start_time_utc);
CREATE INDEX IF NOT EXISTS data_load_log_end_idx   ON data_load_log(end_time_utc);

-- Drop & recreate to ensure a clean schema (DESTRUCTIVE)
DROP TABLE IF EXISTS data_catalog CASCADE;

-- Tracks landed coverage per calendar month for the USGS extractor.
-- One row per month_start (UTC, first day of month).
CREATE TABLE data_catalog (
  -- Partition key
  month_start          date PRIMARY KEY,

  -- Landing lifecycle
  status               text NOT NULL
                       CHECK (status IN ('landing','landed','error')),

  -- Coverage window actually landed (UTC).
  -- Must be within the same calendar month as month_start.
  coverage_start_utc   timestamptz NOT NULL,
  coverage_end_utc     timestamptz NOT NULL,
  CHECK (coverage_start_utc <= coverage_end_utc),
  CHECK (date_trunc('month', coverage_start_utc) = month_start::timestamp),
  CHECK (date_trunc('month', coverage_end_utc)   = month_start::timestamp),

  -- Whether month is fully complete (landed through last day 23:59:59 UTC)
  finalized            boolean NOT NULL DEFAULT false,

  -- Row count landed for this month (for observability)
  rows                 integer NOT NULL DEFAULT 0
                       CHECK (rows >= 0),

  -- Telemetry
  error                text,
  updated_at           timestamptz NOT NULL DEFAULT now()
);

-- Helpful indexes
-- Quick lookups for “work to do” and recent activity.
CREATE INDEX data_catalog_status_idx    ON data_catalog (status);
CREATE INDEX data_catalog_finalized_idx ON data_catalog (finalized);
CREATE INDEX data_catalog_updated_idx   ON data_catalog (updated_at DESC);

-- Optional: a simple view to see completeness at a glance
CREATE OR REPLACE VIEW v_data_catalog_health AS
SELECT
  month_start,
  status,
  finalized,
  rows,
  coverage_start_utc,
  coverage_end_utc,
  (date_trunc('month', (coverage_end_utc + interval '1 second'))
     = (month_start + interval '1 month')) AS covers_full_month,  -- true if end == last second of month
  updated_at,
  error
FROM data_catalog;

-- Optional: comments for psql \d+
COMMENT ON TABLE data_catalog IS
  'Landing catalog for monthly quake data (one row per month). Tracks status, coverage window, and completeness.';
COMMENT ON COLUMN data_catalog.month_start IS 'UTC month key (first day of month).';
COMMENT ON COLUMN data_catalog.status IS 'landing | landed | error';
COMMENT ON COLUMN data_catalog.coverage_start_utc IS 'UTC start timestamp actually landed (must be within month_start month).';
COMMENT ON COLUMN data_catalog.coverage_end_utc IS 'UTC end timestamp actually landed (must be within month_start month).';
COMMENT ON COLUMN data_catalog.finalized IS 'True when month is fully landed to last second of the month.';
COMMENT ON COLUMN data_catalog.rows IS 'Number of records landed for this month.';
