"""
Planner Trace: End-to-end sample showing the full cognitive stack.

    CognitiveState → SelfModel → Planner mode → Controller action

Runs one C6 episode step-by-step, printing the planner decision at
each query turn so the full reasoning chain is visible.
"""

import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from deic_core import (
    DEIC, BeliefInspector, CommitController, SelfModel,
    MinimalPlanner, FixedPartitionGenerator,
)
from benchmark.environment import ProceduralEnvironment, EpisodeConfig
from benchmark.deic_adapter import DEICBenchmarkAdapter


def run_traced_episode(seed=12345, budget=8):
    """Run one C6 episode with full planner tracing."""

    config = EpisodeConfig(seed=seed, condition="c6_hidden_structure")
    env = ProceduralEnvironment(config)
    initial_state = env.get_initial_state()
    agents = env.get_agent_names()
    items = list(initial_state.keys())

    # Stack components
    adapter = DEICBenchmarkAdapter(use_planner=True)
    
    print(f"{'='*70}")
    print(f"PLANNER TRACE — C6 Episode (seed={seed}, budget={budget})")
    print(f"Executing with Minimal Planner Integration (Phase 8)")
    print(f"{'='*70}")

    trajectory, result = adapter.solve(env)

    for i, entry in enumerate(trajectory):
        mode = entry.get("planner_mode", "UNKNOWN")
        act = entry.get("next_action", {})
        
        print(f"\n-- Turn {i+1} --")
        print(f"  Planner:   {mode}")
        if act.get("type") == "query":
            print(f"  Action:    QUERY ({act.get('target_agent')}, {act.get('item_id')})")
        elif act.get("type") == "commit_consensus":
            if act.get("escalated"):
                print(f"  Action:    ESCALATE")
            else:
                print(f"  Action:    COMMIT")

    diff = result.get("true_state_diff", {})
    incorrect = len(diff)
    total = len(items)
    correct = total - incorrect
    accuracy = correct / total

    print(f"\n{'='*70}")
    print(f"RESULT: {correct}/{total} correct ({accuracy:.1%} accuracy)")
    print(f"Queries used: {len(trajectory)-1}/{budget}")
    print("*(Note: Final commit resolves ties stochastically if ambiguity remains)*")
    print(f"{'='*70}")

    return accuracy, len(trajectory)-1


if __name__ == "__main__":
    run_traced_episode()
