from typing import Optional, Sequence, Dict, Any, List
from datetime import datetime, timezone

from sqlmodel import select
from sqlalchemy import and_, or_, func
from data.db import get_session
from models.models import Earthquake

class DataSource:
    """Interface for a data source that returns a GeoJSON feed."""
    def name(self) -> str: ...
    def get_endpoint(self, **kwargs) -> str: ...

class LiveUSGSDataSource(DataSource):
    def name(self): return "USGS (live, last 24h)"
    def get_endpoint(self, **kwargs) -> str:
        return "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_day.geojson"

# ---------- ORM-backed Postgres ----------
class PostgresORMDataSource(DataSource):
    def name(self):
        return "PostgreSQL (ORM: SQLModel)"

    def get_endpoint(self, **kwargs) -> str:
        return ""  # Not used

    def fetch_geojson(
            self,
            *,
            start_ms: int,
            end_ms: int,
            mag_min: float,
            mag_max: float,
            depth_min: float,
            depth_max: float,
            tsunami_only: bool,
            text_query: str,
            networks: Sequence[str],
            bbox: Optional[Sequence[float]],
            limit: int = 5000,
    ) -> Dict[str, Any]:
        """Build SQL with expressions, run via session.exec, return FeatureCollection."""

        # Convert ms → datetime
        start_dt = datetime.fromtimestamp(start_ms / 1000, tz=timezone.utc)
        end_dt   = datetime.fromtimestamp(end_ms   / 1000, tz=timezone.utc)

        conds = [
            Earthquake.time_utc.between(start_dt, end_dt),
            Earthquake.mag.between(mag_min, mag_max),
            Earthquake.depth_km.between(depth_min, depth_max),
        ]

        if tsunami_only:
            conds.append(Earthquake.tsunami == 1)

        tq = (text_query or "").strip().lower()
        if tq:
            like = f"%{tq}%"
            conds.append(or_(
                func.lower(Earthquake.place).ilike(like),
                func.lower(Earthquake.title).ilike(like),
            ))

        nets = [n.strip().lower() for n in networks or [] if n.strip()]
        if nets:
            conds.append(func.lower(Earthquake.net).in_(nets))

        # --- BBOX filter ---
        if bbox:
            min_lon, min_lat, max_lon, max_lat = bbox
            conds.append(
                func.ST_Intersects(
                    Earthquake.geom,
                    func.ST_MakeEnvelope(min_lon, min_lat, max_lon, max_lat, 4326)
                )
            )

        stmt = (
            select(Earthquake)
            .where(and_(*conds))
            .order_by(Earthquake.time_utc.desc())
            .limit(limit)
        )

        with get_session() as session:
            rows: List[Earthquake] = session.exec(stmt).all()

        def to_epoch_ms(ts: Optional[datetime]) -> Optional[int]:
            return int(ts.timestamp() * 1000) if ts else None

        def feat(r: Earthquake) -> Dict[str, Any]:
            coords = None
            if r.lon is not None and r.lat is not None:
                z = float(r.depth_km) if r.depth_km is not None else None
                coords = [float(r.lon), float(r.lat), z]
            return {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": coords} if coords else None,
                "properties": {
                    "time": to_epoch_ms(r.time_utc) or 0,
                    "mag": float(r.mag) if r.mag is not None else None,
                    "place": r.place,
                    "depth_km": float(r.depth_km) if r.depth_km is not None else None,
                    "lon": float(r.lon) if r.lon is not None else None,
                    "lat": float(r.lat) if r.lat is not None else None,
                    "tsunami": int(r.tsunami) if r.tsunami is not None else 0,
                    "net": r.net,
                    "url": r.url,
                    "title": r.title,
                },
            }

        return {"type": "FeatureCollection", "features": [feat(r) for r in rows]}

# Register
DATA_SOURCES = [LiveUSGSDataSource(), PostgresORMDataSource()]
