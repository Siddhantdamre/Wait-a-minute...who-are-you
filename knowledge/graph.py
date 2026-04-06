import networkx as nx


class KnowledgeGraphBuilder:
    def __init__(self):
        self.graph = nx.DiGraph()

    def add_node(self, name: str, node_type: str):
        self.graph.add_node(name, type=node_type)

    def add_edge(self, src: str, relation: str, dst: str):
        self.graph.add_edge(src, dst, relation=relation)

    def build_from_story(self, story_arc, region=None):
        # Core entities
        self.add_node("Hero", "Character")
        self.add_node("Village", "Place")
        self.add_node("Courage", "Value")
        self.add_node("Peace", "Value")

        # Relations
        self.add_edge("Hero", "shows", "Courage")
        self.add_edge("Hero", "protects", "Village")
        self.add_edge("Courage", "leads_to", "Peace")

        if region:
            self.add_node(region, "Region")
            self.add_edge("Village", "located_in", region)

        return self.graph

    def to_json(self):
        nodes = [
            {"id": n, "type": d.get("type")}
            for n, d in self.graph.nodes(data=True)
        ]
        edges = [
            {"source": u, "target": v, "relation": d.get("relation")}
            for u, v, d in self.graph.edges(data=True)
        ]
        return {"nodes": nodes, "edges": edges}

    def explain(self):
        explanations = []
        for u, v, d in self.graph.edges(data=True):
            explanations.append(
                f"{u} {d['relation']} {v}"
            )
        return explanations

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
