from typing import Optional
from sqlmodel import SQLModel, Field
from sqlalchemy import Index

class Earthquake(SQLModel, table=True):
    __tablename__ = "earthquakes"
    # Helpful composite / single-column indexes
    __table_args__ = (
        Index("ix_quakes_time_ms", "time_ms"),
        Index("ix_quakes_mag", "mag"),
        Index("ix_quakes_depth", "depth_km"),
        Index("ix_quakes_lon_lat", "lon", "lat"),
        Index("ix_quakes_net", "net"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    time_ms: int = Field(index=True)                 # epoch ms
    mag: Optional[float] = None
    place: Optional[str] = None
    depth_km: Optional[float] = None
    lon: float
    lat: float
    tsunami: bool = False
    net: Optional[str] = None
    url: Optional[str] = None
