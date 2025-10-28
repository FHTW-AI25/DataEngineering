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