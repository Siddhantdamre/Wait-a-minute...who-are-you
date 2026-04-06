from core.narrative import StoryArc
from knowledge.value_graph import ValueGraph

arc = StoryArc(
    setup="A peaceful village depended on its people.",
    inciting_event="A danger threatened the community.",
    conflict="Fear made safety tempting.",
    climax="The hero acted with courage.",
    resolution="The village was protected.",
    moral="True courage protects the community."
)

vg = ValueGraph()
active = vg.activate_values_from_story(arc)

print("\nACTIVE VALUES:")
print(active)

print("\nVALUE TRADE-OFFS:")
for e in vg.explain_tradeoffs(active):
    print("-", e)
