from __future__ import annotations
from dotenv import load_dotenv
import os
from sqlmodel import create_engine, Session

# Load environment variables from .env
load_dotenv()

def build_connection_string() -> str:
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = os.getenv("POSTGRES_PORT", "5432")
    db = os.getenv("POSTGRES_DB", "db")
    user = os.getenv("POSTGRES_USER", "admin")
    password = os.getenv("POSTGRES_PASSWORD", "password")

    return f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{db}"

_engine = None

def get_engine():
    global _engine
    if _engine is None:
        _engine = create_engine(build_connection_string(), pool_pre_ping=True)
    return _engine

def get_session() -> Session:
    return Session(get_engine())