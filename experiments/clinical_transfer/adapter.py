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
        enable_self_model=True,
        confidence_threshold=0.95,
        entropy_floor=0.10,
        coverage_threshold=0.85,
        enable_adapt_refine=True,
        hypothesis_generator=None,
        enable_upward_capacity_trigger=False,
        enable_final_contradiction_probe=True,
    ):
        self.adaptive_trust = adaptive_trust
        self.use_controller = use_controller
        self.use_planner = use_planner
        self.memory = memory
        self.enable_self_model = enable_self_model
        self.confidence_threshold = confidence_threshold
        self.entropy_floor = entropy_floor
        self.coverage_threshold = coverage_threshold
        self.enable_adapt_refine = enable_adapt_refine
        self.hypothesis_generator = hypothesis_generator
        self.enable_upward_capacity_trigger = enable_upward_capacity_trigger
        self.enable_final_contradiction_probe = enable_final_contradiction_probe

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
        inspector = BeliefInspector(engine)

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
        res = env.submit_assessment(proposed)
        res["final_workspace"] = inspector.workspace(memory=self.memory)
        return res

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
                res["final_workspace"] = inspector.workspace(memory=self.memory)
                return res
            elif decision == CommitController.ACTION_ESCALATE:
                res = env.escalate_uncertainty()
                res["final_workspace"] = inspector.workspace(memory=self.memory)
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
            enable_upward_capacity_trigger=self.enable_upward_capacity_trigger,
            enable_final_contradiction_probe=self.enable_final_contradiction_probe,
        )
        item_queries = {it: set() for it in engine._items}
        stations = env.get_stations()
        family_search_trigger = ""
        family_search_outcome = ""
        candidate_specs_tested = []
        trust_lock_turn = -1
        adaptation_turn = -1
        remaining_budget_at_adaptation = -1
        adaptation_before_full_coverage = False
        precollapse_capacity_trigger_turn = -1
        capacity_trigger_direction = ""
        contradiction_probe_trigger_turn = -1
        contradiction_probe_count = 0
        post_adaptation_queries = 0
        post_adaptation_commit_turn = -1
        post_adaptation_escalation_turn = -1
        post_adaptation_wrong_commit = False
        post_adaptation_query_value_total = 0.0
        decision_trace = []

        while True:
            remaining = budget - 1 - env.turn
            ws = inspector.workspace(memory=self.memory)
            ws.adaptation_count = engine.adaptation_count
            ws.current_family_spec = (
                str(engine._current_generator.family_spec())
                if engine._current_generator and hasattr(engine._current_generator, 'family_spec')
                else ""
            )
            ws.candidate_specs_tested = candidate_specs_tested
            ws.family_search_trigger = family_search_trigger
            ws.family_search_outcome = family_search_outcome
            if trust_lock_turn < 0 and ws.trusted_source_locked:
                trust_lock_turn = env.turn
            ws.trust_lock_turn = trust_lock_turn
            ws.adaptation_turn = adaptation_turn
            ws.remaining_budget_at_adaptation = remaining_budget_at_adaptation
            ws.adaptation_before_full_coverage = adaptation_before_full_coverage
            if (
                precollapse_capacity_trigger_turn < 0
                and self.enable_upward_capacity_trigger
                and ws.trusted_source_locked
                and ws.active_hypotheses_count > 0
                and ws.current_family_capacity >= 1
                and ws.trusted_shifted_count_lower_bound > ws.current_family_capacity
            ):
                precollapse_capacity_trigger_turn = env.turn
                capacity_trigger_direction = "UPWARD"
            ws.precollapse_capacity_trigger_turn = precollapse_capacity_trigger_turn
            ws.capacity_trigger_direction = capacity_trigger_direction
            ws.contradiction_probe_trigger_turn = contradiction_probe_trigger_turn
            ws.contradiction_probe_count = contradiction_probe_count
            ws.post_adaptation_queries = post_adaptation_queries
            ws.post_adaptation_commit_turn = post_adaptation_commit_turn
            ws.post_adaptation_escalation_turn = post_adaptation_escalation_turn
            ws.post_adaptation_wrong_commit = post_adaptation_wrong_commit
            ws.post_adaptation_query_value = (
                post_adaptation_query_value_total / post_adaptation_queries
                if post_adaptation_queries > 0 else 0.0
            )
            sm = SelfModel.from_workspace(ws) if self.enable_self_model else None
            decision = planner.decide(ws, sm, max(0, remaining))
            mode = decision.mode.value

            if mode == "EARLY_COMMIT":
                proposed = engine.propose_state()
                res = env.submit_assessment(proposed)
                decision_trace.append(
                    {
                        "planner_mode": mode,
                        "rationale": decision.rationale,
                        "recommendation": decision.recommendation,
                        "remaining_budget": max(0, remaining),
                        "action": {"type": "commit_assessment", "proposed_vitals": proposed},
                    }
                )
                if engine.adaptation_count > 0:
                    post_adaptation_commit_turn = env.turn
                    post_adaptation_wrong_commit = not res.get("correct", False)
                    ws.post_adaptation_commit_turn = post_adaptation_commit_turn
                    ws.post_adaptation_wrong_commit = post_adaptation_wrong_commit
                res["final_workspace"] = ws
                res["decision_trace"] = decision_trace
                return res
            if mode == "ESCALATE":
                ws.family_search_outcome = family_search_outcome or "escalated"
                decision_trace.append(
                    {
                        "planner_mode": mode,
                        "rationale": decision.rationale,
                        "recommendation": decision.recommendation,
                        "remaining_budget": max(0, remaining),
                        "action": {"type": "escalate_uncertainty"},
                    }
                )
                if engine.adaptation_count > 0:
                    post_adaptation_escalation_turn = env.turn
                    ws.post_adaptation_escalation_turn = post_adaptation_escalation_turn
                return {
                    "escalated": True,
                    "abstained": True,
                    "final_workspace": ws,
                    "decision_trace": decision_trace,
                }
            elif mode == "RESET_TRUST":
                decision_trace.append(
                    {
                        "planner_mode": mode,
                        "rationale": decision.rationale,
                        "recommendation": decision.recommendation,
                        "remaining_budget": max(0, remaining),
                        "action": {"type": "reset_trust"},
                    }
                )
                engine.reset_trust()
                continue
            elif mode == "CONTRADICTION_PROBE":
                trace_action = {"type": "query"}
                if contradiction_probe_trigger_turn < 0:
                    contradiction_probe_trigger_turn = env.turn
                contradiction_probe_count += 1
                untouched = [it for it in engine._items if it not in engine._queried_values]
                if untouched and engine._trusted_source is not None:
                    patient = min(untouched, key=lambda it: (len(item_queries.get(it, set())), engine._items.index(it)))
                    station = engine._trusted_source
                else:
                    station, patient = engine.select_query({
                        'remaining_turns': remaining,
                        'queried_pairs': queried_pairs,
                    })
                trace_action.update({"station": station, "patient": patient})
                decision_trace.append(
                    {
                        "planner_mode": mode,
                        "rationale": decision.rationale,
                        "recommendation": decision.recommendation,
                        "remaining_budget": max(0, remaining),
                        "action": trace_action,
                    }
                )

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
                continue
            elif mode == "ADAPT_STRUCTURE":
                if planner.upward_capacity_trigger_ready(ws):
                    family_search_trigger = "precollapse_capacity_upward"
                else:
                    family_search_trigger = "rule0_structural_contradiction"
                trace_action = {"type": "adapt_structure", "trigger": family_search_trigger}
                gen = engine._current_generator
                if gen is None or not hasattr(gen, 'adjacent_families'):
                    return {
                        "escalated": True,
                        "abstained": True,
                        "final_workspace": ws,
                        "decision_trace": decision_trace,
                    }
                candidates = gen.adjacent_families()
                if not candidates:
                    return {
                        "escalated": True,
                        "abstained": True,
                        "final_workspace": ws,
                        "decision_trace": decision_trace,
                    }
                saved_h = [dict(h) for h in engine._hypotheses]
                saved_q = dict(engine._queried_values)
                saved_g = engine._current_generator
                saved_ac = engine.adaptation_count
                best_result, best_spec = None, None
                from deic_core.hypothesis import HypothesisGenerator
                if family_search_trigger == "precollapse_capacity_upward":
                    upward_candidates = [
                        spec for spec in candidates
                        if getattr(spec, "group_size", 0) > ws.current_family_capacity
                    ]
                    if upward_candidates:
                        best_spec = min(upward_candidates, key=lambda spec: spec.group_size)
                        candidate_specs_tested.append(str(best_spec))
                        best_result = engine.reinitialize_beliefs(HypothesisGenerator.from_spec(best_spec))
                        if best_result['active_hypotheses'] <= 0:
                            best_spec = None
                    else:
                        family_search_outcome = "exhausted"
                else:
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
                    family_search_outcome = family_search_outcome or "rejected"
                trace_action["outcome"] = family_search_outcome
                trace_action["candidates"] = list(candidate_specs_tested)
                decision_trace.append(
                    {
                        "planner_mode": mode,
                        "rationale": decision.rationale,
                        "recommendation": decision.recommendation,
                        "remaining_budget": max(0, remaining),
                        "action": trace_action,
                    }
                )
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
                decision_trace.append(
                    {
                        "planner_mode": mode,
                        "rationale": decision.rationale,
                        "recommendation": decision.recommendation,
                        "remaining_budget": max(0, remaining),
                        "action": {"type": "query", "station": station, "patient": patient},
                    }
                )

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
