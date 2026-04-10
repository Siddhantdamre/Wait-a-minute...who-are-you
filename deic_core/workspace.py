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
    trust_lock_turn: int = -1
    active_hypotheses_count: int = 0
    trust_evidence: dict = field(default_factory=dict)
    suspicion_scores: dict = field(default_factory=dict)
    is_flagged: bool = False
    reset_count: int = 0
    suspicion_triggers: int = 0

    # ── Structure Adaptation telemetry (Phase 14/15) ──────────────────
    adaptation_count: int = 0
    current_family_spec: str = ""
    candidate_specs_tested: List[str] = field(default_factory=list)
    family_search_trigger: str = ""    # "" | "rule0_structural_contradiction"
    family_search_outcome: str = ""    # "" | "adopted" | "rejected" | "exhausted" | "escalated"
    adaptation_turn: int = -1
    remaining_budget_at_adaptation: int = -1
    adaptation_before_full_coverage: bool = False
    trusted_shifted_count_lower_bound: int = 0
    current_family_capacity: int = 0
    precollapse_capacity_trigger_turn: int = -1
    capacity_trigger_direction: str = "" # "" | "UPWARD"
    contradiction_probe_trigger_turn: int = -1
    contradiction_probe_count: int = 0
    post_adaptation_probe_count: int = 0
    post_adaptation_probe_turn: int = -1
    contradiction_after_post_adaptation_probe: bool = False
    untouched_item_count_at_probe: int = -1
    contradiction_surface_turn: int = -1
    recovery_attempt_started: bool = False
    recovery_path_taken: str = ""
    recovery_blocker: str = ""
    family_proposal_opened_after_probe: bool = False
    family_proposal_trigger_count: int = 0
    candidate_family_specs_tested: List[str] = field(default_factory=list)
    adopted_family_spec: str = ""
    proposal_turn: int = -1
    proposal_search_outcome: str = ""
    fit_score_current_family: float = 0.0
    fit_score_candidate_family: float = 0.0
    family_search_exhausted: bool = False
    post_probe_family_proposal_count: int = 0
    post_probe_family_candidates_tested: List[str] = field(default_factory=list)
    post_probe_family_adopted: str = ""
    post_probe_family_fit_current: float = 0.0
    post_probe_family_fit_best_candidate: float = 0.0
    post_adaptation_queries: int = 0
    post_adaptation_commit_turn: int = -1
    post_adaptation_escalation_turn: int = -1
    post_adaptation_wrong_commit: bool = False
    post_adaptation_query_value: float = 0.0
    missed_anomalous_node: bool = False
    coverage_blindspot_triggered: bool = False
    final_outcome_category: str = "" # e.g. "BLIND_SPOT_FAILURE", "CORRECT_ADAPT_RECOVERY"
    
    # ── Extended workspace fields ────────────────────────────────────
    query_rationale: str = ""
    all_hypotheses: List[Tuple[dict, float]] = field(default_factory=list)
    items_queried: int = 0
    items_total: int = 0
    current_goal: str = ""
    next_action: str = ""           # filled by controller / adapter
    last_action_reason: str = ""    # filled by adapter after action
    episode_count: int = 0
    memory_summary: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_engine(cls, engine, **kwargs):
        from .inspector import BeliefInspector
        inspector = BeliefInspector(engine)
        current_capacity = 0
        if engine._current_generator and hasattr(engine._current_generator, "family_spec"):
            spec = engine._current_generator.family_spec()
            if spec is not None and hasattr(spec, "group_size"):
                current_capacity = spec.group_size

        trusted_shifted_lb = 0
        trusted = engine._trusted_source
        if trusted is not None:
            shifted_items = {
                item
                for item, value in engine._source_observations.get(trusted, [])
                if value != engine._initial_values.get(item)
            }
            trusted_shifted_lb = len(shifted_items)

        state = cls(
            entropy=engine.calculate_entropy() if hasattr(engine, 'calculate_entropy') else 0.0,
            confidence_margin=inspector.inspect(top_n=1)['confidence_margin'],
            top_hypotheses=engine.score_hypotheses()[:5],
            active_hypotheses_count=len([h for h in engine._hypotheses if h['prob'] > 1e-6]),
            trusted_source_locked=engine._trusted_source is not None,
            trust_evidence=dict(engine._trust_evidence),
            suspicion_scores=dict(engine._suspicion_scores),
            is_flagged=any(s > 2 for s in engine._suspicion_scores.values()),
            reset_count=engine.reset_count,
            suspicion_triggers=engine.suspicion_triggers,
            trusted_shifted_count_lower_bound=trusted_shifted_lb,
            current_family_capacity=current_capacity,
            query_rationale=inspector.inspect(top_n=1)['query_rationale'],
            all_hypotheses=engine.score_hypotheses(),
            items_queried=len(engine._queried_values),
            items_total=len(engine._items),
            **kwargs
        )
        return state

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
