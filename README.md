# Earthquake Data Engineering Pipeline

Team: Nittmann Alexander, Storck Benjamin, Wahl Sebastian & Wirawan Cahya
Course: Data Engineering
Date: 2025-01-05 

## Abstract / Executive Summary

This project implements a comprehensive earthquake data engineering pipeline that extracts, transforms, and visualizes global seismic events from the USGS (United States Geological Survey) API. The solution uses a containerized 3-stage architecture (extraction → transformation → storage or ETL) with Apache Spark for data transformation and PostGIS for geospatial analysis. The pipeline processes monthly earthquake data, enriches it with geographic context (countries and seas), and provides an interactive Streamlit web interface for visualization and analysis.

## Problem Statement

Seismologists, emergency response teams, and researchers need easy access to historical earthquake data with geographic context to analyze patterns, identify high-risk zones, and understand seismic activity trends. Raw earthquake data from USGS lacks geographic enrichment (country/sea associations) and requires technical expertise to query and visualize effectively.

**User Stories:**
- As a user I can see when the last earthquake was within xxx km of the place yyy, so that I am up-to-date about the latest earthquake.
- As a user I can see a heatmap of earthquake frequencies across the world in the last 24 hours / 365 days, so that I can easily recognize heavily impacted regions.
- As a user I can filter earthquakes by magnitude, so that I only see events that feel relevant to me.
- As a person who lives near the beach, I would like to know if there was tsunami near my place in the last few weeks/months or alerted when there is one
- As a non technical user, I can ask the system any earthquakes data using just a natural language, such as “show me any earthquakes event with magnitude higher than 3.0 in Austria in the last 30 days and sorted by date” 
- As a user I can sort earthquakes by most recent, strongest or nearest to my location so I can scan for events that matter to me.
- As a user I can toggle between different map views like satellite or terrain, so that I can view the impact location from different angles. 
- As a user I can use speed through a certain time period, so that I can check how many earthquakes occurred in that time period. 

## System Architecture and Design

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     EARTHQUAKE DATA PIPELINE                    │
└─────────────────────────────────────────────────────────────────┘

1. EXTRACTION STAGE (Docker container)
   ┌──────────────┐
   │  USGS API    │ (GeoJSON)
   └──────┬───────┘
          │ HTTP GET (monthly chunks)
          ↓
   ┌──────────────────┐
   │ Python Extractor │ → Parquet files (data/usgs_earthquakes/YYYY-MM/)
   └──────┬───────────┘
          │ Updates monthly_loads table (status='loaded')
          ↓

2. TRANSFORMATION STAGE (Docker container)
   ┌──────────────────┐
   │ Apache Spark     │ → Reads Parquet files
   │ + PySpark        │ → Parses GeoJSON features
   │ + GeoPandas      │ → Spatial joins with EEZ/GOaS shapefiles
   └──────┬───────────┘
          │ JDBC writes via PostgreSQL driver
          ↓
   ┌──────────────────────────────────────────┐
   │ PostGIS Database (PostgreSQL 16)         │
   │  • quake (main events + geometry)        │
   │  • country (ISO3 lookup)                 │
   │  • sea (waterbody lookup)                │
   │  • location (quake <-> country/sea)      | 
   │  • monthly_loads (pipeline status)       │
   └──────┬───────────────────────────────────┘
          │
          ↓

3. VISUALIZATION STAGE
   ┌──────────────────┐
   │ Streamlit        │ → SQLModel queries (PostGIS)
   │ Frontend (local) │ → Mapbox GL maps + Altair charts
   └──────────────────┘
```

**Data Flow:**
1. **Extractor** fetches earthquake data from USGS API for the last N months (configurable via `MONTHS_BEFORE_CURRENT`)
2. Each month's data is stored as a Parquet file containing raw GeoJSON features
3. **Spark** processes Parquet files, normalizing data and writing to PostGIS via JDBC with upsert logic (merge by `usgs_id`)
4. **GeoPandas** performs spatial joins with embedded EEZ/GOaS shapefiles to enrich location data (country/sea associations)
5. **Streamlit** provides interactive web interface for querying and visualizing earthquake data

**Key Design Decisions:**
- **Parquet Storage:** Preserves raw GeoJSON as large_string for schema flexibility while enabling columnar processing
- **Status Tracking:** `monthly_loads` table prevents duplicate processing and enables incremental pipeline reruns
- **Spatial Joins:** In-memory GeoPandas processing during Spark transformation (suitable for single-node execution)
- **Local Frontend:** Streamlit runs outside Docker for faster development iteration and debugging

### Data Sources

**Primary Data Source: USGS Earthquake Catalog API**
- **URL:** https://earthquake.usgs.gov/fdsnws/event/1/query
- **Format:** GeoJSON (RFC 7946) with extended USGS properties
- **Velocity:** Batch processing (monthly incremental loads)
- **Volume:** ~10,000-50,000 events per month globally (varies by magnitude threshold)
- **Key Fields:**
  - **Geometry:** longitude, latitude, depth (km below surface)
  - **Properties:** magnitude (Richter/moment magnitude), time (ISO 8601 UTC), place (textual description), title, tsunami flag (0/1), significance, event type
  - **Identifiers:** `usgs_id` (unique event ID), `code` (network-specific code)
  - **Metadata:** updated timestamp, detail URL, status (reviewed/automatic)

**Enrichment Data Sources:**
- **EEZ (Exclusive Economic Zones) Shapefile:**
  - Source: Marine Regions / Flanders Marine Institute
  - Purpose: Country maritime boundaries for spatial joins
  - Format: ESRI Shapefile with ISO3 country codes
- **GOaS (Global Ocean and Seas) Shapefile:**
  - Source: IHO (International Hydrographic Organization) Sea Areas
  - Purpose: Waterbody polygon identification
  - Format: ESRI Shapefile with sea/ocean names


**Data Characteristics:**
- Real-time updates for recent events (USGS updates within minutes of detection)
- All timestamps in UTC timezone
- Coordinates in WGS84 (EPSG:4326) geographic coordinate system

### Data Model

**Entity-Relationship Diagram:**

```
┌──────────────────────────────────────────────┐
│ quake (main earthquake events)               │
│──────────────────────────────────────────────│
│ PK: id (SERIAL)                              │
│ UK: usgs_id (VARCHAR, unique)                │
│     mag (FLOAT)                              │
│     depth_km (FLOAT)                         │
│     time_utc (TIMESTAMPTZ)                   │
│     place (VARCHAR)                          │
│     title (VARCHAR)                          │
│     tsunami (INTEGER) -- 0/1 flag            │
│     sig (INTEGER) -- significance            │
│     typ (VARCHAR) -- event type              │
│     geom (GEOMETRY(Point, 4326)) -- PostGIS  │
│     updated_utc (TIMESTAMPTZ)                │
│     ... (additional USGS metadata)           │
└──────────────┬───────────────────────────────┘
               │ 1
               │
               │ 1
┌──────────────┴───────────────────────────────┐
│ location (geographic resolution)             │
│──────────────────────────────────────────────│
│ PK: quake_id (FK → quake)                    │
│ FK: country_iso (VARCHAR(3) → country)       │
│ FK: sea_id (INTEGER → sea)                   │
└──────────┬────────────────────┬──────────────┘
           │ N                  │ N
           │                    │
      ┌────┴─────────┐    ┌─────┴──────────┐
      │ country      │    │ sea            │
      │──────────────│    │────────────────│
      │ PK: iso      │    │ PK: id         │
      │     name     │    │     name       │
      └──────────────┘    └────────────────┘

┌──────────────────────────────────────────────┐
│ monthly_loads (pipeline status tracking)     │
│──────────────────────────────────────────────│
│ PK: month_start (TIMESTAMPTZ)                │
│     month_end (TIMESTAMPTZ)                  │
│     status (VARCHAR) - 'loaded'/'transformed'│
│     updated_at (TIMESTAMPTZ)                 │
└──────────────────────────────────────────────┘
```

**Key Relationships:**
1. **Quake <-> Location (1:1):** Each earthquake has exactly one location record linking it to geographic entities
2. **Location -> Country (N:1, nullable):** Location references country via ISO3 code (NULL for oceanic events)
3. **Location -> Sea (N:1, nullable):** Location references sea via sea_id (NULL for terrestrial events)
4. **Monthly Loads:** Independent tracking table for ETL orchestration and idempotency

**Spatial Indexes:**
- `quake.geom`: GiST index for fast bounding box queries and spatial predicates

**Sample Data Structures:**

**Quake Record (PostGIS table):**
```sql
id: 12345
usgs_id: 'us7000m3xe'
mag: 6.2
depth_km: 10.5
time_utc: '2024-03-15 14:23:11+00'
place: '89 km SE of Naze, Japan'
title: 'M 6.2 - 89 km SE of Naze, Japan'
tsunami: 1
sig: 602
typ: 'earthquake'
geom: POINT(130.2345 28.6789)  -- PostGIS geometry
updated_utc: '2024-03-15 14:30:22+00'
```

**Location Record:**
```sql
quake_id: 12345
country_iso: 'JPN'
sea_id: 42
```
*Note: Country names and sea names are resolved via JOINs to the `country` and `sea` tables at query time, not stored in the location table.*

**Monthly Load Tracking:**
```sql
month_start: '2024-03-01 00:00:00+00'
month_end: '2024-03-31 23:59:59.999+00'
status: 'transformed'
updated_at: '2024-04-01 02:45:12+00'
```

**SQLModel Implementation:**
The project uses a shared Python package (`common/`) with SQLModel definitions for all tables, enabling type-safe queries across Extractor, Spark, and Streamlit:

```python
# earthquakes_common.models
class Quake(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    usgs_id: str = Field(unique=True, index=True)
    mag: Optional[float]
    depth_km: Optional[float]
    time_utc: Optional[datetime]
    sig: Optional[int]
    geom: Optional[Any] = Field(sa_column=Column(Geometry("POINT", srid=4326)))
    # ... additional fields
```

## Setup and Deployment

### Prerequisites
You'll need the following installed and available on your machine before running this project:

- **Git**
  - Any recent version is fine (>=2.30 recommended)

- **Conda / Miniconda**
  - Miniconda or Anaconda
  - Must support creating environments with `conda env create`
  - Ensure `conda` is available in your PATH (!)

- **Python via Conda**
  - You don't need a global Python setup; Conda will install **Python 3.12**

- **Docker Desktop + Docker Compose**
  - Docker Desktop on Windows/macOS, or Docker Engine + Compose plugin on Linux
  - Must be running before you start the containers
  - Docker Compose version >=3.9 is required

- **(Optional) Make**
  - For macOS/Linux users who want to use helper `make` commands

- **Resources / Access**
  - Read access to this repository
  - Network access to pull container images (PostGIS, Spark, etc.)
  - A few gigabytes of disk space for database storage
  - **Mapbox Account** (free tier) for map visualization tokens


### Installation & Launch

#### 1. Clone the repository
```bash
git clone https://github.com/FHTW-AI25/DataEngineering.git
cd DataEngineering
```

After this step, your directory should contain:
- `common/` (shared SQLModel package)
- `data/` (Parquet files, gitignored)
- `db/` (PostgreSQL init scripts and volumes)
- `dev/` (development utilities)
- `docs/` (documentation)
- `extractor/` (Python USGS API client)
- `scripts/` (helper bash scripts)
- `spark/` (PySpark transformation job)
- `src/` (Streamlit frontend)
- `.env.example`
- `.gitignore`
- `docker-compose.yml`
- `environment.yml`
- `README.md`


---

#### 2. Create the Conda environment
This will:
- Create a new Conda environment named `data-engineering`
- Install **Python 3.12**
- Install additional packages via pip:

```bash
conda env create -f environment.yml
```

---

#### 3. Activate the environment
```bash
conda activate data-engineering
```

You should now see:
```
(data-engineering) >
```

---

#### 4. Configure environment variables
Copy and edit the environment variable file, use copy for Windows:

```bash
cp .env.example .env 
```

Typical `.env` file:
```ini
POSTGRES_DB=db
POSTGRES_USER=admin
POSTGRES_PASSWORD=password
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
PGDATA=/var/lib/postgresql/data

MAPBOX_TOKEN=pk.eyJ1IjoiZXhhbXBsZSIsImEiOiJjazU4M3h0czYwMDA0M2RsbGZ4MHR0cTFuIn0.abc123

MONTHS_BEFORE_CURRENT=12
REQUEST_TIMEOUT_SECONDS=60
REQUEST_SLEEP_SECONDS=0.2
MAX_SPLIT_RETRIES=20
```

---

 **Important setup notes:**
- You **must obtain your own Mapbox access token** to enable interactive maps in the Streamlit frontend.
  - Get your token here → [https://account.mapbox.com/access-tokens/](https://account.mapbox.com/access-tokens/)
  - Replace the placeholder `MAPBOX_TOKEN` value in your `.env` file with your own key.
- You may **optionally change the database name, user, and password** (`POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`) to suit your local environment.

---

#### 5. Build and start the Docker services
Before starting, ensure **Docker Desktop** (or Docker Engine on Linux) is running.

Build and start all containers with:

```bash
docker compose up -d --build
```

This will:
- Build and start **three services**:
  -  **db** -> PostgreSQL + PostGIS database
  -  **extractor**-> earthquake data ingestion pipeline
  -  **spark** -> Spark job processor

Data persistence:
- Database data is stored in `db/volume/`
- Extracted earthquake data is stored in `data/usgs_earthquakes/`

Verify the containers are running:
```bash
docker ps
```

Once running, the PostGIS database will be available on **localhost:5432** (unless changed in `.env`).

Monitor pipeline progress:
```bash
docker compose logs -f extractor
docker compose logs -f spark
```

---

#### 6. Run the Streamlit frontend (locally)
Unlike the other components, **Streamlit is not containerized** — it runs directly on your local machine using the Conda environment you set up.

To start it:

```bash
streamlit run src/streamlit/mainpage.py
```

This will launch the app at:

[http://localhost:8501](http://localhost:8501)

> The Streamlit app connects to the PostGIS container (database host: `localhost` when running locally, `db` if run inside Docker).

---

#### 🧹 Optional: Restart and clean up
If you want to **reset everything**, use the provided `reset.sh` script in /scripts.

This script will:
- Stop and remove all Docker containers
- Remove locally created data volumes and files (`db/volume/` and `data/usgs_earthquakes/`)

Run it from the project root:

```bash
bash scripts/reset.sh
```

After cleanup, you can rebuild and restart everything with:

```bash
docker compose up -d --build
```

---

### Configuration Parameters

**Database Configuration:**
- `POSTGRES_USER`: PostgreSQL username (default: admin)
- `POSTGRES_PASSWORD`: PostgreSQL password
- `POSTGRES_DB`: Database name (default: db)
- `POSTGRES_PORT`: Host port mapping for PostgreSQL (default: 5432)
- `DATABASE_URL`: Full connection string override (optional, auto-constructed if not provided)

**Extraction Configuration:**
- `MONTHS_BEFORE_CURRENT`: Number of historical months to extract (default: 12)
- `REQUEST_TIMEOUT_SECONDS`: USGS API request timeout in seconds (default: 60)
- `REQUEST_SLEEP_SECONDS`: Delay between API requests to respect rate limits (default: 0.2)
- `MAX_SPLIT_RETRIES`: Maximum recursive splits when USGS returns 400 errors due to result size (default: 20)

**Mapbox Configuration:**
- `MAPBOX_TOKEN`: Required for Streamlit map visualization (get from https://account.mapbox.com/)

**Advanced Docker Configuration:**
- `POSTGRES_HOST`: Database hostname (default: `db` in containers, `localhost` for Streamlit)

## Limitations and Future Work

**Limitations:**
- **USGS API Constraints:** The API occasionally returns 400 errors for large time ranges, which is handled through recursive time-range splitting with exponential backoff.
- **US Collection Bias:** USGS data over-represents US micro-earthquakes due to denser seismometer networks, mitigated through magnitude filtering in the Streamlit interface.
- **Spatial Boundary Ambiguity:** Location enrichment uses EEZ and GOaS shapefiles which may have inherent classification challenges for earthquakes on maritime borders or near coastlines.

**Future Work:**
- **Real-Time Streaming:** Implement Kafka + Spark Structured Streaming to ingest the USGS real-time GeoJSON feed, enabling sub-minute latency for recent earthquake visualization and alerting.
- **Enhanced Geospatial Analysis:** Integrate tectonic plate boundary data and population density layers to correlate seismic activity with fault lines and calculate human impact exposure scores.
- **Predictive Analytics:** Apply machine learning models (LSTM networks, DBSCAN clustering) for aftershock prediction and seismic pattern identification across historical data.

---

## Conclusion

This earthquake data engineering pipeline successfully demonstrates modern data engineering practices by building a complete ETL system that extracts global seismic data, enriches it with geospatial context, and provides an intuitive visualization interface. By leveraging containerization (Docker), data processing with Apache Spark, geospatial databases (PostGIS), and interactive visualization (Streamlit with Mapbox), the project addresses the challenge of making complex earthquake data accessible to non-technical users.

The pipeline's incremental loading strategy, spatial enrichment capabilities, and interactive filtering demonstrate scalable data engineering patterns applicable to other geospatial datasets. The modular architecture—featuring a shared SQLModel package for type safety, containerized services for reproducibility, and embedded shapefiles for offline enrichment—ensures maintainability and portability across development environments.

Key technical achievements include:
- Handling USGS API limitations through adaptive time-range splitting and retry logic
- Performing efficient spatial joins using GeoPandas and PostGIS spatial indexing
- Delivering sub-second query performance through strategic use of spatial indexes (GiST)
- Providing rich interactive visualizations with multiple map styles, animated playback, and statistical distributions

The project provides a solid foundation for future enhancements such as real-time streaming architectures and machine learning integration for earthquake prediction.

## Data Sources

* [Global Oceans and Seas v01 (2021‑12‑14)](https://www.marineregions.org/sources.php) — This dataset represents the boundaries between the 10 main oceans and seas (Arctic Ocean, North and South Atlantic Ocean, North and South Pacific Ocean, Southern Ocean, Indian Ocean, Baltic Sea, Mediterranean Region, South China and Eastern Archipelagic Seas). The boundaries are largely based on *“Limits of Oceans & Seas, Special Publication No. 23”* published by the International Hydrographic Organization in 1953. The dataset is available in World Geodetic System of 1984 (WGS84) and was composed by the Flanders Marine Data Centre.

* [Marine and Land Zones: Union of World Country Boundaries and EEZs, Version 4 (2024‑10‑10)](https://www.marineregions.org/sources.php) — This dataset combines the boundaries of world countries and the Exclusive Economic Zones (EEZs). It was created by merging the ESRI world country database and the EEZ V12 dataset.

* **Earthquake Data API** — The Earthquake Catalog API provided by the U.S. Geological Survey (USGS) with base URL `https://earthquake.usgs.gov/fdsnws/event/1/` offers global information on seismic events: when and where earthquakes occur, how strong they are (magnitude), how deep they originate, and other contextual details such as tsunami risk or whether people reported feeling the quake. The service supports both real‑time and historical earthquake data for global analysis.

**Additional Resources:**

* Google Colab for Earthquake Data Collection from USGS using Apache Spark: https://colab.research.google.com/drive/1C2iNmma_JU0TZpWjOTD6zj5_JgSiFg50
