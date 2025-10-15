# src/services/country_sea_manager.py
from __future__ import annotations
from typing import Iterable
import pandas as pd
from sqlmodel import SQLModel
from sqlalchemy import text
from location.data_loader import DataLoader
from data.db import get_engine, get_session
from models.models import Country, Sea

class CountrySeaManager:
    """
    Creates and populates lookup tables:
      - country(iso PK, name)
      - sea(id PK, name)
    Fills data from DataLoader’s EEZ (ISO_SOV1 / SOVEREIGN1) and GOaS ('name').
    """

    def __init__(self, loader: DataLoader | None = None):
        self.loader = loader or DataLoader()

    # --- schema ---
    def create_tables(self) -> None:
        # Ensure models are imported, then create the tables
        engine = get_engine()
        SQLModel.metadata.create_all(engine)

    # --- data ingestion ---
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

        sql = """
            INSERT INTO country (iso, name)
            VALUES (:iso, :name)
            ON CONFLICT (iso) DO UPDATE SET name = EXCLUDED.name
        """
        with get_session() as session:
            session.execute(  # <-- use execute, not exec
                text("""
                    INSERT INTO country (iso, name)
                    VALUES (:iso, :name)
                    ON CONFLICT (iso) DO UPDATE SET name = EXCLUDED.name
                """),
                df.to_dict(orient="records"),  # list[dict] -> executemany
            )
            session.commit()
        return len(df)

    def fill_sea(self) -> int:
        """
        Upsert 10 seas from GOaS into sea(id, name).
        ID assignment is stable: take the first occurrence order by original __row_id__,
        then enumerate 0..N-1 in that order.
        """
        goas = self.loader.load_goas()  # merged back, index==__row_id__

        # Find a 'name' column (case-insensitive)
        name_col = next((c for c in goas.columns if c.lower() == "name"), None)
        if not name_col:
            raise KeyError("GOaS data must contain a 'name' column.")

        # one row per sea name, in original appearance order
        # (sort by index/__row_id__ and drop duplicates keeping the first)
        seas_unique = (
            goas.reset_index()                                  # __row_id__ -> column
                .sort_values("__row_id__")
                .drop_duplicates(subset=[name_col], keep="first")
                [[name_col]]
                .reset_index(drop=True)
        )
        # assign ids 0..N-1
        seas_unique.insert(0, "id", range(len(seas_unique)))
        seas_unique = seas_unique.rename(columns={name_col: "name"})

        if seas_unique.empty:
            return 0

        # Upsert by primary key id
        sql = """
            INSERT INTO sea (id, name)
            VALUES (:id, :name)
            ON CONFLICT (id) DO UPDATE SET name = EXCLUDED.name
        """
        with get_session() as session:
            session.execute(
                text("""
                    INSERT INTO sea (id, name)
                    VALUES (:id, :name)
                    ON CONFLICT (id) DO UPDATE SET name = EXCLUDED.name
                """),
                seas_unique.to_dict(orient="records"),
            )
            session.commit()
        return len(seas_unique)

    def ensure_and_fill_all(self) -> tuple[int, int]:
        """Create tables if needed, then fill both. Returns (countries, seas)."""
        self.create_tables()
        return self.fill_country(), self.fill_sea()
