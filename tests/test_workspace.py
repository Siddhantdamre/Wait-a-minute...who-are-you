"""
Global Workspace Tests

Validates that:
  1. CognitiveState snapshot is consistent with inspector output.
  2. CommitController.decide() accepts CognitiveState via duck typing.
  3. Memory summary appears in workspace when memory is provided.
  4. Goal derivation reflects the cognitive phase.
  5. Workspace does not break existing inspector behavior.
"""

from deic_core import (
    DEIC, BeliefInspector, CommitController, CrossEpisodeMemory,
    CognitiveState, FixedPartitionGenerator,
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


# ── 1. Snapshot consistency ──────────────────────────────────────────

def test_workspace_matches_inspector():
    """Workspace snapshot must contain the same belief data as inspect()."""
    engine = _make_engine()
    inspector = BeliefInspector(engine)

    dict_result = inspector.inspect(top_n=3)
    ws = inspector.workspace(top_n=3)

    assert abs(ws.entropy - dict_result['entropy']) < 1e-9
    assert abs(ws.confidence_margin - dict_result['confidence_margin']) < 1e-9
    assert ws.trusted_source_locked == dict_result['trusted_source_locked']
    assert ws.query_rationale == dict_result['query_rationale']
    assert len(ws.top_hypotheses) == len(dict_result['top_hypotheses'])


# ── 2. Controller backward compatibility ─────────────────────────────

def test_controller_accepts_workspace():
    """CommitController.decide() must work with CognitiveState via [] access."""
    engine = _make_engine()
    inspector = BeliefInspector(engine)
    controller = CommitController()

    ws = inspector.workspace()

    # Must not raise — controller reads ws['confidence_margin'], ws['entropy'], etc.
    decision = controller.decide(ws, remaining_budget=5, has_valid_queries=True)
    assert decision in (
        CommitController.ACTION_QUERY,
        CommitController.ACTION_COMMIT,
        CommitController.ACTION_ESCALATE,
        CommitController.ACTION_STOP,
    )


def test_controller_accepts_dict():
    """Existing dict path must still work (regression guard)."""
    engine = _make_engine()
    inspector = BeliefInspector(engine)
    controller = CommitController()

    dict_result = inspector.inspect()
    decision = controller.decide(dict_result, remaining_budget=5, has_valid_queries=True)
    assert decision in (
        CommitController.ACTION_QUERY,
        CommitController.ACTION_COMMIT,
        CommitController.ACTION_ESCALATE,
        CommitController.ACTION_STOP,
    )


# ── 3. Memory integration ───────────────────────────────────────────

def test_workspace_with_memory():
    """Memory summary must appear in workspace when memory is provided."""
    engine = _make_engine()
    inspector = BeliefInspector(engine)
    memory = CrossEpisodeMemory()

    # Feed some history
    memory.observe_episode_outcome(None, True, {'S': ['i1', 'i2'], 'm': 1.5})
    memory.observe_episode_outcome(None, True, {'S': ['i2', 'i3'], 'm': 2.0})

    ws = inspector.workspace(memory=memory)

    assert ws.episode_count == 2
    assert ws.memory_summary['total_episodes'] == 2
    assert 2 in ws.memory_summary['group_size_counts']
    assert 1.5 in ws.memory_summary['multiplier_counts']
    assert 2.0 in ws.memory_summary['multiplier_counts']


def test_workspace_without_memory():
    """Workspace must work cleanly with memory=None."""
    engine = _make_engine()
    inspector = BeliefInspector(engine)

    ws = inspector.workspace(memory=None)
    assert ws.episode_count == 0
    assert ws.memory_summary == {}


# ── 4. Goal derivation ──────────────────────────────────────────────

def test_goal_trust_phase():
    """Before trust is locked, goal should be 'Establish trusted source'."""
    engine = _make_engine()
    inspector = BeliefInspector(engine)

    ws = inspector.workspace()
    assert ws.current_goal == "Establish trusted source"


def test_goal_after_trust():
    """After trust is locked and hypotheses remain, goal reflects uncertainty."""
    engine = _make_engine()
    # Force trust lock by observing a shifted value
    engine.update_observation('s1', 'i1', 15, t=0)  # 15 != 10 → trust locked
    inspector = BeliefInspector(engine)

    ws = inspector.workspace()
    assert ws.trusted_source_locked is True
    assert ws.current_goal in (
        "Reduce hypothesis uncertainty",
        "Increase confidence margin",
        "Ready to commit",
    )


# ── 5. Extended fields ──────────────────────────────────────────────

def test_workspace_item_counts():
    """Workspace must track queried vs total items."""
    engine = _make_engine()
    inspector = BeliefInspector(engine)

    ws = inspector.workspace()
    assert ws.items_total == 3
    assert ws.items_queried == 0
    assert ws.trust_lock_turn == -1
    assert ws.current_family_capacity == 2
    assert ws.trusted_shifted_count_lower_bound == 0

    # Query one item
    engine.update_observation('s1', 'i1', 15, t=0)
    ws2 = inspector.workspace()
    assert ws2.items_queried == 1
    assert ws2.trusted_shifted_count_lower_bound == 1

    # Query a second shifted item from the trusted source.
    engine.update_observation('s1', 'i2', 30, t=1)
    ws3 = inspector.workspace()
    assert ws3.trusted_shifted_count_lower_bound == 2


def test_workspace_to_dict():
    """to_dict() must produce the same keys as inspect()."""
    engine = _make_engine()
    inspector = BeliefInspector(engine)

    ws = inspector.workspace()
    d = ws.to_dict()

    expected_keys = {'entropy', 'confidence_margin', 'top_hypotheses',
                     'trust_distribution', 'trusted_source_locked',
                     'query_rationale'}
    assert set(d.keys()) == expected_keys


def test_workspace_dict_access():
    """CognitiveState must support ws['field'] access."""
    ws = CognitiveState(entropy=1.5, confidence_margin=0.8)
    assert ws['entropy'] == 1.5
    assert ws['confidence_margin'] == 0.8
    assert ws.get('nonexistent', 42) == 42


def test_workspace_dsl_v1_telemetry_defaults():
    """DSL v1 telemetry fields should exist with stable defaults."""
    ws = CognitiveState()
    assert ws.family_proposal_trigger_count == 0
    assert ws.candidate_family_specs_tested == []
    assert ws.adopted_family_spec == ""
    assert ws.proposal_turn == -1
    assert ws.proposal_search_outcome == ""
    assert ws.fit_score_current_family == 0.0
    assert ws.fit_score_candidate_family == 0.0
    assert ws.family_search_exhausted is False


def test_workspace_conscience_advisory_defaults():
    """Advisory conscience fields should exist with stable defaults."""
    ws = CognitiveState()
    assert ws.conscience_advisory_enabled is False
    assert ws.conscience_advisory_uncertainty_context == 0.0
    assert ws.conscience_advisory_trust_context == 0.5
    assert ws.conscience_advisory_care_relevance == 0.0
    assert ws.conscience_advisory_moral_weight == 0.0
    assert ws.conscience_advisory_threat_context == 0.0
    assert ws.conscience_advisory_candidate_action == ""
    assert ws.conscience_advisory_harm_risk == "none"
    assert ws.conscience_advisory_honesty_conflict is False
    assert ws.conscience_advisory_responsibility_conflict is False
    assert ws.conscience_advisory_repair_needed is False
    assert ws.conscience_advisory_label == ""
    assert ws.conscience_advisory_value_conflict_present is False
    assert ws.conscience_advisory_trace_complete is False
