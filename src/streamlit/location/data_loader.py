from __future__ import annotations
from pathlib import Path
import glob
import geopandas as gpd
import pandas as pd

class DataLoader:
    """
    Loads EEZ + GOaS data for the app.

    - GOaS: assumes you only have split files on disk (one GPKG per ocean),
      each written with a saved '__row_id__' column and a layer named 'ocean'.
      Merges them back into one GeoDataFrame and restores original row order/index.

    - EEZ: loads the shapefile directly.
    """

    # --- default locations (adjust if your structure differs) ---
    EEZ_PATH = Path("../../../data/EEZ_land_union_v4_202410/EEZ_land_union_v4_202410.shp")
    GOAS_SPLIT_DIR = Path("../../../data/GOaS_v1_20211214_gpkg/split")
    GOAS_LAYER = "ocean"   # layer name used when writing split files

    def load_eez_land_union(self) -> gpd.GeoDataFrame:
        gdf = gpd.read_file(self.EEZ_PATH)
        if gdf.crs is not None and gdf.crs.to_epsg() != 4326:
            gdf = gdf.to_crs(4326)
        return gdf  # keep full schema as-is

    def load_goas(self) -> gpd.GeoDataFrame:
        # Merge all split GPKGs back into one GeoDataFrame
        pattern = str(self.GOAS_SPLIT_DIR / "*.gpkg")
        files = sorted(glob.glob(pattern))
        if not files:
            raise FileNotFoundError(
                f"No split GOaS files found under: {self.GOAS_SPLIT_DIR} (pattern {pattern})"
            )

        frames = []
        for fp in files:
            try:
                # preferred: read the explicit layer we wrote
                frames.append(gpd.read_file(fp, layer=self.GOAS_LAYER))
            except Exception:
                # fallback: read default layer if 'ocean' wasn't used
                frames.append(gpd.read_file(fp))

        merged = gpd.GeoDataFrame(pd.concat(frames, ignore_index=True), crs=frames[0].crs)

        # CRS -> WGS84 (lon/lat), just in case parts differ
        if merged.crs is not None and merged.crs.to_epsg() != 4326:
            merged = merged.to_crs(4326)

        # Restore original row order/index using the saved ID
        if "__row_id__" not in merged.columns:
            raise KeyError(
                "Missing '__row_id__' in merged GOaS data. "
                "Make sure you added it before splitting (gdf['__row_id__']=gdf.index)."
            )

        merged = merged.sort_values("__row_id__").reset_index(drop=True)
        merged = merged.set_index("__row_id__", drop=True)

        return merged

    # Optional convenience
    def load_all(self) -> tuple[gpd.GeoDataFrame, gpd.GeoDataFrame]:
        """Returns (eez_land_union, goas)."""
        return self.load_eez_land_union(), self.load_goas()
