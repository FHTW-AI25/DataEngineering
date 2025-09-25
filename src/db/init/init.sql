-- Enable PostGIS
CREATE EXTENSION IF NOT EXISTS postgis;

-- Take a look at: https://earthquake.usgs.gov/earthquakes/feed/v1.0/geojson.php

-- Core table for USGS quakes
CREATE TABLE IF NOT EXISTS usgs_quakes (
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
CREATE INDEX IF NOT EXISTS usgs_quakes_time_idx ON usgs_quakes (time_utc DESC);
CREATE INDEX IF NOT EXISTS usgs_quakes_mag_idx  ON usgs_quakes (mag);
CREATE INDEX IF NOT EXISTS usgs_quakes_geom_gix ON usgs_quakes USING GIST (geom);