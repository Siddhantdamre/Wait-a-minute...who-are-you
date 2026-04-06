from core.narrative import StoryArc
from expression.storyboard import StoryboardBuilder

arc = StoryArc(
    setup="In a quiet village, the sun rose over small houses.",
    inciting_event="A sudden challenge tested the people.",
    conflict="Fear spread as the danger grew.",
    climax="A brave act changed everything.",
    resolution="Peace returned to the village.",
    moral="Courage protects community."
)

builder = StoryboardBuilder()
files = builder.build(arc)

print("\nGenerated storyboard images:")
for f in files:
    print(f)
