# src/services/location_manager.py
from __future__ import annotations
from typing import Iterable, Sequence
import pandas as pd
from sqlalchemy import text
from sqlmodel import SQLModel
from location.data_loader import DataLoader
from location.location_resolver import LocationResolver, Location
from models.models import Country, Sea, Location
from data.db import get_engine, get_session

class LocationManager:
    """
    Creates the location table and fills it by resolving (lat, lon) for earthquakes.
    - quake_id      -> usgs_quakes.id
    - country_iso   -> ISO3 or None
    - sea_id        -> FK to sea.id or None
    """

    def __init__(self, resolver: LocationResolver | None = None):
        # Build resolver from DataLoader if none provided
        if resolver is None:
            loader = DataLoader()
            eez, goas = loader.load_all()
            resolver = LocationResolver(eez, goas)
        self.resolver = resolver

    # --- schema ---
    def create_table(self) -> None:
        engine = get_engine()
        # Make sure the models are imported so metadata knows all tables
        SQLModel.metadata.create_all(engine)

    # --- ingestion ---
    def upsert_locations_for_quakes(self, quakes: Iterable["Earthquake"]) -> int:
        """
        Resolve country & sea for each earthquake and upsert into 'location'.
        Skips quakes without lat/lon.
        Returns number of rows upserted.
        """

        records = []
        for q in quakes:
            if q.lat is None or q.lon is None:
                continue
            loc = self.resolver.resolve(q.lat, q.lon)

            sea_id = None
            if loc and loc.sea:
                sea_id = int(loc.sea)

            records.append({
                "quake_id": int(q.id),
                "country_iso": (loc.country if loc else None),
                "sea_id": sea_id
            })

        if not records:
            return 0

        with get_session() as session:
            session.execute(
                text("""
                    INSERT INTO location (quake_id, country_iso, sea_id)
                    VALUES (:quake_id, :country_iso, :sea_id)
                    ON CONFLICT (quake_id) DO UPDATE
                    SET country_iso = EXCLUDED.country_iso,
                        sea_id = EXCLUDED.sea_id
                """),
                records,
            )
            session.commit()
        return len(records)

    # convenience: pull quakes from DB directly
    def upsert_locations_for_all_quakes(self) -> int:
        with get_session() as session:
            rows = session.exec(text("""
                SELECT id, lat, lon
                FROM usgs_quakes
                WHERE lat IS NOT NULL AND lon IS NOT NULL
            """)).fetchall()
        # Create a tiny shim object with attributes id/lat/lon
        class _Q: pass
        quakes = []
        for r in rows:
            q = _Q()
            q.id, q.lat, q.lon = r[0], r[1], r[2]
            quakes.append(q)
        return self.upsert_locations_for_quakes(quakes)
