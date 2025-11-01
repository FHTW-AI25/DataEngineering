from __future__ import annotations
import os
from dotenv import load_dotenv

# Load .env for local dev; in containers prefer real env vars
load_dotenv(override=False)

def database_url() -> str:
    # Prefer a single DATABASE_URL if present (e.g. used in docker-compose)
    url = os.getenv("DATABASE_URL")
    if url:
        return url

    # Fallback: build from individual parts for local CLI usage
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = os.getenv("POSTGRES_PORT", "5432")
    db   = os.getenv("POSTGRES_DB", "db")
    user = os.getenv("POSTGRES_USER", "admin")
    pw   = os.getenv("POSTGRES_PASSWORD", "password")
    return f"postgresql+psycopg2://{user}:{pw}@{host}:{port}/{db}"
