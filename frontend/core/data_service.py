# [FILE] core/data_service.py
import pandas as pd
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut

class GlobalCultureManager:
    def __init__(self, master_data_path="data/world_cultural_profiles.csv"):
        self.geolocator = Nominatim(user_agent="cultural_storyteller_vFinal")

    def get_profile_by_coords(self, lat: float, lon: float):
        try:
            # REAL Geocoding Logic
            location = self.geolocator.reverse(f"{lat}, {lon}", language="en", timeout=5)
            
            if not location:
                return {"Country": "Unknown Location", "idv": 50, "pdi": 50}
            
            address = location.raw.get('address', {})
            country = address.get('country', "Unknown Country")
            
            # Return Data (Dynamic Country, Default Stats for stability)
            return {
                "Country": country,
                "idv": 60, "pdi": 40, "mas": 50, "uai": 70, "lto": 45
            }
        except Exception as e:
            print(f"Geo Error: {e}")
            return {"Country": "Connection Error", "idv": 50, "pdi": 50}
