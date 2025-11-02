from __future__ import annotations
from typing import Optional
from datetime import datetime
from sqlmodel import SQLModel, Field
from sqlalchemy import Index, Column, UniqueConstraint, CheckConstraint, ForeignKey
from geoalchemy2 import Geometry

# --------------------- quake ---------------------
class Quake(SQLModel, table=True):
    __tablename__ = "quake"
    __table_args__ = (
        UniqueConstraint("usgs_id", name="quake_usgs_id_key"),
        {"extend_existing": True},
    )

    id: Optional[int] = Field(default=None, primary_key=True)             # bigserial
    usgs_id: Optional[str] = Field(default=None)                          # text UNIQUE

    mag: Optional[float] = Field(default=None)                            # numeric
    place: Optional[str] = Field(default=None)                            # text
    time_utc: Optional[datetime] = Field(default=None)                    # timestamptz
    updated_utc: Optional[datetime] = Field(default=None)                 # timestamptz
    url: Optional[str] = Field(default=None)                              # text
    detail_url: Optional[str] = Field(default=None)                       # text
    tsunami: Optional[int] = Field(default=None)                          # smallint
    sig: Optional[int] = Field(default=None)                              # integer
    mag_type: Optional[str] = Field(default=None)                         # text
    typ: Optional[str] = Field(default=None)                              # text
    title: Optional[str] = Field(default=None)                            # text
    net: Optional[str] = Field(default=None)                              # text
    code: Optional[str] = Field(default=None)                             # text
    depth_km: Optional[float] = Field(default=None)                       # numeric
    lon: Optional[float] = Field(default=None)                            # double precision
    lat: Optional[float] = Field(default=None)                            # double precision

    # PostGIS geometry(Point, 4326)
    geom: Optional[str] = Field(
        default=None,
        sa_column=Column(Geometry(geometry_type="POINT", srid=4326))
    )

# --------------------- country ---------------------
class Country(SQLModel, table=True):
    __tablename__ = "country"
    iso: str = Field(primary_key=True, max_length=3)
    name: str = Field(index=True, max_length=255)

# --------------------- sea ---------------------
class Sea(SQLModel, table=True):
    __tablename__ = "sea"
    id: int = Field(primary_key=True)                 # INTEGER primary key
    name: str = Field(index=True, max_length=255)     # UNIQUE at DB level

# --------------------- location ---------------------
class Location(SQLModel, table=True):
    __tablename__ = "location"

    # 1:1 with quake.id
    quake_id: int = Field(primary_key=True, foreign_key="quake.id")

    # nullable FKs
    country_iso: Optional[str] = Field(
        default=None, foreign_key="country.iso", max_length=3
    )
    sea_id: Optional[int] = Field(
        default=None, foreign_key="sea.id"
    )

# --------------------- monthly_loads ---------------------
class MonthlyLoad(SQLModel, table=True):
    __tablename__ = "monthly_loads"
    __table_args__ = (
        CheckConstraint(
            "status in ('loaded','transformed')",
            name="monthly_loads_status_ck",
        ),
        Index("monthly_loads_status_idx", "status"),
        # UTC boundary invariants are enforced in your DDL; we keep python-side class simple.
        {"extend_existing": True},
    )

    month_start: datetime = Field(primary_key=True)  # timestamptz
    month_end: datetime
    status: str                                      # 'loaded' | 'transformed'
    updated_at: Optional[datetime] = Field(default=None)