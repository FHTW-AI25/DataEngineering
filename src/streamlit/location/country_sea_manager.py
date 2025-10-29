from __future__ import annotations
import pandas as pd
from sqlalchemy import text

from location.data_loader import DataLoader
from data.db import get_session


class CountrySeaManager:
    """
    Populates lookup tables:
      - country(iso PK, name)
      - sea(id PK, name)

    Data comes from:
      - EEZ polygons (for countries)
      - GOaS polygons (for seas)
    Assumes tables are already created by init SQL.
    """

    def __init__(self, loader: DataLoader | None = None):
        self.loader = loader or DataLoader()

    def fill_country(self) -> int:
        """Upsert unique (iso, name) from EEZ into country table. Returns rows written."""
        eez = self.loader.load_eez_land_union()

        if "ISO_SOV1" not in eez.columns or "SOVEREIGN1" not in eez.columns:
            raise KeyError("EEZ data must contain 'ISO_SOV1' and 'SOVEREIGN1' columns.")

        df = (
            pd.DataFrame({
                "iso": eez["ISO_SOV1"].astype(str).str.strip().str.upper(),
                "name": eez["SOVEREIGN1"].astype(str).str.strip(),
            })
            .replace({"": pd.NA, "NONE": pd.NA, "NA": pd.NA, "N/A": pd.NA})
            .dropna(subset=["iso", "name"])
            .drop_duplicates(subset=["iso"], keep="first")
            .reset_index(drop=True)
        )

        if df.empty:
            return 0

        with get_session() as session:
            session.execute(
                text("""
                    INSERT INTO country (iso, name)
                    VALUES (:iso, :name)
                    ON CONFLICT (iso)
                    DO UPDATE SET name = EXCLUDED.name
                """),
                df.to_dict(orient="records"),  # executemany
            )
            session.commit()

        return len(df)

    def fill_sea(self) -> int:
        """
        Upsert seas into sea(id, name).
        ID assignment is stable: first appearance in GOaS order.
        """
        goas = self.loader.load_goas()  # merged back, index == __row_id__

        name_col = next((c for c in goas.columns if c.lower() == "name"), None)
        if not name_col:
            raise KeyError("GOaS data must contain a 'name' column.")

        seas_unique = (
            goas.reset_index()  # __row_id__ becomes column
                .sort_values("__row_id__")
                .drop_duplicates(subset=[name_col], keep="first")
                [[name_col]]
                .reset_index(drop=True)
        )

        seas_unique.insert(0, "id", range(len(seas_unique)))
        seas_unique = seas_unique.rename(columns={name_col: "name"})

        if seas_unique.empty:
            return 0

        with get_session() as session:
            session.execute(
                text("""
                    INSERT INTO sea (id, name)
                    VALUES (:id, :name)
                    ON CONFLICT (id)
                    DO UPDATE SET name = EXCLUDED.name
                """),
                seas_unique.to_dict(orient="records"),
            )
            session.commit()

        return len(seas_unique)

    def fill_all(self) -> tuple[int, int]:
        """
        Fill both country and sea tables.
        Assumes schema was created by init SQL (01_schema.sql).
        Returns (num_countries_upserted, num_seas_upserted).
        """
        c = self.fill_country()
        s = self.fill_sea()
        return c, s
