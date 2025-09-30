from __future__ import annotations
from sqlmodel import create_engine, Session
import streamlit as st


def build_connection_string() -> str:
    cfg = st.secrets["postgres"]
    return (
        f"postgresql+psycopg2://{cfg['user']}:{cfg['password']}"
        f"@{cfg['host']}:{cfg['port']}/{cfg['dbname']}"
    )

_engine = None

def get_engine():
    global _engine
    if _engine is None:
        _engine = create_engine(build_connection_string(), pool_pre_ping=True)
    return _engine

def get_session() -> Session:
    return Session(get_engine())