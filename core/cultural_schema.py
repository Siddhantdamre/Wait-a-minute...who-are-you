from pydantic import BaseModel
from typing import List, Dict, Any, Optional

class CulturalNorm(BaseModel):
    description: str
    importance: float

class CulturalRisk(BaseModel):
    risk: str
    severity: float
    explanation: str

class CulturalNarrative(BaseModel):
    theme: str
    explanation: str

class CulturalIntelligence(BaseModel):
    location: Dict[str, float]
    country: str = "Unknown"
    behavior_scores: Optional[Dict[str, Any]] = {}
    inferred_values: Optional[List[str]] = []
    confidence: float = 0.0
    norms: Optional[List[CulturalNorm]] = []
    do_and_dont: Optional[Dict[str, List[str]]] = {}
    narratives: Optional[List[CulturalNarrative]] = []
    risks: Optional[List[CulturalRisk]] = []
    explanation: str = ""
    
    # AGENTIC & MULTIMODAL DATA
    image_url: Optional[str] = None
    video_url: Optional[str] = None
    voice_url: Optional[str] = None
    cultural_history: Optional[str] = None
    current_era: Optional[str] = "Modern"
    thought_signature: Optional[str] = None
    memory_id: Optional[str] = None