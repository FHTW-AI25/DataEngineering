from __future__ import annotations
from contextlib import contextmanager
from sqlmodel import create_engine, Session
import os
from dotenv import load_dotenv

load_dotenv(override=False)

def _database_url() -> str:
    url = os.getenv("DATABASE_URL")
    if url:
        return url
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = os.getenv("POSTGRES_PORT", "5432")
    db   = os.getenv("POSTGRES_DB", "db")
    user = os.getenv("POSTGRES_USER", "admin")
    pw   = os.getenv("POSTGRES_PASSWORD", "password")
    return f"postgresql+psycopg2://{user}:{pw}@{host}:{port}/{db}"

_engine = None

def get_engine():
    global _engine
    if _engine is None:
        _engine = create_engine(_database_url(), pool_pre_ping=True)
    return _engine

@contextmanager
def get_session() -> Session:
    s = Session(get_engine())
    try:
        yield s
    finally:
        s.close()
