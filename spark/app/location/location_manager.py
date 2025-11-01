from __future__ import annotations
from typing import Iterable, Optional, Dict, Tuple, List
from sqlalchemy import text
from earthquakes_common import get_session
from app.geo.data_loader import DataLoader
from .location_resolver import LocationResolver, Location

class LocationManager:
    """
    Fills the 'location' table (quake_id, country_iso, sea_id) by resolving lat/lon.
    """

    def __init__(self, resolver: LocationResolver | None = None):
        if resolver is None:
            loader = DataLoader()
            eez, goas = loader.load_all()
            resolver = LocationResolver(eez, goas)
        self.resolver = resolver
        self._sea_name_to_id: Dict[str, int] = {}

    def _sea_id_for_name(self, name: Optional[str]) -> Optional[int]:
        if not name:
            return None
        if name in self._sea_name_to_id:
            return self._sea_name_to_id[name]
        with get_session() as s:
            row = s.execute(text("SELECT id FROM sea WHERE name = :n"), {"n": name}).fetchone()
            if row:
                self._sea_name_to_id[name] = int(row.id)
                return self._sea_name_to_id[name]
        return None

    def _resolve_record(self, qid: int, lat: Optional[float], lon: Optional[float]) -> Optional[dict]:
        if lat is None or lon is None:
            return None
        loc: Location = self.resolver.resolve(lat, lon)
        sea_id = self._sea_id_for_name(loc.sea_name) if loc else None
        return {
            "quake_id": qid,
            "country_iso": (loc.country_iso if loc else None),
            "sea_id": sea_id,
        }

    def upsert_locations_for_rows(self, rows: Iterable[Tuple[int, Optional[float], Optional[float]]]) -> int:
        records: List[dict] = []
        for qid, lat, lon in rows:
            rec = self._resolve_record(int(qid), lat, lon)
            if rec:
                records.append(rec)
        if not records:
            return 0
        with get_session() as s:
            s.execute(
                text("""
                    INSERT INTO location (quake_id, country_iso, sea_id)
                    VALUES (:quake_id, :country_iso, :sea_id)
                    ON CONFLICT (quake_id) DO UPDATE
                    SET country_iso = EXCLUDED.country_iso,
                        sea_id      = EXCLUDED.sea_id
                """),
                records,
            )
            s.commit()
        return len(records)

    def upsert_locations_for_month(self, start_ts, end_ts_inclusive) -> int:
        """
        Resolve & upsert locations for quakes with time_utc in [start_ts, end_ts_inclusive].
        """
        with get_session() as s:
            rows = s.execute(text("""
                SELECT id, lat, lon
                  FROM quake
                 WHERE time_utc >= :start_ts
                   AND time_utc <= :end_ts
                   AND lat IS NOT NULL
                   AND lon IS NOT NULL
            """), {"start_ts": start_ts, "end_ts": end_ts_inclusive}).fetchall()
        return self.upsert_locations_for_rows(rows)
