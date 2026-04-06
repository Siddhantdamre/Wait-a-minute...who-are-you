import networkx as nx
from knowledge.values import CORE_VALUES, VALUE_RELATIONS


class ValueGraph:
    def __init__(self):
        self.graph = nx.DiGraph()
        self._init_core_values()

    def _init_core_values(self):
        for v in CORE_VALUES:
            self.graph.add_node(v, type="Value")

        for src, rel, dst in VALUE_RELATIONS:
            self.graph.add_edge(src, dst, relation=rel)

    def activate_values_from_story(self, story_arc):
        """
        Very simple heuristic for now.
        Later this can use NLP / rules / feedback.
        """
        text = (
            story_arc.setup +
            story_arc.conflict +
            story_arc.climax +
            story_arc.moral
        ).lower()

        active = set()
        for value in CORE_VALUES:
            if value.lower() in text:
                active.add(value)

        # Always include moral-related values
        if "courage" in text:
            active.add("Courage")

        return list(active)

    def explain_tradeoffs(self, active_values):
        explanations = []

        for v in active_values:
            for _, target, data in self.graph.out_edges(v, data=True):
                if target in active_values:
                    explanations.append(
                        f"{v} {data['relation']} {target}"
                    )

        return explanations

    def to_json(self):
        return {
            "nodes": [
                {"id": n, "type": d.get("type")}
                for n, d in self.graph.nodes(data=True)
            ],
            "edges": [
                {"source": u, "target": v, "relation": d.get("relation")}
                for u, v, d in self.graph.edges(data=True)
            ],
        }
