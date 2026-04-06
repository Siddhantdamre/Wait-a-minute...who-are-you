from typing import List, Dict

class NarrativeState:
    def __init__(
        self,
        setting: str,
        values: List[str],
        emotion_curve: List[str],
        moral: str,
        visual_motifs: List[str],
        confidence: float
    ):
        self.setting = setting
        self.values = values
        self.emotion_curve = emotion_curve
        self.moral = moral
        self.visual_motifs = visual_motifs
        self.confidence = confidence
