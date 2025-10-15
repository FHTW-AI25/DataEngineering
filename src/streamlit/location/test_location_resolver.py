from data_loader import DataLoader
from location_resolver import LocationResolver

test_points = [
    (42.5, -87.0, "Lake Michigan, USA — Wasser"),
    (33.0, -97.0, "Dallas, TX, USA — Land"),
    (40.0, -127.0, "Off California, USA — EEZ Wasser"),
    (0.0, -120.0, "Equatorial Pacific — International Waters Wasser"),
    (23, 121, "Taiwan Island - Land"),
    (-89, 0, "Antarctica"),
]

# Use DataLoader (paths are set inside the class)
loader = DataLoader()
eez_land_union = loader.load_eez_land_union()
goas = loader.load_goas()  # merges your split GOaS files and restores order

location_resolver = LocationResolver(eez_land_union, goas)

for lat, lon, note in test_points:
    location = location_resolver.resolve(lat, lon)
    print(f"{note}: {location.country}, {location.sea}")
