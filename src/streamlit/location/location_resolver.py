from dataclasses import dataclass
from typing import Optional
from shapely.geometry import Point
import geopandas as gpd

@dataclass
class Location:
    sea: Optional[str]
    country: Optional[str]

class LocationResolver:
    def __init__(self, eez_land_union: gpd.GeoDataFrame, goas: gpd.GeoDataFrame):
        self.eez_land_union = eez_land_union
        self.goas = goas

    def resolve(self, lat: float, lon: float) -> Optional[Location]:
        return Location(self.resolve_sea(lat, lon), self.resolve_country(lat, lon))

    def resolve_sea(self, lat: float, lon: float) -> Optional[str]:
        pt = Point(lon, lat)
        candidates = self.goas.sindex.query(pt)
        if len(candidates) == 0:
            return None
        mask = self.goas.iloc[candidates].geometry.covers(pt)
        if not mask.any():
            return None
        row = self.goas.iloc[candidates][mask].iloc[0]
        return row.name  # or a column if you prefer a specific label

    def resolve_country(self, lat: float, lon: float) -> Optional[str]:
        try:
            pt = Point(lon, lat)
            candidates = self.eez_land_union.sindex.query(pt)
            if len(candidates) == 0:
                return None
            mask = self.eez_land_union.iloc[candidates].geometry.covers(pt)
            if not mask.any():
                return None
            row = self.eez_land_union.iloc[candidates][mask].iloc[0]
            return row.get("ISO_SOV1")
        except Exception:
            return None
