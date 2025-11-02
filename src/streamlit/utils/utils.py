# utils.py

import json
import pandas as pd
from typing import Dict, Any, List, Optional, Sequence
from datetime import datetime, timezone

from sqlmodel import select
from sqlalchemy import and_, or_, func, Table, Column, Integer, Text, MetaData, exists, select as sa_select

from earthquakes_common import get_session, Quake
from utils.types import AppConfig


# ---------------------
# JS/templating helpers
# ---------------------

def js_bool(b: bool) -> str:
    return "true" if b else "false"

def js_str(s: str) -> str:
    # robust JS string literal (uses Python's repr for basic escaping)
    # (You can switch to json.dumps(s) if you prefer JSON escaping.)
    return repr(s)

def fill_template_vars(template: str, cfg: AppConfig, geojson: dict | None) -> str:
    """
    Replace placeholders in a template string (JS or HTML).
    """
    return (
        template
        .replace("__MAPBOX_TOKEN__", js_str(cfg.mapbox_token))
        .replace("__MAP_STYLE__", js_str(cfg.style_url))
        .replace("__MAP_STYLE_NAME__", js_str(cfg.style_name))
        .replace("__LAYER_MODE__", js_str(cfg.layer_mode.lower()))
        .replace("__SPEED_HPS__", str(cfg.speed_hps))
        .replace("__START_MS__", str(int(cfg.start_dt.timestamp() * 1000)))
        .replace("__END_MS__", str(int(cfg.end_dt.timestamp() * 1000)))
        .replace("__MAG_MIN__", str(cfg.mag_min))
        .replace("__MAG_MAX__", str(cfg.mag_max))
        .replace("__DEPTH_MIN__", str(cfg.depth_min))
        .replace("__DEPTH_MAX__", str(cfg.depth_max))
        .replace("__TSUNAMI_ONLY__", js_bool(cfg.tsunami_only))
        .replace("__TEXT_QUERY__", js_str(cfg.text_query.strip().lower()))
        .replace(
            "__NETWORKS_JSON__",
            str([s.strip().lower() for s in cfg.networks_csv.split(",") if s.strip()])
        )
        .replace("__BBOX_JSON__", "null" if cfg.bbox is None else str(cfg.bbox))
        .replace("__GEOJSON__", json.dumps(geojson) if geojson else "null")
        .replace("__START_ISO__", cfg.start_dt.isoformat().replace("T", " ").replace("+00:00", " Z"))
        .replace("__END_ISO__", cfg.end_dt.isoformat().replace("T", " ").replace("+00:00", " Z"))
    )


# ---------------------
# DataFrame conversion
# ---------------------

def features_to_dataframe(gj: Dict[str, Any]) -> pd.DataFrame:
    feats = (gj or {}).get("features", []) or []
    rows: List[Dict[str, Any]] = []
    for f in feats:
        p = f.get("properties", {}) or {}
        g = f.get("geometry", {}) or {}
        # lon, lat, depth
        coords = g.get("coordinates", [None, None, None]) or [None, None, None]

        time_ms = p.get("time_ms")
        if time_ms is None:
            time_ms = p.get("time")

        time = to_iso(time_ms)

        if p and g:
            rows.append({
                "time": time,
                "time_ms": time_ms,
                "mag": p.get("mag"),
                "depth_km": coords[2] if len(coords) > 2 else p.get("depth_km"),
                "lon": coords[0],
                "lat": coords[1],
                "place": p.get("place") or p.get("title"),
                "net": p.get("net"),
                "tsunami": p.get("tsunami"),
                "url": p.get("url"),
            })

    df = pd.DataFrame(rows)
    if not df.empty:
        for col in ["mag", "depth_km", "lon", "lat", "time_ms"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")
        if "time_ms" in df.columns:
            df["time"] = pd.to_datetime(df["time_ms"], unit="ms", utc=True, errors="coerce")
    return df


def to_iso(ts_ms: Optional[int]) -> str:
    if not ts_ms:
        return "—"
    # render as UTC
    return datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


# -------------------------------------
# Embedded Postgres ORM data source
# -------------------------------------

# Lightweight table object for location so we can build EXISTS predicates
_metadata = MetaData()
location_tbl = Table(
    "location", _metadata,
    Column("quake_id", Integer),
    Column("country_iso", Text),
    Column("sea_id", Integer),
)

class PostgresORMDataSource:
    """ORM-backed PostgreSQL data source that returns GeoJSON."""
    def name(self) -> str:
        return "PostgreSQL"

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
        location_mode: str = "both",
        filter_by_country: bool = False,
        country_isos: Sequence[str] = (),
    ) -> Dict[str, Any]:
        """Build SQL with expressions, run via session.exec, return FeatureCollection."""

        # Convert ms -> datetime
        start_dt = datetime.fromtimestamp(start_ms / 1000, tz=timezone.utc)
        end_dt   = datetime.fromtimestamp(end_ms   / 1000, tz=timezone.utc)

        # Base conditions
        conds = [
            Quake.time_utc.between(start_dt, end_dt),
            Quake.mag.between(mag_min, mag_max),
            Quake.depth_km.between(depth_min, depth_max),
        ]

        # Tsunami filter
        if tsunami_only:
            conds.append(Quake.tsunami == 1)

        # Text search
        tq = (text_query or "").strip().lower()
        if tq:
            like = f"%{tq}%"
            conds.append(or_(
                func.lower(Quake.place).ilike(like),
                func.lower(Quake.title).ilike(like),
            ))

#        # Networks filter
#        nets = [n.strip().lower() for n in networks or [] if n.strip()]
#        if nets:
#            conds.append(func.lower(Quake.net).in_(nets))

        # BBOX filter (uses PostGIS)
        if bbox:
            min_lon, min_lat, max_lon, max_lat = bbox
            conds.append(
                func.ST_Intersects(
                    Quake.geom,
                    func.ST_MakeEnvelope(min_lon, min_lat, max_lon, max_lat, 4326)
                )
            )

        # Location filter (land/sea)
        if (location_mode or "both").lower() == "land":
            conds.append(
                exists(sa_select(location_tbl.c.quake_id).where(
                    location_tbl.c.quake_id == Quake.id,
                    location_tbl.c.sea_id.is_(None),
                ))
            )
        elif (location_mode or "both").lower() == "sea":
            conds.append(
                exists(sa_select(location_tbl.c.quake_id).where(
                    location_tbl.c.quake_id == Quake.id,
                    location_tbl.c.sea_id.is_not(None),
                ))
            )

        # Country filter
        if filter_by_country:
            iso_list = [c.lower() for c in (country_isos or [])]
            if len(iso_list) == 0:
                # Enabled, but no countries selected → country_iso IS NULL
                conds.append(
                    exists(sa_select(location_tbl.c.quake_id).where(
                        location_tbl.c.quake_id == Quake.id,
                        location_tbl.c.country_iso.is_(None),
                    ))
                )
            else:
                # Enabled, some countries selected → country_iso IN (...)
                conds.append(
                    exists(sa_select(location_tbl.c.quake_id).where(
                        location_tbl.c.quake_id == Quake.id,
                        func.lower(location_tbl.c.country_iso).in_(iso_list),
                    ))
                )
        # else: not enabled → don’t add any country predicate

        # Statement
        stmt = (
            select(Quake)
            .where(and_(*conds))
            .order_by(Quake.time_utc.desc())
        )

        # Fetch rows
        with get_session() as session:
            rows: List[Quake] = session.exec(stmt).all()

        return {"type": "FeatureCollection", "features": [feat(r) for r in rows]}


# --- Helper methods for GeoJSON feature building ---

def to_epoch_ms(ts: Optional[datetime]) -> Optional[int]:
    return int(ts.timestamp() * 1000) if ts else None

def feat(entity: Quake) -> Dict[str, Any]:
    coords = None
    if entity.lon is not None and entity.lat is not None:
        coords = [float(entity.lon), float(entity.lat)]
    return {
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": coords} if coords else None,
        "properties": {
            "time": to_epoch_ms(entity.time_utc) or 0,
            "mag": float(entity.mag) if entity.mag is not None else None,
            "place": entity.place,
            "depth_km": float(entity.depth_km) if entity.depth_km is not None else None,
            "lon": float(entity.lon) if entity.lon is not None else None,
            "lat": float(entity.lat) if entity.lat is not None else None,
            "tsunami": int(entity.tsunami) if entity.tsunami is not None else 0,
            "net": entity.net,
            "url": entity.url,
            "title": entity.title,
        },
    }


# -------------------------------------
# Public function used by callers
# -------------------------------------

def fetch_geojson_for_cfg(cfg: AppConfig) -> Dict[str, Any]:
    """
    Fetch GeoJSON for the given config using the embedded Postgres ORM data source.
    """
    start_ms = int(cfg.start_dt.timestamp() * 1000)
    end_ms   = int(cfg.end_dt.timestamp() * 1000)

    ds = PostgresORMDataSource()
    return ds.fetch_geojson(
        start_ms=start_ms,
        end_ms=end_ms,
        mag_min=cfg.mag_min,
        mag_max=cfg.mag_max,
        depth_min=cfg.depth_min,
        depth_max=cfg.depth_max,
        tsunami_only=cfg.tsunami_only,
        text_query=cfg.text_query,
        networks=[],  # not used anymore
        bbox=cfg.bbox,
        location_mode=cfg.location_mode,
        filter_by_country=cfg.filter_by_country,
        country_isos=cfg.country_isos,
    )
