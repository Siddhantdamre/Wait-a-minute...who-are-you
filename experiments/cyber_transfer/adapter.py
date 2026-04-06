"""
Cyber Incident Adapter for DEIC

Bridges the CyberIncidentEnvironment to the domain-agnostic
DEIC engine. Uses CyberHypothesisGenerator for domain-specific
hypothesis setup.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from deic_core import DEIC, cyber_generator, BeliefInspector, CommitController


class CyberDEICAdapter:
    """
    Uses DEIC to diagnose a cyber incident by mapping:
      service  -> item
      monitor  -> source
      latency  -> value
      baseline -> initial_values
    """

    def __init__(self, adaptive_trust=True, use_controller=False, memory=None):
        self.adaptive_trust = adaptive_trust
        self.use_controller = use_controller
        self.memory = memory

    def diagnose(self, env):
        baseline = env.get_baseline_latency()
        services = env.get_services()
        monitors = env.get_monitors()
        budget = env.config.max_queries

        engine = DEIC(adaptive_trust=self.adaptive_trust)
        engine.initialize_beliefs(
            {'items': services, 'sources': monitors, 'initial_values': baseline},
            hypothesis_generator=cyber_generator(),
            memory=self.memory
        )

        if self.use_controller:
            return self._diagnose_with_controller(env, engine, budget)
        else:
            return self._diagnose_legacy(env, engine, budget)

    def _diagnose_legacy(self, env, engine, budget):
        queried_pairs = set()

        # Phase A: Trust discovery (find the live monitor)
        while env.turn < budget - 1 and engine._trusted_source is None:
            monitor, service = engine.select_query({
                'remaining_turns': budget - 1 - env.turn,
                'queried_pairs': queried_pairs,
            })

            result = env.query(monitor, service)
            queried_pairs.add((monitor, service))

            if result.get("status") == "timeout":
                break
            if "reported_latency" in result:
                engine.update_observation(
                    monitor, service, result["reported_latency"], env.turn
                )
                if engine._trusted_source is None and not self.adaptive_trust:
                    engine.update_trust()

        # Phase B: Structural queries via trusted monitor
        while env.turn < budget - 1 and engine._trusted_source is not None:
            active = engine.score_hypotheses()
            if len(active) <= 1:
                break

            monitor, service = engine.select_query({
                'remaining_turns': budget - 1 - env.turn,
                'queried_pairs': queried_pairs,
            })

            result = env.query(monitor, service)
            queried_pairs.add((monitor, service))

            if result.get("status") == "timeout":
                break
            if "reported_latency" in result:
                engine.update_observation(
                    monitor, service, result["reported_latency"], env.turn
                )

        # Submit diagnosis
        proposed = engine.propose_state()
        diagnosis_result = env.submit_diagnosis(proposed)
        return diagnosis_result

    def _diagnose_with_controller(self, env, engine, budget):
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
                return env.submit_diagnosis(proposed)
            
            elif decision == CommitController.ACTION_QUERY:
                monitor, service = engine.select_query({
                    'remaining_turns': remaining,
                    'queried_pairs': queried_pairs,
                })
                result = env.query(monitor, service)
                queried_pairs.add((monitor, service))

                if result.get("status") == "timeout":
                    pass
                elif "reported_latency" in result:
                    engine.update_observation(
                        monitor, service, result["reported_latency"], env.turn
                    )
                    if engine._trusted_source is None and not self.adaptive_trust:
                        engine.update_trust()
