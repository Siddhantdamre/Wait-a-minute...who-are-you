from pydantic import BaseModel
from typing import List


class VerificationResult(BaseModel):
    confidence: float  # 0.0 – 1.0
    grounded: bool
    consistent: bool
    value_aligned: bool
    warnings: List[str]

class SelfVerificationEngine:
    def verify(
        self,
        story_arc,
        context_docs,
        knowledge_graph,
        value_graph,
        active_values
    ) -> VerificationResult:

        warnings = []

        # 1️⃣ RAG grounding check
        grounded = bool(context_docs)
        if not grounded:
            warnings.append("Story not grounded in external sources.")

        # 2️⃣ Narrative completeness
        consistent = all([
            story_arc.setup,
            story_arc.inciting_event,
            story_arc.conflict,
            story_arc.climax,
            story_arc.resolution,
            story_arc.moral
        ])
        if not consistent:
            warnings.append("Narrative arc incomplete.")

        # 3️⃣ Knowledge graph sanity
        if knowledge_graph.number_of_nodes() == 0:
            warnings.append("Knowledge graph is empty.")

        # 4️⃣ Value reasoning sanity
        value_aligned = len(active_values) > 0
        if not value_aligned:
            warnings.append("No explicit values detected.")

        # Confidence score (simple but explainable)
        confidence = (
            (1 if grounded else 0) +
            (1 if consistent else 0) +
            (1 if value_aligned else 0)
        ) / 3.0

        return VerificationResult(
            confidence=confidence,
            grounded=grounded,
            consistent=consistent,
            value_aligned=value_aligned,
            warnings=warnings
        )
