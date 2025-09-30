# Directory for source code

Here you can find information about how to start the different services

---

## Start the Streamlit App

Follow these minimal steps to run the app. The app **must be started from the project root** so Streamlit can read the secret token.

### Install Streamlit

```bash
pip install -r requirements.txt
```

### Set the Mapbox secret
Create the file at `./streamlit/.streamlit/secrets.toml` with the key:
```toml
MAPBOX_TOKEN = "<your-mapbox-token-here>"
```

### Set DB credentials
Add db credentials to `./streamlit/.streamlit/secrets.toml` file:
```toml
[postgres]
host = "<host>" # e.g. localhost 
port = 5432
dbname = "<dbname>"
user = "<dbuser>"
password = "<dbpassword>"
```
> The file and folder must live at the **streamlit** root of the project.

### Start the app from the project root

```bash
streamlit run mainpage.py
```

That’s it. Launching from the `./streamlit/` ensures the `./streamlit/.streamlit/secrets.toml` is discovered and `MAPBOX_TOKEN` is available to the app.

---

## Docker Compose

This explains how to start the **PostgreSQL + PostGIS** service defined below and where your database files live on your machine.

### Prerequisites

* Docker Desktop or Docker Engine + Compose
* A `.env` file in the db root with at least:

  ```dotenv
  POSTGRES_USER=your_user
  POSTGRES_PASSWORD=your_password
  POSTGRES_DB=your_db_name
  PG_PORT=5432
  ```

---

### Start the database

From the **db root** (where `docker-compose.yml` lives):

```bash
# start in the background
docker compose up -d db
```

When healthy, logs will settle and the healthcheck will report `healthy`.

#### Check health

```bash
docker ps --filter name=earthquakes-db --format 'table {{.Names}}\t{{.Status}}'
```

Look for `Up ... (healthy)`.

---

#### Connect to the database

**From your host (e.g., psql):**

```bash
psql "host=localhost port=$PG_PORT dbname=$POSTGRES_DB user=$POSTGRES_USER password=$POSTGRES_PASSWORD sslmode=disable"
```

**From inside the container (optional):**

```bash
docker exec -it earthquakes-db psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"
```

---

#### One‑time init scripts

Any `.sql` files placed in `./db/init` are executed **once** on first startup when no existing database is present. They will not rerun on subsequent restarts unless you wipe the data directory.

---

#### Where is my data saved?

All PostgreSQL data is persisted on your local machine in the project folder:

```
./db/volume/
```

This host directory is bind‑mounted to the container path `/var/lib/postgresql/data/pgdata`. That means:

* **Stop/start safe:** Restarting the container does not delete data.
* **Rebuild safe:** Rebuilding the image does not affect data.
* **Fresh start:** Deleting `./db/volume/` (or emptying it) wipes the database so the init scripts run again on next boot.

> Keep `./db/volume/` out of version control.

---

### Stop / restart / remove

```bash
# stop the container (keeps data)
docker compose stop db

# start again
docker compose start db

# remove the container (keeps data on host)
docker compose down

# remove container + named volumes (not used here), networks, etc.
# (data in ./volume remains because it's a bind mount)
docker compose down -v
```