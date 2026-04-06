"""
Unit tests for the Minimal Planner.

Verifies the deterministic decision table across all modes:
    EXPLORE, REFINE, EARLY_COMMIT, ESCALATE
"""

from deic_core.planner import MinimalPlanner, PlannerMode
from deic_core.workspace import CognitiveState
from deic_core.self_model import SelfModel


def _make_ws(**overrides):
    """Build a CognitiveState with sensible defaults, overridden as needed."""
    defaults = dict(
        entropy=1.0,
        confidence_margin=0.3,
        top_hypotheses=[({'shifted_items': frozenset(), 'multiplier': 1.0}, 0.5)],
        trust_distribution={'A': 0.5, 'B': 0.5},
        trusted_source_locked=False,
        query_rationale="Phase 1: Trust Discovery (seeking divergence)",
        all_hypotheses=[
            ({'shifted_items': frozenset(), 'multiplier': 1.0}, 0.5),
            ({'shifted_items': frozenset(), 'multiplier': 1.5}, 0.5),
        ],
        items_queried=0,
        items_total=8,
        current_goal="Establish trusted source",
    )
    defaults.update(overrides)
    return CognitiveState(**defaults)


def _make_sm(ws):
    """Build a SelfModel from a workspace."""
    return SelfModel.from_workspace(ws)


# ── R1: ESCALATE — budget gone + high entropy ─────────────────────

def test_r1_escalate_budget_zero_high_entropy():
    ws = _make_ws(entropy=2.5, confidence_margin=0.0, trusted_source_locked=False)
    sm = _make_sm(ws)
    planner = MinimalPlanner()
    d = planner.decide(ws, sm, remaining_budget=0)
    assert d.mode == PlannerMode.ESCALATE


# ── R2: EARLY_COMMIT — budget gone + low entropy ──────────────────

def test_r2_commit_budget_zero_low_entropy():
    ws = _make_ws(entropy=0.5, confidence_margin=0.6, trusted_source_locked=True)
    sm = _make_sm(ws)
    planner = MinimalPlanner()
    d = planner.decide(ws, sm, remaining_budget=0)
    assert d.mode == PlannerMode.EARLY_COMMIT


# ── R3: EARLY_COMMIT — high margin + low entropy ──────────────────

def test_r3_early_commit_high_confidence():
    ws = _make_ws(
        entropy=0.05,
        confidence_margin=0.97,
        trusted_source_locked=True,
        all_hypotheses=[({'shifted_items': frozenset(), 'multiplier': 1.0}, 0.97)],
    )
    sm = _make_sm(ws)
    planner = MinimalPlanner()
    d = planner.decide(ws, sm, remaining_budget=5)
    assert d.mode == PlannerMode.EARLY_COMMIT
    assert "saved" in d.recommendation.lower()


# ── R4: EARLY_COMMIT — single surviving hypothesis ────────────────

def test_r4_early_commit_single_hypothesis():
    """When only one hypothesis survives, R3 or R4 should trigger EARLY_COMMIT.
    With margin=1.0 and entropy=0.0, R3 fires first — that's correct behavior."""
    ws = _make_ws(
        entropy=0.0,
        confidence_margin=1.0,
        trusted_source_locked=True,
        all_hypotheses=[({'shifted_items': frozenset(), 'multiplier': 1.5}, 1.0)],
    )
    sm = _make_sm(ws)
    planner = MinimalPlanner()
    d = planner.decide(ws, sm, remaining_budget=4)
    assert d.mode == PlannerMode.EARLY_COMMIT
    assert "saved" in d.recommendation.lower() or "commit" in d.recommendation.lower()


# ── R5: EXPLORE — trust not locked ────────────────────────────────

def test_r5_explore_no_trust():
    ws = _make_ws(
        entropy=3.0,
        confidence_margin=0.0,
        trusted_source_locked=False,
    )
    sm = _make_sm(ws)
    planner = MinimalPlanner()
    d = planner.decide(ws, sm, remaining_budget=6)
    assert d.mode == PlannerMode.EXPLORE
    assert "trust" in d.rationale.lower()


# ── R6: REFINE — trust locked, ambiguity remains ──────────────────

def test_r6_refine_trust_locked_ambiguous():
    ws = _make_ws(
        entropy=1.5,
        confidence_margin=0.3,
        trusted_source_locked=True,
        query_rationale="Phase 2: Structural Elimination (resolving 12 hypotheses)",
    )
    sm = _make_sm(ws)
    planner = MinimalPlanner()
    d = planner.decide(ws, sm, remaining_budget=4)
    assert d.mode == PlannerMode.REFINE
    assert "infogain" in d.recommendation.lower()


# ── R7: Fallback — everything resolved ────────────────────────────

def test_r7_fallback_commit():
    ws = _make_ws(
        entropy=0.0,
        confidence_margin=0.0,
        trusted_source_locked=True,
        all_hypotheses=[],  # edge case: no hypotheses
    )
    sm = _make_sm(ws)
    planner = MinimalPlanner()
    d = planner.decide(ws, sm, remaining_budget=2)
    assert d.mode == PlannerMode.EARLY_COMMIT


# ── Custom thresholds ─────────────────────────────────────────────

def test_custom_threshold_tighter():
    """With a stricter confidence threshold, R3 shouldn't fire at margin=0.96."""
    ws = _make_ws(
        entropy=0.05,
        confidence_margin=0.96,
        trusted_source_locked=True,
        all_hypotheses=[
            ({'shifted_items': frozenset(), 'multiplier': 1.0}, 0.96),
            ({'shifted_items': frozenset(), 'multiplier': 1.5}, 0.04),
        ],
    )
    sm = _make_sm(ws)
    planner = MinimalPlanner(confidence_threshold=0.98)
    d = planner.decide(ws, sm, remaining_budget=3)
    # With threshold=0.98, margin 0.96 doesn't clear R3,
    # but there are 2 active hyps so R4 doesn't fire →  R6 REFINE
    assert d.mode == PlannerMode.REFINE


# ── Rationale is always non-empty ─────────────────────────────────

def test_rationale_always_present():
    planner = MinimalPlanner()
    for trust, budget, entropy, margin in [
        (False, 5, 2.0, 0.0),
        (True, 0, 0.5, 0.4),
        (True, 3, 0.05, 0.97),
        (True, 3, 1.5, 0.3),
    ]:
        ws = _make_ws(
            trusted_source_locked=trust,
            entropy=entropy,
            confidence_margin=margin,
        )
        sm = _make_sm(ws)
        d = planner.decide(ws, sm, remaining_budget=budget)
        assert len(d.rationale) > 0
        assert len(d.recommendation) > 0
