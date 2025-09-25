class DataSource:
    """Interface for a data source that returns a GeoJSON feed."""
    def name(self) -> str: ...
    def get_endpoint(self, **kwargs) -> str: ...

class LiveUSGSDataSource(DataSource):
    def name(self): return "USGS (live, last 24h)"
    def get_endpoint(self, **kwargs) -> str:
        return "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_day.geojson"

class CustomAPIDataSource(DataSource):
    def name(self): return "Custom API (prepared)"
    def get_endpoint(self, **kwargs) -> str:
        # Example for your future backend:
        # return f"https://your-api/earthquakes?start={kwargs['start_ms']}&end={kwargs['end_ms']}"
        return "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_day.geojson"

DATA_SOURCES = [LiveUSGSDataSource(), CustomAPIDataSource()]
