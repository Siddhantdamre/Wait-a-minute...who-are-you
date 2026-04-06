# [FILE] core/cultural_intelligence_builder.py
# Restoring this dependency so agent.py imports don't crash
from pydantic import BaseModel
from typing import Any, Dict

class Intel(BaseModel):
    country: str
    cultural_history: str = ""
    thought_signature: str = ""
    current_era: str = ""
    image_url: str = ""
    video_prompt: str = ""
    behavior_scores: Dict[str, Any] = {}

class CulturalIntelligenceBuilder:
    def build(self, lat, lon, country, profile, story_arc):
        return Intel(
            country=country,
            behavior_scores=profile
        )
