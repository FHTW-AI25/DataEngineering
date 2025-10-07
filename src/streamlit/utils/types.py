from dataclasses import dataclass
from datetime import datetime

@dataclass
class AppConfig:
    # playback
    speed_hps: float
    # data source & tokens
    ds_choice: object
    mapbox_token: str

    # map config
    style_name: str
    style_url: str
    layer_mode: str

    # time range
    start_dt: datetime
    end_dt: datetime

    # filters
    mag_min: float
    mag_max: float
    depth_min: float
    depth_max: float
    tsunami_only: bool
    text_query: str
    networks_csv: str
    bbox: list | None