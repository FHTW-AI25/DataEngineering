from __future__ import annotations
from typing import Iterable
import pandas as pd  # (not strictly used right now, so you *can* drop this import)
from sqlalchemy import text

from location.data_loader import DataLoader
from location.location_resolver import LocationResolver
from data.db import get_session


class LocationManager:
    """
    Populates the 'location' table by resolving (lat, lon) for earthquakes.

    location schema:
      quake_id    -> quake.id (PK, 1:1)
      country_iso -> country.iso (nullable)
      sea_id      -> sea.id (nullable)

    Assumes:
    - 'quake', 'country', 'sea', and 'location' tables already exist.
    - PostGIS + schema were created by init SQL (01_schema.sql).
    """

    def __init__(self, resolver: LocationResolver | None = None):
        # Build resolver from DataLoader if none provided
        if resolver is None:
            loader = DataLoader()
            eez, goas = loader.load_all()
            resolver = LocationResolver(eez, goas)
        self.resolver = resolver

    def upsert_locations_for_quakes(self, quakes: Iterable[object]) -> int:
        """
        For each quake object with {id, lat, lon}, figure out:
          - which country it's in (if any)
          - which sea it's in (if offshore)
        and upsert into the 'location' table.

        Skips quakes missing lat/lon.
        Returns number of rows upserted.
        """
        records = []
        for q in quakes:
            if q.lat is None or q.lon is None:
                continue

            resolved = self.resolver.resolve(q.lat, q.lon)

            sea_id = None
            if resolved and resolved.sea is not None:
                # resolved.sea is expected to be an integer-like ID into `sea.id`
                sea_id = int(resolved.sea)

            records.append({
                "quake_id": int(q.id),
                "country_iso": (resolved.country if resolved else None),
                "sea_id": sea_id,
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
                        sea_id      = EXCLUDED.sea_id
                """),
                records,
            )
            session.commit()

        return len(records)

    def upsert_locations_for_all_quakes(self) -> int:
        """
        Convenience helper:
        - pulls all quakes (id, lat, lon) from DB
        - runs upsert_locations_for_quakes() on them
        """
        with get_session() as session:
            rows = session.exec(text("""
                SELECT id, lat, lon
                FROM quake
                WHERE lat IS NOT NULL
                  AND lon IS NOT NULL
            """)).fetchall()

        # Build lightweight quake-like objects with attributes .id / .lat / .lon
        class _Q:
            __slots__ = ("id", "lat", "lon")

        quakes = []
        for (qid, qlat, qlon) in rows:
            q = _Q()
            q.id = qid
            q.lat = qlat
            q.lon = qlon
            quakes.append(q)

        return self.upsert_locations_for_quakes(quakes)
