import pytest
import math
from deic_core import DEIC, BeliefInspector, FixedPartitionGenerator

def test_inspector_initial_state():
    engine = DEIC(adaptive_trust=True)
    gen = FixedPartitionGenerator(group_size=2, multipliers=[1.5])
    env_spec = {
        'items': ['i1', 'i2', 'i3'],
        'sources': ['s1', 's2'],
        'initial_values': {'i1': 10, 'i2': 10, 'i3': 10}
    }
    engine.initialize_beliefs(env_spec, hypothesis_generator=gen)
    
    inspector = BeliefInspector(engine)
    state = inspector.inspect(top_n=2)
    
    assert state['trusted_source_locked'] is False
    assert state['query_rationale'] == "Phase 1: Trust Discovery (seeking divergence)"
    
    # 3 items, choose 2 -> 3 combinations. 1 multiplier. -> 3 hypotheses equally likely.
    # entropy = -(3 * (1/3) * log2(1/3)) = log2(3) = 1.5849625
    expected_entropy = math.log2(3)
    assert math.isclose(state['entropy'], expected_entropy, rel_tol=1e-5)
    
    assert state['confidence_margin'] == 0.0
    assert len(state['top_hypotheses']) == 2
    assert state['trust_distribution'] == {'s1': 0.5, 's2': 0.5}


def test_inspector_trust_locked():
    engine = DEIC(adaptive_trust=True)
    gen = FixedPartitionGenerator(group_size=2, multipliers=[1.5])
    env_spec = {
        'items': ['i1', 'i2', 'i3'],
        'sources': ['s1', 's2'],
        'initial_values': {'i1': 10, 'i2': 10, 'i3': 10}
    }
    engine.initialize_beliefs(env_spec, hypothesis_generator=gen)
    
    # Observe item 1 from s1 with shifted value
    engine.update_observation('s1', 'i1', 15, t=1)
    
    inspector = BeliefInspector(engine)
    state = inspector.inspect(top_n=3)
    
    assert state['trusted_source_locked'] is True
    assert "Phase 2: Structural Elimination" in state['query_rationale']
    
    assert state['trust_distribution']['s1'] == 1.0
    assert state['trust_distribution']['s2'] == 0.2
    
    # Hypotheses involving i1: ('i1', 'i2') and ('i1', 'i3'). Posterior drops ('i2', 'i3').
    # So 2 hypotheses left, each 0.5 prob.
    expected_entropy = 1.0 # 2 equally likely
    assert math.isclose(state['entropy'], expected_entropy, rel_tol=1e-5)
    assert state['confidence_margin'] == 0.0


def test_inspector_posterior_collapsed():
    engine = DEIC(adaptive_trust=True)
    gen = FixedPartitionGenerator(group_size=2, multipliers=[1.5])
    env_spec = {
        'items': ['i1', 'i2', 'i3'],
        'sources': ['s1', 's2'],
        'initial_values': {'i1': 10, 'i2': 10, 'i3': 10}
    }
    engine.initialize_beliefs(env_spec, hypothesis_generator=gen)
    
    engine.update_observation('s1', 'i1', 15, t=1)
    engine.update_observation('s1', 'i2', 15, t=2)
    
    inspector = BeliefInspector(engine)
    state = inspector.inspect()
    
    assert state['trusted_source_locked'] is True
    assert "Completed: Posterior collapsed" in state['query_rationale']
    
    assert math.isclose(state['entropy'], 0.0, rel_tol=1e-5)
    assert math.isclose(state['confidence_margin'], 1.0, rel_tol=1e-5)

def test_inspector_non_adaptive_rationale():
    engine = DEIC(adaptive_trust=False)
    gen = FixedPartitionGenerator(group_size=2, multipliers=[1.5])
    env_spec = {
        'items': ['i1', 'i2', 'i3'],
        'sources': ['s1', 's2'],
        'initial_values': {'i1': 10, 'i2': 10, 'i3': 10}
    }
    engine.initialize_beliefs(env_spec, hypothesis_generator=gen)
    
    inspector = BeliefInspector(engine)
    state = inspector.inspect()
    assert state['query_rationale'] == "Phase 1: Trust Discovery (seeking majority consensus)"
