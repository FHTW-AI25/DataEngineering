from __future__ import annotations
from pathlib import Path
import os, glob
import geopandas as gpd
import pandas as pd

class DataLoader:
    """Loads EEZ and GOaS datasets from DATA_ROOT (default /data)."""
    def __init__(self, data_root: str | None = None):
        root = os.getenv("DATA_ROOT", data_root or "/data")
        self.data_dir = Path(root).resolve()
        self.eez_dir = self.data_dir / "EEZ_land_union_v4_202410"
        self.eez_path = self.eez_dir / "EEZ_land_union_v4_202410.shp"
        self.goas_split_dir = self.data_dir / "GOaS_v1_20211214_gpkg" / "split"

    def _need(self, p: Path, hint=""):
        if not p.exists():
            raise FileNotFoundError(f"Missing path: {p}\n{hint}")

    def _need_shp_set(self, shp: Path):
        sidecars = [shp.with_suffix(ext) for ext in (".shp", ".shx", ".dbf")]
        miss = [p for p in sidecars if not p.exists()]
        if miss:
            raise FileNotFoundError("Missing shapefile sidecars:\n  " + "\n  ".join(map(str, miss)))

    def load_eez_land_union(self) -> gpd.GeoDataFrame:
        self._need(self.eez_dir, "Put EEZ files under data/EEZ_land_union_v4_202410/")
        self._need(self.eez_path, "Expect EEZ_land_union_v4_202410.shp present")
        self._need_shp_set(self.eez_path)
        gdf = gpd.read_file(str(self.eez_path))
        if gdf.crs and gdf.crs.to_epsg() != 4326:
            gdf = gdf.to_crs(4326)
        return gdf

    def load_goas(self) -> gpd.GeoDataFrame:
        self._need(self.goas_split_dir, "Expected split gpkg files under data/GOaS_v1_20211214_gpkg/split/")
        files = sorted(glob.glob(str(self.goas_split_dir / "*.gpkg")))
        if not files:
            raise FileNotFoundError(f"No .gpkg files in {self.goas_split_dir}")
        frames = [gpd.read_file(fp) for fp in files]
        merged = gpd.GeoDataFrame(pd.concat(frames, ignore_index=True), crs=frames[0].crs)
        if merged.crs and merged.crs.to_epsg() != 4326:
            merged = merged.to_crs(4326)
        return merged
