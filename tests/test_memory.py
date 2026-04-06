import math
from deic_core import DEIC, CrossEpisodeMemory, FixedPartitionGenerator

def test_memory_no_action_by_default():
    engine = DEIC()
    gen = FixedPartitionGenerator(group_size=2, multipliers=[1.5])
    env_spec = {
        'items': ['i1', 'i2', 'i3'],
        'sources': ['s1', 's2'],
        'initial_values': {'i1': 10, 'i2': 10, 'i3': 10}
    }
    
    # Passing memory=None should work seamlessly
    engine.initialize_beliefs(env_spec, hypothesis_generator=gen, memory=None)
    assert len(engine._hypotheses) == 3
    for h in engine._hypotheses:
        assert h['prob'] == 1.0 / 3.0

def test_memory_affects_priors():
    memory = CrossEpisodeMemory()
    
    # Observe 10 episodes, 9 of them are group size 2 and m=1.5
    for _ in range(9):
        memory.observe_episode_outcome(None, True, {'S': ['i1', 'i2'], 'm': 1.5})
    
    # 1 episode is group size 3 and m=2.0
    memory.observe_episode_outcome(None, True, {'S': ['i1', 'i2', 'i3'], 'm': 2.0})

    engine = DEIC()
    gen = FixedPartitionGenerator(group_size=2, multipliers=[1.5, 2.0])
    env_spec = {
        'items': ['i1', 'i2', 'i3'],
        'sources': ['s1', 's2'],
        'initial_values': {'i1': 10, 'i2': 10, 'i3': 10}
    }
    
    engine.initialize_beliefs(env_spec, hypothesis_generator=gen, memory=memory)
    
    probs = [h['prob'] for h in engine._hypotheses]
    # The hypotheses with m=1.5 should be heavily favored over m=2.0
    h_m1_5 = [h['prob'] for h in engine._hypotheses if h['m'] == 1.5]
    h_m2_0 = [h['prob'] for h in engine._hypotheses if h['m'] == 2.0]
    
    assert h_m1_5[0] > h_m2_0[0], "Prior bias did not favor the frequently observed multiplier"
