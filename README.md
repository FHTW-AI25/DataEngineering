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
- `environment.yml`
- `docker-compose.yml`
- `README.md`
- `src/`
- `scripts/`

---

#### 2. Create the Conda environment
This will:
- Create a new Conda environment named `data-engineering`
- Install **Python 3.12**
- Install `geopandas` from Conda
- Install additional packages via pip:
  - Streamlit 1.50.0  
  - SQLModel 0.0.27  
  - GeoAlchemy2 0.18.0  
  - psycopg2-binary 2.9.11
  - python-dotenv 1.2.1

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
```

---

💡 **Important setup notes:**
- You **must obtain your own Mapbox access token** to enable interactive maps in the Streamlit frontend.  
  - Get your token here → [https://account.mapbox.com/access-tokens/](https://account.mapbox.com/access-tokens/)  
  - Replace the placeholder `MAPBOX_TOKEN` value in your `.env` file with your own key.  
- You may **optionally change the database name, user, and password** (`POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`) to suit your local environment.

---

#### 5. Start Docker services
Ensure Docker Desktop is running, then start all containers:

```bash
docker compose up -d
```

This starts:
- **db** → PostGIS database  
- **spark** → Spark processing container  
- **streamlit** → Streamlit frontend (if defined in compose file)

Data persistence:
- Database data stored in `src/db/volume/`
- Initialization SQL scripts in `src/db/init/`

Verify containers are running:
```bash
docker ps
```

---

#### 6. Run Streamlit frontend
You can run Streamlit in two ways:

**Option A: Local Conda environment (recommended for development)**
```bash
streamlit run src/streamlit/mainpage.py
```
Then open [http://localhost:8501](http://localhost:8501)

**Option B: Inside Docker (for consistent deployment)**
```bash
docker compose up -d streamlit
```
Then visit [http://localhost:8501](http://localhost:8501)

> When using Docker, the database host is `db`.  
> When running locally, use `localhost`.

---

#### 7. Verify your setup
Run a quick check to confirm everything imports correctly:

```bash
python -c "import geopandas, streamlit, sqlmodel, geoalchemy2, psycopg2; print('✅ All imports OK')"
```

Expected output:
```
✅ All imports OK
```

---

### Useful Commands

| Action | Command |
|--------|----------|
| Create environment | `conda env create -f environment.yml` |
| Update environment | `conda env update -f environment.yml --prune` |
| Activate environment | `conda activate data-engineering-py314` |
| Deactivate environment | `conda deactivate` |
| Remove environment | `conda env remove -n data-engineering-py314` |
| Start all Docker services | `docker compose up -d` |
| Stop all Docker services | `docker compose down` |
| Run Streamlit app locally | `streamlit run src/streamlit/mainpage.py` |
| Check running containers | `docker ps` |

---

## Project Structure

```
{project-directory}/
├── README.md                # Project documentation
├── .env.example             # Template for environment variables
├── .env                     # Local configuration (not in Git)
├── environment.yml          # Conda + pip environment specification
├── docker-compose.yml       # Defines database, Spark, Streamlit containers
│
├── scripts/                 # Automation and helper scripts
│   ├── start_all.sh
│   ├── stop_all.sh
│   ├── rebuild.sh
│   └── run_frontend.sh
│
├── src/
│   ├── streamlit/           # Streamlit app files
│   │   ├── mainpage.py
│   │   ├── components/
│   │   └── utils/
│   │
│   ├── db/                  # Database setup & volume
│   │   ├── init/
│   │   └── volume/
│   │
│   ├── spark/               # Spark Docker + job definitions
│   │   ├── Dockerfile
│   │   ├── jobs/
│   │   └── scripts/
│   │
│   ├── data/                # Local data files (gitignored)
│   └── utils/               # Shared helper scripts
│
└── tests/                   # Unit / integration tests
```

---

## Quick Recap

1. `conda env create -f environment.yml`  
2. `conda activate data-engineering-py314`  
3. `cp .env.example .env` and edit values  
4. `docker compose up -d`  
5. `streamlit run src/streamlit/mainpage.py`

You’re all set 🚀


* Google Colab for Earthquake Data Collection from USGS using Apache Spark: https://colab.research.google.com/drive/1C2iNmma_JU0TZpWjOTD6zj5_JgSiFg50
