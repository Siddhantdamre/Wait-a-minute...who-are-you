from core.narrative import StoryArc
from core.verification import SelfVerificationEngine
import networkx as nx

arc = StoryArc(
    setup="A village lived peacefully.",
    inciting_event="A threat emerged.",
    conflict="Fear spread.",
    climax="Courage prevailed.",
    resolution="Peace returned.",
    moral="Courage protects community."
)

context_docs = [{"content": "A folk story from Maharashtra."}]
kg = nx.DiGraph()
kg.add_node("Hero")
active_values = ["Courage", "Community"]

verifier = SelfVerificationEngine()
result = verifier.verify(
    story_arc=arc,
    context_docs=context_docs,
    knowledge_graph=kg,
    value_graph=None,
    active_values=active_values
)

print("\nVERIFICATION RESULT:")
print(result)
