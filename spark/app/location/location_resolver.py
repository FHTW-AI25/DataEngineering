from __future__ import annotations
from dataclasses import dataclass
from typing import Optional
from shapely.geometry import Point
import geopandas as gpd

@dataclass
class Location:
    sea_name: Optional[str]
    country_iso: Optional[str]

class LocationResolver:
    def __init__(self, eez_land_union: gpd.GeoDataFrame, goas: gpd.GeoDataFrame):
        self.eez_land_union = eez_land_union
        self.goas = goas

    def resolve(self, lat: float, lon: float) -> Optional[Location]:
        return Location(self.resolve_sea(lat, lon), self.resolve_country(lat, lon))

    def resolve_sea(self, lat: float, lon: float) -> Optional[str]:
        pt = Point(lon, lat)
        # fast candidate check via spatial index
        idx = self.goas.sindex.query(pt)
        if len(idx) == 0:
            return None
        # precise geometry test
        subset = self.goas.iloc[idx]
        mask = subset.geometry.covers(pt)
        if not mask.any():
            return None
        row = subset[mask].iloc[0]
        # Use a "name" column if present; else fallback to index-like name
        return row.get("name") if "name" in row else (str(row.name) if row.name is not None else None)

    def resolve_country(self, lat: float, lon: float) -> Optional[str]:
        pt = Point(lon, lat)
        idx = self.eez_land_union.sindex.query(pt)
        if len(idx) == 0:
            return None
        subset = self.eez_land_union.iloc[idx]
        mask = subset.geometry.covers(pt)
        if not mask.any():
            return None
        row = subset[mask].iloc[0]
        # ISO_SOV1 holds ISO3 sovereign code in the EEZ data
        return row.get("ISO_SOV1")
