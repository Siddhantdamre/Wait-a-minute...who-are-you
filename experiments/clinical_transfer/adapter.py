"""
Clinical Adapter for DEIC (Zero Modification)

Bridges ClinicalEnvironment to the domain-agnostic DEIC engine.
DEIC core.py is used WITHOUT any changes.

IMPORTANT: DEIC assumes group_size=4 (fixed partition).
The clinical domain has variable deteriorating group sizes (2-6).
This adapter passes group_size=4 because DEIC's API requires it.
The purpose of this test is to see what happens when that
assumption is wrong.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from deic_core import DEIC


class ClinicalDEICAdapter:
    """
    Uses DEIC to assess patient deterioration by mapping:
      patient  -> item
      station  -> source
      vitals   -> value
      baseline -> initial_values

    NOTE: group_size is hardcoded to 4, matching DEIC's
    current assumption. The clinical environment generates
    variable groups (2-6). This mismatch is the test.
    """

    def __init__(self, adaptive_trust=True):
        self.adaptive_trust = adaptive_trust

    def diagnose(self, env):
        baseline = env.get_baseline_vitals()
        patients = env.get_patients()
        stations = env.get_stations()
        budget = env.config.max_queries

        engine = DEIC(adaptive_trust=self.adaptive_trust)
        engine.initialize_beliefs({
            'items': patients,
            'sources': stations,
            'group_sizes': [2, 3, 4, 5, 6],        # Variable group sizes
            'valid_multipliers': [1.3, 1.8, 2.5],
            'initial_values': baseline,
        })

        queried_pairs = set()

        # Phase A: Trust discovery
        while env.turn < budget - 1 and engine._trusted_source is None:
            station, patient = engine.select_query({
                'remaining_turns': budget - 1 - env.turn,
                'queried_pairs': queried_pairs,
            })

            result = env.query(station, patient)
            queried_pairs.add((station, patient))

            if result.get("status") == "timeout":
                break
            if "reported_vitals" in result:
                engine.update_observation(
                    station, patient, result["reported_vitals"], env.turn
                )
                if engine._trusted_source is None and not self.adaptive_trust:
                    engine.update_trust()

        # Phase B: Structural queries
        while env.turn < budget - 1 and engine._trusted_source is not None:
            active = engine.score_hypotheses()
            if len(active) <= 1:
                break

            station, patient = engine.select_query({
                'remaining_turns': budget - 1 - env.turn,
                'queried_pairs': queried_pairs,
            })

            result = env.query(station, patient)
            queried_pairs.add((station, patient))

            if result.get("status") == "timeout":
                break
            if "reported_vitals" in result:
                engine.update_observation(
                    station, patient, result["reported_vitals"], env.turn
                )

        proposed = engine.propose_state()
        return env.submit_assessment(proposed)
