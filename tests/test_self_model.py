"""
SelfModel Tests

Validates:
  1. Correct generation of SelfModel from CognitiveState.
  2. Textual summaries match expected descriptors (confidence, etc.).
  3. Counterfactual trigger correctly identifies disagreement.
  4. Limitation detection activates on budget/entropy thresholds.
  5. Trust summary reflects engine reliability tracking.
"""

from deic_core import (
    DEIC, BeliefInspector, CognitiveState, SelfModel, FixedPartitionGenerator
)


def _make_engine():
    """Create a minimal DEIC engine for testing."""
    engine = DEIC()
    gen = FixedPartitionGenerator(group_size=2, multipliers=[1.5, 2.0])
    engine.initialize_beliefs({
        'items': ['i1', 'i2', 'i3'],
        'sources': ['s1', 's2'],
        'initial_values': {'i1': 10, 'i2': 20, 'i3': 30},
    }, hypothesis_generator=gen)
    return engine


def test_self_model_basic():
    """Verify basic summaries are generated."""
    engine = _make_engine()
    ws = BeliefInspector(engine).workspace()
    sm = SelfModel.from_workspace(ws)

    assert "group size 2" in sm.current_belief
    assert "Establish trusted source" in sm.goal_description
    assert sm.workspace_snapshot == ws
    assert str(sm).startswith("─── DEIC Self-Model Snapshot ───")


def test_confidence_descriptors():
    """Verify confidence mapping."""
    ws = CognitiveState(confidence_margin=0.95)
    assert "Very High" in SelfModel.from_workspace(ws).confidence_description

    ws.confidence_margin = 0.5
    assert "Moderate" in SelfModel.from_workspace(ws).confidence_description

    ws.confidence_margin = 0.05
    assert "Minimal" in SelfModel.from_workspace(ws).confidence_description


def test_counterfactual_trigger_item():
    """Verify trigger identifies a specific disagreement in items."""
    ws = CognitiveState(
        top_hypotheses=[
            ({'shifted_items': frozenset(['i1', 'i2']), 'multiplier': 2.0}, 0.6),
            ({'shifted_items': frozenset(['i2', 'i3']), 'multiplier': 2.0}, 0.3),
        ]
    )
    sm = SelfModel.from_workspace(ws)
    # H2 has i3, H1 does not. 
    assert "i3" in sm.counterfactual_trigger
    assert "secondary hypothesis" in sm.counterfactual_trigger


def test_counterfactual_trigger_multiplier():
    """Verify trigger identifies a specific disagreement in multiplier."""
    ws = CognitiveState(
        top_hypotheses=[
            ({'shifted_items': frozenset(['i1', 'i2']), 'multiplier': 2.0}, 0.6),
            ({'shifted_items': frozenset(['i1', 'i2']), 'multiplier': 1.5}, 0.3),
        ]
    )
    sm = SelfModel.from_workspace(ws)
    assert "1.50" in sm.counterfactual_trigger
    assert "shift my estimate" in sm.counterfactual_trigger


def test_limitation_warning():
    """Verify warnings for budget and entropy."""
    # Low items remaining
    ws = CognitiveState(items_total=10, items_queried=9)
    sm = SelfModel.from_workspace(ws)
    assert "monitoring capacity nearly exhausted" in sm.limitation_warning

    # High entropy
    ws.items_queried = 0
    ws.entropy = 3.0
    sm2 = SelfModel.from_workspace(ws)
    assert "too fragmented" in sm2.limitation_warning


def test_trust_summary():
    """Verify trust summary logic."""
    ws = CognitiveState(
        trusted_source_locked=True,
        trust_distribution={'s1': 0.9, 's2': 0.1}
    )
    sm = SelfModel.from_workspace(ws)
    assert "'s1'" in sm.trust_status
    assert "reliable observer" in sm.trust_status

    ws.trusted_source_locked = False
    ws.trust_distribution = {'s1': 0.2, 's2': 0.2}
    sm2 = SelfModel.from_workspace(ws)
    assert "cross-source conflict" in sm2.trust_status
