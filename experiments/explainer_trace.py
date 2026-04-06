"""
Explainer Trace: End-to-end sample showing the full cognitive stack and explanation layer.

    CognitiveState → SelfModel → Planner mode → Controller action → Explanation

Outputs the diagnostic explanation style at each step to demonstrate falsifiability rules
and safe natural language generation.
"""

import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from deic_core import (
    DEIC, BeliefInspector, CommitController, SelfModel,
    MinimalPlanner, FixedPartitionGenerator, StateExplainer
)
from benchmark.environment import ProceduralEnvironment, EpisodeConfig

def run_explainer_trace(seed=12345, budget=8):
    config = EpisodeConfig(seed=seed, condition="c6_hidden_structure")
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

    inspector = BeliefInspector(engine)
    planner = MinimalPlanner()
    explainer = StateExplainer()
    
    item_queries = {it: set() for it in engine._items}
    queried_pairs = set()

    print(f"{'='*70}")
    print(f"EXPLAINER TRACE — C6 Episode (seed={seed}, budget={budget})")
    print(f"{'='*70}")

    for turn in range(budget):
        remaining = budget - turn

        ws = inspector.workspace()
        sm = SelfModel.from_workspace(ws)
        pd = planner.decide(ws, sm, remaining_budget=remaining)
        mode = pd.mode.value

        # Build simulated action based on adapter logic for full pipeline representation
        if mode in ("EARLY_COMMIT", "ESCALATE"):
            proposed = engine.propose_state()
            action = {"type": "commit_consensus", "proposed_inventory": proposed}
            if mode == "ESCALATE":
                action["escalated"] = True
        else:
            if mode == "EXPLORE":
                target_item = None
                for it, ags in item_queries.items():
                    if 0 < len(ags) < len(agents):
                        target_item = it
                        break
                if not target_item:
                    for it, ags in item_queries.items():
                        if len(ags) < len(agents):
                            target_item = it
                            break
                if not target_item:
                    target_item = engine._items[0]
                    
                avail = [a for a in agents if a not in item_queries[target_item]]
                monitor = avail[0] if avail else agents[0]
                action = {"type": "query", "target_agent": monitor, "item_id": target_item}
            else:
                monitor, service = engine.select_query({
                    'remaining_turns': remaining,
                    'queried_pairs': queried_pairs,
                })
                action = {"type": "query", "target_agent": monitor, "item_id": service}

        # Generate Explanation
        diagnostic_text = explainer.generate_explanation(ws, sm, pd, action, style="diagnostic")
        
        print(f"\n[Turn {turn+1}] ----------------------------------------------------")
        print(diagnostic_text)

        if mode in ("EARLY_COMMIT", "ESCALATE"):
            result = env.step(action)
            break
            
        # Execute query
        obs = env.step(action)
        monitor, service = action["target_agent"], action["item_id"]
        queried_pairs.add((monitor, service))
        item_queries[service].add(monitor)

        if "reported_quantity" in obs:
            engine.update_observation(monitor, service, obs["reported_quantity"], t=turn)
            if engine._trusted_source is None:
                engine.update_trust()
    else:
        # Budget exhausted cleanly
        proposed = engine.propose_state()
        result = env.step({"type": "commit_consensus", "proposed_inventory": proposed})

    diff = result.get("true_state_diff", {})
    incorrect = len(diff)
    total = len(items)
    correct = total - incorrect
    
    print(f"\n{'='*70}")
    print(f"RESULT: {correct}/{total} correct ({correct/total:.1%} accuracy)")
    print(f"{'='*70}")

if __name__ == "__main__":
    run_explainer_trace(seed=42, budget=12)
