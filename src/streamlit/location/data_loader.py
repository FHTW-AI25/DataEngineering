# src/data_loader.py
from __future__ import annotations
from pathlib import Path
import glob
import geopandas as gpd
import pandas as pd
import fiona

class DataLoader:
    def __init__(self) -> None:
        # project_root = parent of "src/" (because this file lives in src/)
        self.project_root = Path(__file__).resolve().parents[1]
        self.data_dir = (self.project_root / "data").resolve()
        self.eez_dir = self.data_dir / "EEZ_land_union_v4_202410"
        self.eez_path = self.eez_dir / "EEZ_land_union_v4_202410.shp"
        self.goas_split_dir = self.data_dir / "GOaS_v1_20211214_gpkg" / "split"

    def _require_exists(self, path: Path, hint: str = "") -> None:
        if not path.exists():
            raise FileNotFoundError(f"Missing path: {path}\n{hint}")

    def _require_shapefile_set(self, shp: Path) -> None:
        required = [shp.with_suffix(ext) for ext in (".shp", ".shx", ".dbf")]
        missing = [p for p in required if not p.exists()]
        if missing:
            raise FileNotFoundError(
                "Shapefile sidecar(s) missing:\n  " + "\n  ".join(map(str, missing)) +
                f"\nMake sure the whole shapefile set is under: {shp.parent}"
            )

    def load_eez_land_union(self) -> gpd.GeoDataFrame:
        # sanity checks with helpful hints
        self._require_exists(self.data_dir, "Expected a top-level 'data/' directory.")
        self._require_exists(self.eez_dir, "Put EEZ files under 'data/EEZ_land_union_v4_202410/'.")
        self._require_exists(self.eez_path, "Expected 'EEZ_land_union_v4_202410.shp' in 'data/eez/'.")
        self._require_shapefile_set(self.eez_path)

        gdf = gpd.read_file(str(self.eez_path))
        if gdf.crs and gdf.crs.to_epsg() != 4326:
            gdf = gdf.to_crs(4326)
        return gdf

    def _read_single_layer(self, fp: str) -> gpd.GeoDataFrame:
        layers = fiona.listlayers(fp)
        layer = "ocean" if "ocean" in layers else (layers[0] if layers else None)
        if layer is None:
            raise ValueError(f"No layers found in {fp}")
        return gpd.read_file(fp, layer=layer)

    def load_goas(self) -> gpd.GeoDataFrame:
        self._require_exists(self.goas_split_dir, "Expected GOaS split files under 'data/GOaS_v1_20211214_gpkg/split/'.")
        files = sorted(glob.glob(str(self.goas_split_dir / "*.gpkg")))
        if not files:
            raise FileNotFoundError(f"No '*.gpkg' files found in {self.goas_split_dir}")

        frames = [self._read_single_layer(fp) for fp in files]
        merged = gpd.GeoDataFrame(pd.concat(frames, ignore_index=True), crs=frames[0].crs)

        if merged.crs and merged.crs.to_epsg() != 4326:
            merged = merged.to_crs(4326)

        if "__row_id__" not in merged.columns:
            raise KeyError(
                "Missing '__row_id__' in GOaS split files. "
                "Add it before splitting (gdf['__row_id__']=gdf.index)."
            )

        merged = merged.sort_values("__row_id__").reset_index(drop=True).set_index("__row_id__", drop=True)
        return merged

    def load_all(self):
        return self.load_eez_land_union(), self.load_goas()
