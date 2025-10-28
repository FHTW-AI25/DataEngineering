-- Enable PostGIS (geometry types, spatial indexes, etc.)
CREATE EXTENSION IF NOT EXISTS postgis;

-- ============================================================================
-- Table: quake
-- Main earthquake event table (USGS-like feed)
-- ============================================================================

CREATE TABLE IF NOT EXISTS quake (
    id            BIGSERIAL PRIMARY KEY,
    -- original USGS (or other feed) ID
    usgs_id       TEXT,

    -- core event attributes
    mag           NUMERIC,
    place         TEXT,
    time_utc      TIMESTAMPTZ,
    updated_utc   TIMESTAMPTZ,
    url           TEXT,
    detail_url    TEXT,

    tsunami       SMALLINT,     -- 0 or 1
    sig           INTEGER,      -- "significance" score
    mag_type      TEXT,
    typ           TEXT,
    title         TEXT,
    net           TEXT,
    code          TEXT,

    depth_km      NUMERIC,
    lon           DOUBLE PRECISION,
    lat           DOUBLE PRECISION,

    -- PostGIS geometry point in EPSG:4326 (lon/lat)
    geom          geometry(Point, 4326)
);

-- Helpful indexes for queries / filters
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
