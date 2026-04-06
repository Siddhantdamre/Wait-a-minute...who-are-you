"""
Global Workspace — CognitiveState

A structured, read-only snapshot of the system's current cognitive
state.  All modules (inspector, controller, memory, future planner)
can read from this single object instead of passing ad-hoc dicts.

Design principles:
  - Field names match the existing inspector dict keys so the
    CommitController can consume a CognitiveState via [] access
    without code changes (duck typing).
  - Extended fields (items_queried, current_goal, memory_summary,
    etc.) carry workspace-only data that did not exist before.
  - The dataclass is mutable so callers can annotate a snapshot
    after construction (e.g. record the controller's decision
    in next_action).
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Tuple


@dataclass
class CognitiveState:
    """
    Global Workspace snapshot.

    Canonical producer: BeliefInspector.workspace()
    Canonical consumers: CommitController.decide(), adapters, loggers.
    """

    # ── Belief state (mirrors inspector dict) ────────────────────────
    entropy: float = 0.0
    confidence_margin: float = 0.0
    top_hypotheses: List[Tuple[dict, float]] = field(default_factory=list)
    trust_distribution: Dict[str, float] = field(default_factory=dict)
    trusted_source_locked: bool = False
    query_rationale: str = ""

    # ── Extended workspace fields ────────────────────────────────────
    all_hypotheses: List[Tuple[dict, float]] = field(default_factory=list)
    items_queried: int = 0
    items_total: int = 0
    current_goal: str = ""
    next_action: str = ""           # filled by controller / adapter
    last_action_reason: str = ""    # filled by adapter after action
    episode_count: int = 0
    memory_summary: Dict[str, Any] = field(default_factory=dict)

    # ── Dict-like access for backward compatibility ──────────────────

    def __getitem__(self, key):
        """Allow workspace['confidence_margin'] style access."""
        try:
            return getattr(self, key)
        except AttributeError:
            raise KeyError(key)

    def get(self, key, default=None):
        """Dict-style .get() for safe access."""
        return getattr(self, key, default)

    def __contains__(self, key):
        return hasattr(self, key)

    def to_dict(self):
        """
        Convert to the plain dict format that BeliefInspector.inspect()
        returns, for full backward compatibility.
        """
        return {
            'entropy': self.entropy,
            'confidence_margin': self.confidence_margin,
            'top_hypotheses': self.top_hypotheses,
            'trust_distribution': self.trust_distribution,
            'trusted_source_locked': self.trusted_source_locked,
            'query_rationale': self.query_rationale,
        }
