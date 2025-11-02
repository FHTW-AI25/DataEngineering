from dataclasses import dataclass
from datetime import datetime
from typing import Literal, Optional, List, Tuple

LocationMode = Literal["both", "land", "sea"]

@dataclass
class AppConfig:
    # Playback
    speed_hps: float

    # Map/token
    mapbox_token: str
    style_name: str
    style_url: str
    layer_mode: str

    # Time range (UTC datetimes)
    start_dt: datetime
    end_dt: datetime

    # Filters
    location_mode: LocationMode
    filter_by_country: bool
    country_isos: Optional[List[str]]
    mag_min: float
    mag_max: float
    depth_min: float
    depth_max: float
    tsunami_only: bool
    text_query: str
    networks_csv: str

    # Bounding box: (min_lon, min_lat, max_lon, max_lat)
    bbox: Optional[Tuple[float, float, float, float]]