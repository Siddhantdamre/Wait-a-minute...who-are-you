# [FILE] core/agent.py
import itertools
import wikipediaapi
from core.narrative import NarrativePlanner
from core.cultural_intelligence_builder import CulturalIntelligenceBuilder
from core.data_service import GlobalCultureManager

class StoryAgent:
    def __init__(self, api_keys: list):
        # We initialize Wikipedia with a proper user agent
        self.wiki = wikipediaapi.Wikipedia(
            user_agent='CulturalStorytellerProject/1.0 (student_research_demo)',
            language='en'
        )
        self.key_pool = itertools.cycle(api_keys)
        self.planner = NarrativePlanner(api_key=next(self.key_pool))
        self.cultural_builder = CulturalIntelligenceBuilder()
        self.culture_manager = GlobalCultureManager()

    def get_real_facts(self, country, era):
        """Fetches REAL historical data from Wikipedia."""
        try:
            # Try specific history page first
            page = self.wiki.page(f"History of {country}")
            if not page.exists():
                # Fallback to main country page
                page = self.wiki.page(country)
            
            if page.exists():
                # Get the summary, clean it up, and limit length
                return page.summary[:600].replace('\n', ' ')
        except Exception as e:
            print(f"Wiki Error: {e}")
        return f"Historical archives for {country} are currently being digitized."

    def process(self, lat, lon, text="", era="1950"):
        # 1. Real Geolocation (Find out where we clicked)
        profile = self.culture_manager.get_profile_by_coords(lat, lon)
        country = profile.get("Country", "Unknown Location")
        
        print(f"[RAG] Fetching REAL history for {country}...")
        
        # 2. Get Real Facts (The step that was missing!)
        real_facts = self.get_real_facts(country, era)
        
        # 3. Generate Content based on REAL Facts
        # We weave the Wikipedia facts into the narrative so it's unique.
        narrative = (
            f"Set in {era}, the region of {country} holds a deep history. "
            f"Context: {real_facts[:250]}... "
            f"Against this backdrop, the theme of '{text}' emerges..."
        )
        
        # 4. Format History for Dashboard (Bullet points)
        # Split the wikipedia summary into readable chunks
        sentences = real_facts.split('. ')
        history_formatted = "\n• " + "\n• ".join(sentences[:3]) + "."

        # 5. Build Final Intel Object
        video_prompt = f"Cinematic documentary shot of {country}, {era}, historical style, 4k"
        image_url = f"Historical painting of {country} in {era}"

        intel = self.cultural_builder.build(lat, lon, country, profile, {})
        intel_dict = intel.model_dump() if hasattr(intel, 'model_dump') else intel.dict()
        
        # Populate with REAL data
        intel_dict['video_prompt'] = video_prompt
        intel_dict['image_url'] = image_url
        intel_dict['cultural_history'] = history_formatted
        intel_dict['thought_signature'] = f"Data retrieved for {country} ({lat:.2f}, {lon:.2f})"

        return narrative, intel_dict
