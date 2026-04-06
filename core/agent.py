# [AGENT] WEB SEARCH EDITION
# STORY: Pollinations (Cloud) - Fast & Creative
# IMAGE: DuckDuckGo Search (Real Web Results) - 100% Reliable
import json
import re
import requests
import urllib.parse
import wikipediaapi
import os
import sys

# --- STEP 0: AUTO-INSTALL SEARCH LIBRARY ---
# We verify and install 'duckduckgo-search' if missing
try:
    from duckduckgo_search import DDGS
except ImportError:
    print("[SYSTEM] Installing Search Engine Library...")
    os.system(f"{sys.executable} -m pip install -U duckduckgo-search")
    from duckduckgo_search import DDGS

from core.narrative import NarrativePlanner
from core.cultural_intelligence_builder import CulturalIntelligenceBuilder
from core.data_service import GlobalCultureManager

class StoryAgent:
    def __init__(self, api_keys: list):
        self.planner = NarrativePlanner(api_key="none")
        self.cultural_builder = CulturalIntelligenceBuilder()
        self.culture_manager = GlobalCultureManager()
        self.wiki = wikipediaapi.Wikipedia(user_agent='CulturalApp/WebSearch', language='en')

    def get_real_facts(self, country):
        try:
            page = self.wiki.page(f"History of {country}")
            if not page.exists(): page = self.wiki.page(country)
            if page.exists(): return page.summary[:1000].replace('\n', ' ')
        except: pass
        return f"History of {country}"

    def ask_pollinations_story(self, prompt):
        """Cloud API for Story (Kept as requested)"""
        try:
            url = "https://text.pollinations.ai/"
            headers = {"Content-Type": "application/json"}
            data = {"messages": [{"role": "user", "content": prompt}], "model": "openai", "jsonMode": True}
            response = requests.post(url, headers=headers, json=data, timeout=10)
            return response.text
        except: return "{}"

    # --- THE FIX: WEB IMAGE SEARCH ---
    def search_web_image(self, query):
        """Searches the web and returns the FIRST valid image URL."""
        print(f"[SEARCH] Looking for image: {query}...")
        try:
            # Simple synchronous search for 1 image
            with DDGS() as ddgs:
                results = list(ddgs.images(
                    keywords=query,
                    max_results=1,
                    safesearch='off', # Ensure we get historical/artistic results
                    type_image='photo' # Prefer photos/paintings over icons
                ))
                
            if results and len(results) > 0:
                image_url = results[0]['image']
                print(f"[SEARCH] Found: {image_url[:50]}...")
                return image_url
        except Exception as e:
            print(f"[SEARCH ERROR] {e}")
        
        # Fallback if search fails (e.g., connection issue)
        return "https://placehold.co/1280x720/black/white?text=Image+Not+Found"

    def clean_json(self, text):
        try:
            match = re.search(r'\{.*\}', text, re.DOTALL)
            if match: return json.loads(match.group(0))
        except: pass
        return {}

    def process(self, lat, lon, text="", era="Modern"): 
        # 1. Get Location & Facts
        profile = self.culture_manager.get_profile_by_coords(lat, lon)
        country = profile.get("Country", "Unknown")
        raw_facts = self.get_real_facts(country)
        formatted_history = "\n• " + "\n• ".join([s.strip() for s in raw_facts.split('.') if len(s) > 10][:3]) + "."

        # 2. Ask Cloud for Story
        story_prompt = f"""
        Act as a JSON API. Topic: Folklore of {country} in {era}. Theme: {text}.
        Context: {raw_facts[:500]}
        
        Task:
        1. Write a proper in-detail folklore story.
        2. Provide a Moral.
        3. Write a simple 5-word search query to find a real image of this setting (e.g. "1950 Brazil carnival vintage photo").
        
        Output JSON: {{ "story": "...", "moral": "...", "search_query": "..." }}
        """

        print(f"[AGENT] Fetching story for {country}...")
        raw_text = self.ask_pollinations_story(story_prompt)
        res_data = self.clean_json(raw_text)

        if not res_data.get("story"):
            res_data = {
                "story": f"In {era}, {country} stood strong. {raw_facts[:1000]}...",
                "moral": "Resilience endures.",
                "search_query": f"{country} {era} history culture"
            }

        # 3. SEARCH THE WEB FOR THE IMAGE
        search_query = res_data.get('search_query', f"{country} {era} culture")
        web_image_url = self.search_web_image(search_query)

        # 4. Build Result
        intel = self.cultural_builder.build(lat, lon, country, profile, {})
        intel_dict = intel.model_dump() if hasattr(intel, 'model_dump') else intel.dict()
        
        # Pass the Real Web URL
        intel_dict['image_url'] = web_image_url
        intel_dict['video_prompt'] = search_query
        
        full_narrative = f"{res_data.get('story')}\n\n**Moral:** {res_data.get('moral')}"
        intel_dict['cultural_history'] = formatted_history
        intel_dict['thought_signature'] = f"Hybrid (Story: AI | Image: Web Search)"
        
        return full_narrative, intel_dict
