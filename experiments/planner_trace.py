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


def run_traced_episode(seed=12345, budget=8):
    """Run one C6 episode with full planner tracing."""

    config = EpisodeConfig(seed=seed, condition="c6_hidden_structure")
    env = ProceduralEnvironment(config)
    initial_state = env.get_initial_state()
    agents = env.get_agent_names()
    items = list(initial_state.keys())

    # Stack components
    engine = DEIC()
    gen = FixedPartitionGenerator(group_size=4, multipliers=[1.2, 1.5, 2.0, 2.5])
    engine.initialize_beliefs({
        'items': items,
        'sources': agents,
        'initial_values': dict(initial_state),
    }, hypothesis_generator=gen)

    inspector = BeliefInspector(engine)
    controller = CommitController()
    planner = MinimalPlanner()

    queried_pairs = set()
    queries_used = 0

    print(f"{'='*70}")
    print(f"PLANNER TRACE — C6 Episode (seed={seed}, budget={budget})")
    print(f"{'='*70}")

    for turn in range(budget):
        remaining = budget - turn

        # 1. Build workspace
        ws = inspector.workspace()

        # 2. Build self-model
        sm = SelfModel.from_workspace(ws)

        # 3. Planner decides mode
        pd = planner.decide(ws, sm, remaining_budget=remaining)

        # 4. Controller decides action
        ctrl_action = controller.decide(ws, remaining_budget=remaining,
                                         has_valid_queries=True)

        # Print trace
        print(f"\n-- Turn {turn+1}/{budget} --")
        print(f"  Entropy:     {ws.entropy:.3f}")
        print(f"  Margin:      {ws.confidence_margin:.3f}")
        print(f"  Trust:       {'LOCKED' if ws.trusted_source_locked else 'OPEN'}")
        print(f"  Active Hyps: {len([h for h, p in ws.all_hypotheses if p > 0])}")
        print(f"  SelfModel:   {sm.confidence_description}")
        print(f"  Planner:     {pd.mode.value}")
        print(f"  Rationale:   {pd.rationale}")
        print(f"  Recommend:   {pd.recommendation}")
        print(f"  Controller:  {ctrl_action}")

        # If planner says EARLY_COMMIT or ESCALATE, stop querying
        if pd.mode.value in ("EARLY_COMMIT", "ESCALATE"):
            print(f"\n  >>> Planner triggered {pd.mode.value}. Stopping queries.")
            queries_used = turn
            break

        # Execute query
        source, item = engine.select_query({
            'remaining_turns': remaining,
            'queried_pairs': queried_pairs,
        })
        action = {"type": "query", "target_agent": source, "item_id": item}
        obs = env.step(action)
        queried_pairs.add((source, item))

        if "reported_quantity" in obs:
            engine.update_observation(source, item, obs["reported_quantity"], t=turn)

        print(f"  Query:       ({source}, {item}) → {obs.get('reported_quantity', '?')}")
        queries_used = turn + 1
    else:
        # Budget fully consumed
        pass

    # Final commit
    proposed = engine.propose_state()
    commit_action = {"type": "commit_consensus", "proposed_inventory": proposed}
    result = env.step(commit_action)

    diff = result.get("true_state_diff", {})
    incorrect = len(diff)
    total = len(items)
    correct = total - incorrect
    accuracy = correct / total

    print(f"\n{'='*70}")
    print(f"RESULT: {correct}/{total} correct ({accuracy:.1%} accuracy)")
    print(f"Queries used: {queries_used}/{budget}")
    print("*(Note: Final commit resolves ties stochastically if ambiguity remains)*")
    print(f"{'='*70}")

    return accuracy, queries_used


if __name__ == "__main__":
    run_traced_episode()
