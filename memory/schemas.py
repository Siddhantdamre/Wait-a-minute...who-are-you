from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class MemoryEntry(BaseModel):
    user_input: str
    system_output: str
    timestamp: datetime
    region: Optional[str] = None
    theme: Optional[str] = None
    modality: Optional[str] = "text"  # text | voice | image
