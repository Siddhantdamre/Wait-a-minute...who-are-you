from core.narrative import StoryArc
from expression.narration import StoryNarrator

arc = StoryArc(
    setup="In a quiet village, the sun rose gently.",
    inciting_event="One day, a test of courage appeared.",
    conflict="Fear tried to hold the hero back.",
    climax="At the final moment, courage won.",
    resolution="Peace returned to the village.",
    moral="Courage grows when fear is faced."
)

narrator = StoryNarrator()
files = narrator.narrate_arc(arc)

print("\nGenerated audio files:")
for f in files:
    print(f)
