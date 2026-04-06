"""
Cyber Incident Adapter for DEIC

Bridges the CyberIncidentEnvironment to the domain-agnostic
DEIC engine. DEIC core.py is used without any modifications.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from deic_core import DEIC


class CyberDEICAdapter:
    """
    Uses DEIC to diagnose a cyber incident by mapping:
      service  -> item
      monitor  -> source
      latency  -> value
      baseline -> initial_values
    """

    def __init__(self, adaptive_trust=True):
        self.adaptive_trust = adaptive_trust

    def diagnose(self, env):
        baseline = env.get_baseline_latency()
        services = env.get_services()
        monitors = env.get_monitors()
        budget = env.config.max_queries

        # Initialize DEIC with cyber domain parameters
        engine = DEIC(adaptive_trust=self.adaptive_trust)
        engine.initialize_beliefs({
            'items': services,
            'sources': monitors,
            'group_size': 4,
            'valid_multipliers': [1.5, 2.0, 3.0, 5.0],
            'initial_values': baseline,
        })

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
