"""
Clinical Adapter for DEIC

Bridges ClinicalEnvironment to the domain-agnostic DEIC engine.
Uses ClinicalHypothesisGenerator for variable group-size support.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from deic_core import DEIC, clinical_generator, BeliefInspector, CommitController, MinimalPlanner, SelfModel


class ClinicalDEICAdapter:
    """
    Uses DEIC to assess patient deterioration by mapping:
      patient  -> item
      station  -> source
      vitals   -> value
      baseline -> initial_values
    """

    def __init__(
        self,
        adaptive_trust=True,
        use_controller=False,
        use_planner=False,
        memory=None,
        confidence_threshold=0.95,
        entropy_floor=0.10,
        coverage_threshold=0.85,
        enable_adapt_refine=True,
        hypothesis_generator=None,
    ):
        self.adaptive_trust = adaptive_trust
        self.use_controller = use_controller
        self.use_planner = use_planner
        self.memory = memory
        self.confidence_threshold = confidence_threshold
        self.entropy_floor = entropy_floor
        self.coverage_threshold = coverage_threshold
        self.enable_adapt_refine = enable_adapt_refine
        self.hypothesis_generator = hypothesis_generator

    @staticmethod
    def _is_better_fit(candidate, current_best):
        """Rank candidate replay results."""
        if candidate['active_hypotheses'] > current_best['active_hypotheses']:
            return True
        if candidate['active_hypotheses'] == current_best['active_hypotheses']:
            return candidate['confidence_margin'] > current_best['confidence_margin']
        return False

    def diagnose(self, env):
        baseline = env.get_baseline_vitals()
        patients = env.get_patients()
        stations = env.get_stations()
        budget = env.config.max_queries

        engine = DEIC(adaptive_trust=self.adaptive_trust)
        engine.initialize_beliefs(
            {'items': patients, 'sources': stations, 'initial_values': baseline},
            hypothesis_generator=self.hypothesis_generator or clinical_generator(),
            memory=self.memory
        )

        if self.use_planner:
            return self._diagnose_with_planner(env, engine, budget)
        elif self.use_controller:
            return self._diagnose_with_controller(env, engine, budget)
        else:
            return self._diagnose_legacy(env, engine, budget)

    def _diagnose_legacy(self, env, engine, budget):
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

    def _diagnose_with_controller(self, env, engine, budget):
        queried_pairs = set()
        inspector = BeliefInspector(engine)
        controller = CommitController(
            confidence_threshold=self.confidence_threshold,
            entropy_floor=self.entropy_floor
        )

        while True:
            remaining = budget - 1 - env.turn
            inspector_state = inspector.inspect(top_n=1)
            
            unqueried_items = [it for it in engine._items if it not in engine._queried_values]
            has_valid_queries = len(unqueried_items) > 0

            decision = controller.decide(inspector_state, max(0, remaining), has_valid_queries=has_valid_queries)

            if decision in (CommitController.ACTION_COMMIT, CommitController.ACTION_STOP):
                proposed = engine.propose_state()
                res = env.submit_assessment(proposed)
                res["final_workspace"] = inspector_state
                return res
            elif decision == CommitController.ACTION_ESCALATE:
                res = env.escalate_uncertainty()
                res["final_workspace"] = inspector_state
                return res
            
            elif decision == CommitController.ACTION_QUERY:
                station, patient = engine.select_query({
                    'remaining_turns': remaining,
                    'queried_pairs': queried_pairs,
                })
                result = env.query(station, patient)
                queried_pairs.add((station, patient))

                if result.get("status") == "timeout":
                    pass
                elif "reported_vitals" in result:
                    engine.update_observation(
                        station, patient, result["reported_vitals"], env.turn
                    )
                    if engine._trusted_source is None and not self.adaptive_trust:
                        engine.update_trust()

    def _diagnose_with_planner(self, env, engine, budget):
        queried_pairs = set()
        inspector = BeliefInspector(engine)
        planner = MinimalPlanner(
            confidence_threshold=self.confidence_threshold,
            entropy_floor=self.entropy_floor,
            coverage_threshold=self.coverage_threshold,
            enable_adapt_refine=self.enable_adapt_refine,
        )
        item_queries = {it: set() for it in engine._items}
        stations = env.get_stations()
        family_search_trigger = ""
        family_search_outcome = ""
        candidate_specs_tested = []
        adaptation_turn = -1
        remaining_budget_at_adaptation = -1
        adaptation_before_full_coverage = False
        post_adaptation_queries = 0
        post_adaptation_commit_turn = -1
        post_adaptation_escalation_turn = -1
        post_adaptation_wrong_commit = False
        post_adaptation_query_value_total = 0.0

        while True:
            remaining = budget - 1 - env.turn
            ws = inspector.workspace()
            ws.adaptation_count = engine.adaptation_count
            ws.current_family_spec = (
                str(engine._current_generator.family_spec())
                if engine._current_generator and hasattr(engine._current_generator, 'family_spec')
                else ""
            )
            ws.candidate_specs_tested = candidate_specs_tested
            ws.family_search_trigger = family_search_trigger
            ws.family_search_outcome = family_search_outcome
            ws.adaptation_turn = adaptation_turn
            ws.remaining_budget_at_adaptation = remaining_budget_at_adaptation
            ws.adaptation_before_full_coverage = adaptation_before_full_coverage
            ws.post_adaptation_queries = post_adaptation_queries
            ws.post_adaptation_commit_turn = post_adaptation_commit_turn
            ws.post_adaptation_escalation_turn = post_adaptation_escalation_turn
            ws.post_adaptation_wrong_commit = post_adaptation_wrong_commit
            ws.post_adaptation_query_value = (
                post_adaptation_query_value_total / post_adaptation_queries
                if post_adaptation_queries > 0 else 0.0
            )
            sm = SelfModel.from_workspace(ws)
            decision = planner.decide(ws, sm, max(0, remaining))
            mode = decision.mode.value

            if mode == "EARLY_COMMIT":
                proposed = engine.propose_state()
                res = env.submit_assessment(proposed)
                if engine.adaptation_count > 0:
                    post_adaptation_commit_turn = env.turn
                    post_adaptation_wrong_commit = not res.get("correct", False)
                    ws.post_adaptation_commit_turn = post_adaptation_commit_turn
                    ws.post_adaptation_wrong_commit = post_adaptation_wrong_commit
                res["final_workspace"] = ws
                return res
            if mode == "ESCALATE":
                ws.family_search_outcome = family_search_outcome or "escalated"
                if engine.adaptation_count > 0:
                    post_adaptation_escalation_turn = env.turn
                    ws.post_adaptation_escalation_turn = post_adaptation_escalation_turn
                return {"escalated": True, "abstained": True, "final_workspace": ws}
            elif mode == "RESET_TRUST":
                engine.reset_trust()
                continue
            elif mode == "ADAPT_STRUCTURE":
                family_search_trigger = "rule0_structural_contradiction"
                gen = engine._current_generator
                if gen is None or not hasattr(gen, 'adjacent_families'):
                    return {
                        "escalated": True,
                        "abstained": True,
                        "final_workspace": ws,
                    }
                candidates = gen.adjacent_families()
                if not candidates:
                    return {
                        "escalated": True,
                        "abstained": True,
                        "final_workspace": ws,
                    }
                saved_h = [dict(h) for h in engine._hypotheses]
                saved_q = dict(engine._queried_values)
                saved_g = engine._current_generator
                saved_ac = engine.adaptation_count
                best_result, best_spec = None, None
                from deic_core.hypothesis import HypothesisGenerator
                for spec in candidates:
                    candidate_specs_tested.append(str(spec))
                    replay = engine.reinitialize_beliefs(HypothesisGenerator.from_spec(spec))
                    if replay['active_hypotheses'] > 0:
                        if best_result is None or self._is_better_fit(replay, best_result):
                            best_result = replay
                            best_spec = spec
                if best_spec is not None:
                    engine.reinitialize_beliefs(HypothesisGenerator.from_spec(best_spec))
                    engine.adaptation_count = saved_ac + 1
                    if self.enable_adapt_refine and engine._trusted_source is not None:
                        engine._suspicion_scores[engine._trusted_source] = 0
                    family_search_outcome = "adopted"
                    adaptation_turn = env.turn
                    remaining_budget_at_adaptation = max(0, remaining)
                    adaptation_before_full_coverage = (
                        len(engine._queried_values) < len(engine._items)
                    )
                else:
                    engine._hypotheses = saved_h
                    engine._queried_values = saved_q
                    engine._current_generator = saved_g
                    engine.adaptation_count = saved_ac + 1
                    family_search_outcome = "rejected"
                continue
            
            elif mode in ("EXPLORE", "REFINE", "ADAPT_REFINE"):
                if engine.adaptation_count > 0:
                    post_adaptation_queries += 1
                station, patient = None, None
                
                if mode == "EXPLORE" and engine._trusted_source is None:
                    # DIAGONAL PROBING
                    station = stations[env.turn % len(stations)]
                    unqueried = [it for it in engine._items if it not in engine._queried_values]
                    if unqueried:
                        patient = unqueried[0]
                    else:
                        patient = engine._items[env.turn % len(engine._items)]
                    
                    if (station, patient) in queried_pairs:
                        station, patient = engine.select_query({
                            'remaining_turns': remaining,
                            'queried_pairs': queried_pairs,
                        })
                elif mode == "EXPLORE":
                    station, patient = engine.select_query({
                        'remaining_turns': remaining,
                        'queried_pairs': queried_pairs,
                    })
                else: 
                    station, patient = engine.select_query({
                        'remaining_turns': remaining,
                        'queried_pairs': queried_pairs,
                    })

                pre_query_entropy = ws.entropy
                result = env.query(station, patient)
                queried_pairs.add((station, patient))
                item_queries[patient].add(station)

                if result.get("status") == "timeout":
                    pass
                elif "reported_vitals" in result:
                    engine.update_observation(
                        station, patient, result["reported_vitals"], env.turn
                    )
                    if engine._trusted_source is None and not self.adaptive_trust:
                        engine.update_trust()
                    if engine.adaptation_count > 0:
                        post_state = inspector.inspect(top_n=1)
                        post_adaptation_query_value_total += max(
                            0.0, pre_query_entropy - post_state["entropy"]
                        )
