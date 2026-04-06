from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional


class AutobiographicalEntry(BaseModel):
    user_id: Optional[str]
    region: Optional[str]
    story_theme: str
    active_values: List[str]
    confidence: float
    user_feedback: Optional[str]  # agree | disagree | correction
    timestamp: datetime
