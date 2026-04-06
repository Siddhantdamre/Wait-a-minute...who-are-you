
import sys
import os
import random
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from deic_core import (
    DEIC, BeliefInspector, SelfModel, 
    FixedPartitionGenerator, VariablePartitionGenerator
)
from benchmark.environment import ProceduralEnvironment, EpisodeConfig
from experiments.cyber_transfer.environment import CyberIncidentEnvironment, CyberEpisodeConfig
from experiments.clinical_transfer.environment import ClinicalEnvironment, ClinicalEpisodeConfig

def run_sample(domain_name, runner):
    print(f"\n{'='*20} Domain: {domain_name} {'='*20}")
    try:
        sm = runner()
        print(sm)
    except Exception as e:
        print(f"Error in {domain_name}: {e}")

def sample_c6():
    config = EpisodeConfig(seed=12345, condition="c6_hidden_structure")
    env = ProceduralEnvironment(config)
    initial_state = env.get_initial_state()
    agents = env.get_agent_names()
    items = list(initial_state.keys())
    
    engine = DEIC()
    gen = FixedPartitionGenerator(group_size=4, multipliers=[1.2, 1.5, 2.0, 2.5])
    engine.initialize_beliefs({
        'items': items,
        'sources': agents,
        'initial_values': dict(initial_state),
    }, hypothesis_generator=gen)
    
    # Perform 4 queries
    for _ in range(4):
        source, item = engine.select_query({'remaining_turns': 10, 'queried_pairs': set()})
        obs = env.step({"type": "query", "target_agent": source, "item_id": item})
        val = obs.get("reported_quantity")
        if val is not None:
            engine.update_observation(source, item, val, t=0)
    
    ws = BeliefInspector(engine).workspace()
    return SelfModel.from_workspace(ws)

def sample_cyber():
    config = CyberEpisodeConfig(seed=54321)
    env = CyberIncidentEnvironment(config)
    initial_state = env.initial_inventory
    agents = env.agents
    items = env.items
    
    engine = DEIC()
    gen = FixedPartitionGenerator(group_size=4, multipliers=[1.5, 2.0, 3.0, 5.0])
    engine.initialize_beliefs({
        'items': items,
        'sources': agents,
        'initial_values': dict(initial_state),
    }, hypothesis_generator=gen)
    
    # Perform 3 queries
    for _ in range(3):
        source, item = engine.select_query({'remaining_turns': 10, 'queried_pairs': set()})
        obs = env.step({"type": "query", "target_agent": source, "item_id": item})
        val = obs.get("reported_quantity")
        if val is not None:
            engine.update_observation(source, item, val, t=0)
    
    ws = BeliefInspector(engine).workspace()
    return SelfModel.from_workspace(ws)

def sample_clinical():
    config = ClinicalEpisodeConfig(seed=99999)
    env = ClinicalEnvironment(config)
    
    patients = env.get_patients()
    stations = env.get_stations()
    baselines = env.get_baseline_vitals()
    
    engine = DEIC()
    gen = VariablePartitionGenerator(group_sizes=[2, 3, 4, 5, 6], multipliers=[1.3, 1.8, 2.5])
    engine.initialize_beliefs({
        'items': patients,
        'sources': stations,
        'initial_values': baselines,
    }, hypothesis_generator=gen)
    
    # Perform 3 queries (increased from 2 to get more evidence)
    for _ in range(3):
        source, item = engine.select_query({'remaining_turns': 10, 'queried_pairs': set()})
        obs = env.query(source, item)
        val = obs.get("reported_vitals")
        if val is not None:
            engine.update_observation(source, item, val, t=0)
    
    ws = BeliefInspector(engine).workspace()
    return SelfModel.from_workspace(ws)

if __name__ == "__main__":
    run_sample("C6 Benchmark", sample_c6)
    run_sample("Cyber Incident", sample_cyber)
    run_sample("Clinical Monitoring", sample_clinical)
