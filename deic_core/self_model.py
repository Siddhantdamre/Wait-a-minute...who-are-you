"""
DEIC Self-Model Layer

This module provides a deterministic, explicit self-representation 
of the system's current cognitive state, derived from the Global 
Workspace (CognitiveState).

Purpose:
  - Explain *what* the system believes.
  - Explain *why* it is uncertain.
  - State its current goals and limitations.
  - Identify specific evidence that would change its mind.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
from .workspace import CognitiveState


@dataclass
class SelfModel:
    """
    A readable, high-level representation of the system's cognitive state.
    Generated deterministically from a CognitiveState snapshot.
    """

    # ── Summaries ───────────────────────────────────────────────────
    current_belief: str = ""
    confidence_description: str = ""
    uncertainty_rationale: str = ""
    goal_description: str = ""
    action_justification: str = ""
    limitation_warning: Optional[str] = None
    counterfactual_trigger: str = "No alternative hypothesis compelling enough to track."
    trust_status: str = ""

    # ── Original Data ───────────────────────────────────────────────
    workspace_snapshot: Optional[CognitiveState] = None

    @classmethod
    def from_workspace(cls, ws: CognitiveState):
        """
        Construct a SelfModel from a Global Workspace snapshot.
        
        Args:
            ws: The CognitiveState to summarize.
            
        Returns:
            A populated SelfModel instance.
        """
        sm = cls(workspace_snapshot=ws)

        # 1. Belief Summary
        sm.current_belief = cls._summarize_belief(ws)

        # 2. Confidence Description
        sm.confidence_description = cls._describe_confidence(ws)

        # 3. Uncertainty Rationale
        sm.uncertainty_rationale = cls._summarize_uncertainty(ws)

        # 4. Goal Description
        sm.goal_description = ws.current_goal

        # 5. Action Justification
        sm.action_justification = ws.query_rationale

        # 6. Limitations
        sm.limitation_warning = cls._detect_limitations(ws)

        # 7. Counterfactual Trigger
        sm.counterfactual_trigger = cls._derive_counterfactual(ws)

        # 8. Trust Status
        sm.trust_status = cls._summarize_trust(ws)

        return sm

    @staticmethod
    def _summarize_belief(ws: CognitiveState) -> str:
        if not ws.top_hypotheses:
            return "No active hypotheses."
        
        h_map, prob = ws.top_hypotheses[0]
        # Hypothesis format from engine.score_hypotheses():
        # {'shifted_items': frozenset(...), 'multiplier': float}
        s_list = h_map.get('shifted_items', [])
        m_val = h_map.get('multiplier', 0.0)
        
        return f"Primary candidate: group size {len(s_list)}, multiplier {m_val:.2f} (p={prob:.2%})"

    @staticmethod
    def _describe_confidence(ws: CognitiveState) -> str:
        margin = ws.confidence_margin
        if margin > 0.90:
            return f"Very High ({margin:.2f} margin)"
        if margin > 0.70:
            return f"High ({margin:.2f} margin)"
        if margin > 0.40:
            return f"Moderate ({margin:.2f} margin)"
        if margin > 0.10:
            return f"Low ({margin:.2f} margin)"
        return f"Minimal/None ({margin:.2f} margin)"

    @staticmethod
    def _summarize_uncertainty(ws: CognitiveState) -> str:
        n_active = len([h for h, p in ws.all_hypotheses if p > 1e-4])
        if n_active <= 1:
            return "Uncertainty is minimal; beliefs have largely converged."
        
        if not ws.trusted_source_locked:
            return f"High uncertainty due to unresolved trust (divergence among {len(ws.trust_distribution)} sources)."
        
        return f"Internal ambiguity remains among {n_active} structural interpretations."

    @staticmethod
    def _detect_limitations(ws: CognitiveState) -> Optional[str]:
        # Item total - items queried is a proxy for remaining capacity
        if ws.items_total > 0 and (ws.items_total - ws.items_queried) <= 1:
            return "Warning: Physical monitoring capacity nearly exhausted."
        
        if ws.entropy > 2.5:
            return "Critical: State space is too fragmented for reliable decision."
            
        return None

    @staticmethod
    def _derive_counterfactual(ws: CognitiveState) -> str:
        """
        Identify what specific observation would flip the MAP hypothesis.
        Compare H1 (MAP) vs H2 (Runner-up).
        """
        if len(ws.top_hypotheses) < 2:
            return "Confidence is absolute; no plausible counter-hypothesis exists."
        
        h1, p1 = ws.top_hypotheses[0]
        h2, p2 = ws.top_hypotheses[1]
        
        s1 = set(h1.get('shifted_items', []))
        s2 = set(h2.get('shifted_items', []))
        
        # Disagreeing items
        diff_1_not_2 = s1 - s2
        diff_2_not_1 = s2 - s1
        
        if diff_2_not_1:
            item = sorted(list(diff_2_not_1))[0]
            return f"If evidence confirms {item} is deteriorating, I would switch to my secondary hypothesis."
            
        if diff_1_not_2:
            item = sorted(list(diff_1_not_2))[0]
            return f"If evidence confirms {item} is stable, my primary hypothesis would lose viability."
            
        # If same S, check multiplier
        m1 = h1.get('multiplier', 0.0)
        m2 = h2.get('multiplier', 0.0)
        if abs(m1 - m2) > 0.01:
            return f"If items show a deviation magnitude closer to {m2:.2f} than {m1:.2f}, I would shift my estimate."
            
        return "Hypotheses are fundamentally distinct but item-level divergence is subtle."

    @staticmethod
    def _summarize_trust(ws: CognitiveState) -> str:
        if ws.trusted_source_locked:
            # Find the most trusted source
            best_s = max(ws.trust_distribution.items(), key=lambda x: x[1])
            return f"Source '{best_s[0]}' is identified as the reliable observer."
            
        n_sources = len(ws.trust_distribution)
        if n_sources == 0:
            return "No observers identified."
            
        avg_trust = sum(ws.trust_distribution.values()) / n_sources
        if avg_trust < 0.3:
            return "Significant cross-source conflict detected."
            
        return "Establishing observer reliability via consensus filtering."

    def __str__(self):
        """Preformatted human-readable output."""
        lines = [
            "─── DEIC Self-Model Snapshot ───",
            f"Belief:      {self.current_belief}",
            f"Confidence:  {self.confidence_description}",
            f"Goal:        {self.goal_description}",
            f"Justification: {self.action_justification}",
            f"Trigger:     {self.counterfactual_trigger}",
            f"Trust:       {self.trust_status}"
        ]
        if self.limitation_warning:
            lines.insert(1, f"!! LIMITATION: {self.limitation_warning}")
        return "\n".join(lines)
