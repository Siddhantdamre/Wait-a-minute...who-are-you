from core.narrative import StoryArc
from knowledge.graph import KnowledgeGraphBuilder

arc = StoryArc(
    setup="In a quiet village...",
    inciting_event="A challenge appeared...",
    conflict="Fear spread...",
    climax="The hero acted bravely...",
    resolution="Peace returned...",
    moral="Courage protects community."
)

kg = KnowledgeGraphBuilder()
graph = kg.build_from_story(arc, region="Maharashtra")

print("\nGRAPH JSON:")
print(kg.to_json())

print("\nEXPLANATION:")
for line in kg.explain():
    print("-", line)
