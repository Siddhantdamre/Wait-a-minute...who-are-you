
import sys
import os
import math
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from deic_core import DEIC, BeliefInspector, FixedPartitionGenerator

def _make_engine():
    engine = DEIC()
    gen = FixedPartitionGenerator(group_size=2, multipliers=[1.5, 2.0])
    engine.initialize_beliefs({
        'items': ['i1', 'i2', 'i3'],
        'sources': ['s1', 's2'],
        'initial_values': {'i1': 10, 'i2': 20, 'i3': 30},
    }, hypothesis_generator=gen)
    return engine

def debug_test():
    engine = _make_engine()
    print(f"DEBUG: Initial trusted source: {engine._trusted_source}")
    
    # Force trust lock by observing a shifted value
    engine.update_observation('s1', 'i1', 15, t=0)
    print(f"DEBUG: After update, trusted source: {engine._trusted_source}")
    
    inspector = BeliefInspector(engine)
    inspector_data = inspector.inspect()
    print(f"DEBUG: Inspector data: {inspector_data}")
    
    ws = inspector.workspace()
    print(f"DEBUG: Workspace goal: '{ws.current_goal}'")
    print(f"DEBUG: Workspace confidence_margin: {ws.confidence_margin}")
    print(f"DEBUG: Workspace entropy: {ws.entropy}")
    print(f"DEBUG: Workspace top_hypotheses: {len(ws.top_hypotheses)}")
    print(f"DEBUG: Workspace trusted_source_locked: {ws.trusted_source_locked}")

    allowed = (
        "Reduce hypothesis uncertainty",
        "Increase confidence margin",
        "Ready to commit",
    )
    if ws.current_goal in allowed:
        print("DEBUG: ASYNC PASS")
    else:
        print(f"DEBUG: ASYNC FAIL! '{ws.current_goal}' not in {allowed}")

if __name__ == "__main__":
    debug_test()
