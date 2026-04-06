"""
Thin benchmark adapter: bridges the Kaggle ProceduralEnvironment
to the domain-agnostic DEIC engine.

This file does NOT contain inference logic. It translates
environment JSON payloads into DEIC API calls and DEIC outputs
back into environment actions.
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from deic_core import DEIC, BeliefInspector, CommitController


def _trajectory_entry(action, fault_prior):
    return {"next_action": action, "confidence_scores": dict(fault_prior)}


class DEICBenchmarkAdapter:
    """
    Drop-in replacement for DiscreteStructureAgentV2 that delegates
    all inference to the standalone DEIC module.
    """

    def __init__(self, adaptive_trust=True, use_controller=False, memory=None):
        self.adaptive_trust = adaptive_trust
        self.use_controller = use_controller
        self.memory = memory

    def solve(self, env):
        initial_state = env.get_initial_state()
        agents = env.get_agent_names()
        items = list(initial_state.keys())
        budget = env.config.max_turns

        # 1. Initialize DEIC
        engine = DEIC(adaptive_trust=self.adaptive_trust)
        engine.initialize_beliefs({
            'items': items,
            'sources': agents,
            'group_size': 4,
            'valid_multipliers': [1.2, 1.5, 2.0, 2.5],
            'initial_values': dict(initial_state),
        }, memory=self.memory)

        if self.use_controller:
            return self._solve_with_controller(env, engine, budget, agents)
        else:
            return self._solve_legacy(env, engine, budget, agents)

    def _solve_legacy(self, env, engine, budget, agents):
        trajectory = []
        fault_prior = {a: 0.1 for a in agents}
        queried_pairs = set()

        # 2. Phase A: Trust discovery
        while env.turn < budget - 1 and engine._trusted_source is None:
            source, item = engine.select_query({
                'remaining_turns': budget - 1 - env.turn,
                'queried_pairs': queried_pairs,
            })

            action = {"type": "query", "target_agent": source, "item_id": item}
            trajectory.append(_trajectory_entry(action, fault_prior))
            obs = env.step(action)
            queried_pairs.add((source, item))

            if obs.get("status") == "budget_exhausted":
                break
            if "reported_quantity" in obs:
                engine.update_observation(source, item, obs["reported_quantity"], env.turn)
                if engine._trusted_source is None and not self.adaptive_trust:
                    engine.update_trust()

        # 3. Phase B: Structural queries via trusted source
        while env.turn < budget - 1 and engine._trusted_source is not None:
            active = engine.score_hypotheses()
            if len(active) <= 1:
                break

            source, item = engine.select_query({
                'remaining_turns': budget - 1 - env.turn,
                'queried_pairs': queried_pairs,
            })

            action = {"type": "query", "target_agent": source, "item_id": item}
            trajectory.append(_trajectory_entry(action, fault_prior))
            obs = env.step(action)
            queried_pairs.add((source, item))

            if obs.get("status") == "budget_exhausted":
                break
            if "reported_quantity" in obs:
                engine.update_observation(source, item, obs["reported_quantity"], env.turn)

        # 4. Commit
        proposed = engine.propose_state()
        commit_action = {"type": "commit_consensus", "proposed_inventory": proposed}
        trajectory.append(_trajectory_entry(commit_action, fault_prior))
        result = env.step(commit_action)
        return trajectory, result

    def _solve_with_controller(self, env, engine, budget, agents):
        trajectory = []
        fault_prior = {a: 0.1 for a in agents}
        queried_pairs = set()
        inspector = BeliefInspector(engine)
        controller = CommitController()

        while True:
            remaining = budget - 1 - env.turn
            inspector_state = inspector.inspect(top_n=1)
            
            unqueried_items = [it for it in engine._items if it not in engine._queried_values]
            has_valid_queries = len(unqueried_items) > 0

            decision = controller.decide(inspector_state, max(0, remaining), has_valid_queries=has_valid_queries)

            if decision in (CommitController.ACTION_COMMIT, CommitController.ACTION_STOP, CommitController.ACTION_ESCALATE):
                proposed = engine.propose_state()
                commit_action = {"type": "commit_consensus", "proposed_inventory": proposed}
                if decision == CommitController.ACTION_ESCALATE:
                    commit_action["escalated"] = True
                trajectory.append(_trajectory_entry(commit_action, fault_prior))
                result = env.step(commit_action)
                return trajectory, result
            
            elif decision == CommitController.ACTION_QUERY:
                source, item = engine.select_query({
                    'remaining_turns': remaining,
                    'queried_pairs': queried_pairs,
                })
                action = {"type": "query", "target_agent": source, "item_id": item}
                trajectory.append(_trajectory_entry(action, fault_prior))
                obs = env.step(action)
                queried_pairs.add((source, item))

                if obs.get("status") == "budget_exhausted":
                    pass
                elif "reported_quantity" in obs:
                    engine.update_observation(source, item, obs["reported_quantity"], env.turn)
                    if engine._trusted_source is None and not self.adaptive_trust:
                        engine.update_trust()
