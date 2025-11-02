from __future__ import annotations
import pandas as pd
from sqlalchemy import text
from earthquakes_common import get_session   # shared DB
from .data_loader import DataLoader

class CountrySeaManager:
    def __init__(self, loader: DataLoader | None = None):
        self.loader = loader or DataLoader()

    def fill_country(self) -> int:
        eez = self.loader.load_eez_land_union()
        if "ISO_SOV1" not in eez.columns or "SOVEREIGN1" not in eez.columns:
            raise KeyError("EEZ must contain ISO_SOV1 and SOVEREIGN1")
        df = (
            pd.DataFrame({
                "iso": eez["ISO_SOV1"].astype(str).str.strip().str.upper(),
                "name": eez["SOVEREIGN1"].astype(str).str.strip(),
            })
            .replace({"": pd.NA, "NONE": pd.NA, "NA": pd.NA, "N/A": pd.NA})
            .dropna(subset=["iso", "name"])
            .drop_duplicates(subset=["iso"], keep="first")
        )
        if df.empty:
            return 0
        with get_session() as s:
            s.execute(
                text("""
                    INSERT INTO country (iso, name)
                    VALUES (:iso, :name)
                    ON CONFLICT (iso) DO UPDATE SET name = EXCLUDED.name
                """),
                df.to_dict(orient="records"),
            )
            s.commit()
        return len(df)

    def fill_sea(self) -> int:
        goas = self.loader.load_goas()
        name_col = next((c for c in goas.columns if c.lower() == "name"), None)
        if not name_col:
            raise KeyError("GOaS must contain a 'name' column")
        seas = (goas[[name_col]]
                .dropna()
                .drop_duplicates()
                .reset_index(drop=True)
                .rename(columns={name_col: "name"}))
        seas.insert(0, "id", range(len(seas)))
        with get_session() as s:
            s.execute(
                text("""
                    INSERT INTO sea (id, name)
                    VALUES (:id, :name)
                    ON CONFLICT (id) DO UPDATE SET name = EXCLUDED.name
                """),
                seas.to_dict(orient="records"),
            )
            s.commit()
        return len(seas)

    def fill_all(self) -> tuple[int, int]:
        return self.fill_country(), self.fill_sea()
