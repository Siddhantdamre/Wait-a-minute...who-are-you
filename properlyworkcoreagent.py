%%writefile core/agent.py
# [AGENT] POLLINATIONS CLOUD (Free, No Key, Smart)
# ERA LOGIC: Strictly follows the frontend slider.
import json
import re
import requests
import urllib.parse
import wikipediaapi
from core.narrative import NarrativePlanner
from core.cultural_intelligence_builder import CulturalIntelligenceBuilder
from core.data_service import GlobalCultureManager

class StoryAgent:
    def __init__(self, api_keys: list):
        # No keys needed for this method
        self.planner = NarrativePlanner(api_key="none")
        self.cultural_builder = CulturalIntelligenceBuilder()
        self.culture_manager = GlobalCultureManager()
        self.wiki = wikipediaapi.Wikipedia(user_agent='CulturalApp/FreeCloud', language='en')

    def get_real_facts(self, country):
        try:
            # Fetch general history to give the AI context
            page = self.wiki.page(f"History of {country}")
            if not page.exists(): page = self.wiki.page(country)
            if page.exists(): return page.summary[:800].replace('\n', ' ')
        except: pass
        return f"History of {country}"

    def ask_pollinations_cloud(self, prompt):
        """Hits the Free Pollinations Text API."""
        try:
            safe_prompt = urllib.parse.quote(prompt)
            # We specifically ask for OpenAI model via Pollinations for best quality
            url = f"https://text.pollinations.ai/{safe_prompt}?model=openai"
            response = requests.get(url, timeout=10)
            return response.text
        except Exception as e:
            print(f"[CLOUD ERROR] {e}")
            return "{}"

    def clean_json(self, text):
        try:
            match = re.search(r'\{.*\}', text, re.DOTALL)
            if match: return json.loads(match.group(0))
        except: pass
        return {}

    def process(self, lat, lon, text="", era="Modern"): 
        # Note: 'era' here comes directly from the frontend slider
        
        # 1. Get Location & Facts
        profile = self.culture_manager.get_profile_by_coords(lat, lon)
        country = profile.get("Country", "Unknown")
        facts = self.get_real_facts(country)

        # 2. Ask the Cloud (Dynamic Era)
        prompt = f"""
        Act as a JSON API. 
        Analyze: {country} during the year {era}.
        Theme: {text}
        Historical Context: {facts[:300]}
        
        Task:
        1. Write a 2-sentence story about {country} specifically set in {era}.
        2. Write a visual image prompt for that specific era and story.
        
        Return JSON ONLY:
        {{
            "story": "...",
            "image_prompt": "..."
        }}
        """

        res_data = {}
        print(f"[CLOUD] Generating story for {country} in {era}...")
        
        raw_text = self.ask_pollinations_cloud(prompt)
        res_data = self.clean_json(raw_text)

        # Fallback (Uses the slider 'era' variable, not a fixed date)
        if not res_data.get("story"):
            res_data = {
                "story": f"In the year {era}, {country} was defined by its enduring spirit. {facts[:150]}...",
                "image_prompt": f"Historical painting of {country} in the year {era}, highly detailed"
            }

        # 3. Build Result
        intel = self.cultural_builder.build(lat, lon, country, profile, {})
        intel_dict = intel.model_dump() if hasattr(intel, 'model_dump') else intel.dict()
        
        intel_dict['video_prompt'] = res_data.get('image_prompt', f"View of {country} in {era}")
        intel_dict['image_url'] = res_data.get('image_prompt', f"View of {country} in {era}")
        intel_dict['cultural_history'] = f"• Context ({era}): {facts[:500]}..."
        intel_dict['thought_signature'] = f"Pollinations Cloud ({era})"
        
        return res_data.get('story', 'No story generated.'), intel_dict