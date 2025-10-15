from __future__ import annotations
from typing import Optional
from datetime import datetime
from sqlmodel import SQLModel, Field
from sqlalchemy import Index, Column
from geoalchemy2 import Geometry

class Earthquake(SQLModel, table=True):
    """
    ORM for: usgs_quakes
    """
    __tablename__ = "usgs_quakes"

    __table_args__ = (
        Index("usgs_quakes_time_idx", "time_utc"),
        Index("usgs_quakes_mag_idx", "mag"),
        {"extend_existing": True},
    )

    # Columns
    id: Optional[int] = Field(default=None, primary_key=True)
    usgs_id: Optional[str] = None

    mag: Optional[float] = None
    place: Optional[str] = None
    time_utc: Optional[datetime] = None
    updated_utc: Optional[datetime] = None
    url: Optional[str] = None
    detail_url: Optional[str] = None

    tsunami: Optional[int] = None
    sig: Optional[int] = None
    mag_type: Optional[str] = None
    typ: Optional[str] = None
    title: Optional[str] = None
    net: Optional[str] = None
    code: Optional[str] = None

    depth_km: Optional[float] = None
    lon: Optional[float] = None
    lat: Optional[float] = None

    # PostGIS geometry column
    geom: Optional[str] = Field(
        default=None,
        sa_column=Column(Geometry(geometry_type="POINT", srid=4326))
    )

class Country(SQLModel, table=True):
    __tablename__ = "country"
    iso: str = Field(primary_key=True, max_length=3)
    name: str = Field(index=True, max_length=255)

class Sea(SQLModel, table=True):
    __tablename__ = "sea"
    id: int = Field(primary_key=True)      # 0..9
    name: str = Field(index=True, max_length=255, unique=True)