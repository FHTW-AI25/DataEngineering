# Data Engineering Project

## Setup and Deployment

### Prerequisites
You’ll need the following installed and available on your machine before running this project:

- **Git**
  - Any recent version is fine (>=2.30 recommended)

- **Conda / Miniconda**
  - Miniconda or Anaconda
  - Must support creating environments with `conda env create`
  - Ensure `conda` is available in your PATH

- **Python via Conda**
  - You don’t need a global Python setup; Conda will install **Python 3.12**

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


### Installation & Launch

#### 1. Clone the repository
```bash
git clone https://github.com/FHTW-AI25/DataEngineering.git
cd DataEngineering
```

After this step, your directory should contain:
- `common/`
- `data/`
- `db/`
- `dev/`
- `docs/`
- `extractor/`
- `scripts/`
- `spark/`
- `src/`
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
Copy and edit the environment variable file:

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
REQUEST_TIMEOUT_SECONDS=10
REQUEST_SLEEP_SECONDS=0.2
MAX_SPLIT_RETRIES=3
```

---

💡 **Important setup notes:**
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
  - 🐘 **db** → PostgreSQL + PostGIS database  
  - ⚙️ **extractor** → earthquake data ingestion pipeline  
  - 🔥 **spark** → Spark job processor  

Data persistence:
- Database data is stored in `db/volume/`
- Extracted earthquake data is stored in `data/usgs_earthquakes/`

Verify the containers are running:
```bash
docker ps
```

Once running, the PostGIS database will be available on **localhost:5432** (unless changed in `.env`).

---

#### 6. Run the Streamlit frontend (locally)
Unlike the other components, **Streamlit is not containerized** — it runs directly on your local machine using the Conda environment you set up.

To start it:

```bash
streamlit run src/streamlit/mainpage.py
```

This will launch the app at:

👉 [http://localhost:8501](http://localhost:8501)

> The Streamlit app connects to the PostGIS container (database host: `localhost` when running locally, `db` if run inside Docker).

---

#### 🧹 Optional: Restart and clean up
If you want to **reset everything**, use the provided `restart.sh` script.

This script will:
- Stop and remove all Docker containers
- Remove locally created data volumes and files (`db/volume/` and `data/usgs_earthquakes/`)

Run it from the project root:

```bash
bash scripts/restart.sh
```

After cleanup, you can rebuild and restart everything with:

```bash
docker compose up -d --build
```

---

* Google Colab for Earthquake Data Collection from USGS using Apache Spark: https://colab.research.google.com/drive/1C2iNmma_JU0TZpWjOTD6zj5_JgSiFg50
