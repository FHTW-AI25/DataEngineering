-- Enable PostGIS
CREATE EXTENSION IF NOT EXISTS postgis;

-- Take a look at: https://earthquake.usgs.gov/earthquakes/feed/v1.0/geojson.php

-- Core table for USGS quakes
CREATE TABLE IF NOT EXISTS quake (
    id            bigserial PRIMARY KEY,
    -- earthquake id, maybe save as well
    usgs_id       text,
    -- starting feature properties
    mag           numeric,
    place         text,
    time_utc      timestamptz,
    updated_utc   timestamptz,
    url           text,
    detail_url    text,
    -- 0 - 1
    tsunami       smallint,
    -- significants level [0 - 1000]
    sig           integer,
    -- maybe not needed
    mag_type      text,
    -- type maybe also not needed
    typ           text,
    title         text,
    -- also not needed
    net           text,
    -- also not needed
    code          text,
    -- typically [0 - 1000]
    depth_km      numeric,
    lon           double precision,
    lat           double precision,
    geom          geometry(Point, 4326)
    );

-- some useful indexes
CREATE INDEX IF NOT EXISTS quake_time_idx ON quake (time_utc DESC);
CREATE INDEX IF NOT EXISTS quake_mag_idx  ON quake (mag);
CREATE INDEX IF NOT EXISTS quake_geom_gix ON quake USING GIST (geom);


-- ──────────────────────────────────────────────────────────────────────────────
-- Dummy seed data for quake (UTC timestamps, diverse locations/mags)
-- Paste below your CREATE TABLE / INDEX statements in init.sql
-- ──────────────────────────────────────────────────────────────────────────────

INSERT INTO quake (
    usgs_id, mag, place, time_utc, updated_utc, url, detail_url,
    tsunami, sig, mag_type, typ, title, net, code,
    depth_km, lon, lat, geom
) VALUES
-- 1) Alaska
('ak-20250929-001', 4.6, '120 km W of Homer, Alaska', '2025-09-29 03:14:22+00', '2025-09-29 03:20:00+00',
 'https://example.usgs.gov/event/ak-20250929-001', 'https://example.usgs.gov/detail/ak-20250929-001',
 0, 326, 'ml', 'earthquake', 'M4.6 - 120 km W of Homer, Alaska', 'ak', '20250929-001',
 55.3, -153.10, 59.63, ST_SetSRID(ST_MakePoint(-153.10, 59.63), 4326)),

-- 2) Japan trench
('us-20250928-abc', 6.1, 'Off the east coast of Honshu, Japan', '2025-09-28 18:42:10+00', '2025-09-28 18:55:30+00',
 'https://example.usgs.gov/event/us-20250928-abc', 'https://example.usgs.gov/detail/us-20250928-abc',
 1, 572, 'mw', 'earthquake', 'M6.1 - Off the east coast of Honshu, Japan', 'us', 'abc',
 24.8, 142.37, 38.21, ST_SetSRID(ST_MakePoint(142.37, 38.21), 4326)),

-- 3) Chile
('us-20250927-chl', 5.3, 'Near the coast of central Chile', '2025-09-27 09:05:00+00', '2025-09-27 09:07:45+00',
 'https://example.usgs.gov/event/us-20250927-chl', 'https://example.usgs.gov/detail/us-20250927-chl',
 0, 433, 'mw', 'earthquake', 'M5.3 - Near the coast of central Chile', 'us', 'chl',
 18.2, -72.45, -35.21, ST_SetSRID(ST_MakePoint(-72.45, -35.21), 4326)),

-- 4) California
('ci-20250926-xyz', 3.7, '10 km NE of Ridgecrest, California', '2025-09-26 14:12:33+00', '2025-09-26 14:20:10+00',
 'https://example.usgs.gov/event/ci-20250926-xyz', 'https://example.usgs.gov/detail/ci-20250926-xyz',
 0, 211, 'ml', 'earthquake', 'M3.7 - 10 km NE of Ridgecrest, CA', 'ci', 'xyz',
 8.6, -117.55, 35.73, ST_SetSRID(ST_MakePoint(-117.55, 35.73), 4326)),

-- 5) Greece
('eu-20250925-gr', 4.9, 'Dodecanese Islands, Greece', '2025-09-25 06:50:11+00', '2025-09-25 06:58:00+00',
 'https://example.usgs.gov/event/eu-20250925-gr', 'https://example.usgs.gov/detail/eu-20250925-gr',
 0, 362, 'mb', 'earthquake', 'M4.9 - Dodecanese Islands, Greece', 'eu', 'gr',
 12.4, 27.43, 36.65, ST_SetSRID(ST_MakePoint(27.43, 36.65), 4326)),

-- 6) Indonesia
('us-20250924-id', 5.8, 'Banda Sea, Indonesia', '2025-09-24 22:29:47+00', '2025-09-24 22:40:02+00',
 'https://example.usgs.gov/event/us-20250924-id', 'https://example.usgs.gov/detail/us-20250924-id',
 0, 508, 'mw', 'earthquake', 'M5.8 - Banda Sea, Indonesia', 'us', 'id',
 150.0, 129.25, -6.43, ST_SetSRID(ST_MakePoint(129.25, -6.43), 4326)),

-- 7) New Zealand
('us-20250923-nz', 4.5, 'South Island, New Zealand', '2025-09-23 11:05:13+00', '2025-09-23 11:15:20+00',
 'https://example.usgs.gov/event/us-20250923-nz', 'https://example.usgs.gov/detail/us-20250923-nz',
 0, 318, 'ml', 'earthquake', 'M4.5 - South Island, New Zealand', 'us', 'nz',
 10.2, 170.50, -43.53, ST_SetSRID(ST_MakePoint(170.50, -43.53), 4326)),

-- 8) Iceland
('is-20250922-ic', 3.9, 'Reykjanes Peninsula, Iceland', '2025-09-22 02:44:59+00', '2025-09-22 02:50:00+00',
 'https://example.usgs.gov/event/is-20250922-ic', 'https://example.usgs.gov/detail/is-20250922-ic',
 0, 247, 'ml', 'earthquake', 'M3.9 - Reykjanes Peninsula, Iceland', 'is', 'ic',
 6.8, -22.18, 63.90, ST_SetSRID(ST_MakePoint(-22.18, 63.90), 4326)),

-- 9) Türkiye
('eu-20250921-tr', 5.1, 'Eastern Türkiye', '2025-09-21 19:30:42+00', '2025-09-21 19:38:05+00',
 'https://example.usgs.gov/event/eu-20250921-tr', 'https://example.usgs.gov/detail/eu-20250921-tr',
 0, 401, 'mb', 'earthquake', 'M5.1 - Eastern Türkiye', 'eu', 'tr',
 22.5, 41.15, 39.10, ST_SetSRID(ST_MakePoint(41.15, 39.10), 4326)),

-- 10) Philippines (tsunami=1)
('us-20250920-ph', 6.4, 'Mindanao, Philippines', '2025-09-20 05:12:00+00', '2025-09-20 05:25:40+00',
 'https://example.usgs.gov/event/us-20250920-ph', 'https://example.usgs.gov/detail/us-20250920-ph',
 1, 611, 'mw', 'earthquake', 'M6.4 - Mindanao, Philippines', 'us', 'ph',
 35.7, 126.60, 7.30, ST_SetSRID(ST_MakePoint(126.60, 7.30), 4326));