from pydantic import BaseModel
from typing import List


class InteractionPrompt(BaseModel):
    question: str
    options: List[str]
    arc_point: str  # conflict | climax

class InteractionEngine:
    def generate_prompt(self, story_arc) -> InteractionPrompt:
        return InteractionPrompt(
            question="What do you think the hero should do now?",
            options=[
                "Face the danger bravely",
                "Ask others for help",
                "Avoid the danger"
            ],
            arc_point="conflict"
        )

    def apply_choice(self, choice: str, story_arc):
        # Light branching — NOT full rewrite
        if "bravely" in choice.lower():
            story_arc.climax = (
                "Summoning inner strength, the hero stepped forward without fear."
            )
        elif "help" in choice.lower():
            story_arc.climax = (
                "Realizing wisdom in unity, the hero sought help and stood together."
            )
        else:
            story_arc.climax = (
                "Though hesitation slowed the moment, courage eventually emerged."
            )

        return story_arc
