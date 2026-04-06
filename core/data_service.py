# [FILE] core/data_service.py
# YOUR EXACT CODE
import pandas as pd
from typing import Any
from geopy.geocoders import Nominatim

class GlobalCultureManager:
    def __init__(self, master_data_path="data/world_cultural_profiles.csv"):
        try:
            self.db = pd.read_csv(master_data_path)
        except FileNotFoundError:
            print(f"Error: {master_data_path} not found.")
            self.db = pd.DataFrame()
            
        self.geolocator = Nominatim(user_agent="smart_storyteller_v1")

    def get_profile_by_coords(self, lat: float, lon: float):
        # Default Fallback Profile to prevent crashes
        fallback_profile = {
            "Country": "Global Baseline",
            "Family_Importance": 0.5,
            "pdi": 50,
            "idv": 50,
            "Trust_In_People": 0.3
        }

        try:
            # We use 'Any' to bypass the incorrect type warnings for language and timeout
            location: Any = self.geolocator.reverse(
                f"{lat}, {lon}", 
                language="en", # type: ignore
                timeout=float(10) # type: ignore
            )
            
            # Check if location was actually found
            if location is None:
                return fallback_profile  # <--- FIXED: Return fallback instead of None
            
            address_data = location.raw.get('address', {})
            country_name = address_data.get('country')
            
            if not country_name:
                return fallback_profile # <--- FIXED

            # Find the cultural data in our CSV
            profile_row = self.db[self.db['Country'].str.lower() == country_name.lower()]

            if not profile_row.empty:
                return profile_row.to_dict('records')[0]
            else:
                # Return generic baseline but with the correct Country Name found
                fallback_profile["Country"] = country_name
                return fallback_profile
            
        except Exception as e:
            print(f"Geocoding Error: {e}")
            return fallback_profile  # <--- FIXED: Return fallback on error
