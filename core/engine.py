from datetime import datetime, timezone
from memory.schemas import MemoryEntry
from knowledge.rag import CulturalRAG
from memory import MemoryManager
from core.agent import StoryAgent
from core.cultural_intelligence_builder import CulturalIntelligenceBuilder
from core.narrative import NarrativePlanner
from spatial.spatial_inference import SpatialCultureInference
from spatial.temporal_inference import infer_values

class CulturalEngine:
    def __init__(self):
        # Use the classes/functions actually imported above
        self.spatial = SpatialCultureInference() 
        self.builder = CulturalIntelligenceBuilder()
        self.narrative = NarrativePlanner()

    def run(self, lat, lon, year, canonical_text, memory_bank):
        # 1. Temporal Refinement (using the imported function)
        # Assuming infer_values acts as the refinement step
        values, confidence = infer_values(lat, lon, year, memory_bank)

        # 3. Narrative Planning
        # Fixed: intent must be a dict for your NarrativePlanner
        narrative_state = self.narrative.plan(intent={"theme": canonical_text}, context_docs=[])
        
        # 4. Build Intelligence
        cultural_intel = self.builder.build(
            lat=lat, 
            lon=lon, 
            values=values, 
            story_arc=narrative_state
        )

        return narrative_state, cultural_intel

class StorytellingEngine:
    def __init__(self, agent: StoryAgent, memory: MemoryManager, rag: CulturalRAG):
        self.agent = agent
        self.memory = memory
        self.rag = rag
        self.cultural_core = CulturalEngine()

    def process(self, user_input: str, lat: float, lon: float, year: int):
        # Step 1: Logic & Narrative Generation
        # (Integrating the CulturalEngine here)
        story_arc, intel = self.cultural_core.run(lat, lon, year, user_input, self.memory)
        
        # Step 2: Render Final Text
        story_text = self.agent._render_story(story_arc)

        # Step 3: Persistence
        memory_entry = MemoryEntry(
            user_input=user_input,
            system_output=story_text,
            timestamp=datetime.now(timezone.utc), # Updated from utcnow()
            region=getattr(intel, "region", "unknown"),
            theme=user_input, # Or extract from intel
            modality="text"
        )
        self.memory.remember(memory_entry)

        return story_text