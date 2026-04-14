"""
Clinical Adapter for DEIC

Bridges ClinicalEnvironment to the domain-agnostic DEIC engine.
Uses ClinicalHypothesisGenerator for variable group-size support.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from deic_core import (
    DEIC,
    clinical_generator,
    BeliefInspector,
    CommitController,
    MinimalPlanner,
    SelfModel,
    build_advisory_appraisal,
    evaluate_conscience_advisory,
    apply_conscience_advisory_trace,
    conscience_advisory_trace_dict,
)


def _is_saturated_with_untouched(ws):
    return (
        ws.get("trusted_shifted_count_lower_bound", 0) == ws.get("current_family_capacity", -1)
        and ws.get("items_queried", 0) < ws.get("items_total", 0)
    )


def _final_outcome_category(ws, correct, escalated):
    if escalated:
        return "ESCALATED"
    if correct and ws.get("adaptation_count", 0) > 0:
        return "CORRECT_ADAPT_RECOVERY"
    if correct:
        return "STABLE_CORRECT"
    if ws.get("adaptation_count", 0) > 0 and _is_saturated_with_untouched(ws):
        return "POST_ADAPT_SATURATED_WRONG_COMMIT"
    if _is_saturated_with_untouched(ws):
        return "SATURATED_PRE_ADAPT_WRONG_COMMIT"
    if ws.get("adaptation_count", 0) > 0:
        return "POST_ADAPT_WRONG_COMMIT"
    return "STABLE_WRONG_COMMIT"


def _annotate_conscience_advisory(ws, candidate_action, domain_profile):
    appraisal = build_advisory_appraisal(ws, domain_profile)
    result = evaluate_conscience_advisory(ws, candidate_action, domain_profile)
    apply_conscience_advisory_trace(ws, appraisal, result)
    return conscience_advisory_trace_dict(ws)


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
        enable_post_adaptation_guarded_probe=False,
        enable_post_probe_family_proposal=False,
        enable_conscience_advisory=False,
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
        self.enable_post_adaptation_guarded_probe = enable_post_adaptation_guarded_probe
        self.enable_post_probe_family_proposal = enable_post_probe_family_proposal
        self.enable_conscience_advisory = enable_conscience_advisory

    @staticmethod
    def _is_better_fit(candidate, current_best, candidate_spec, best_spec):
        """Rank candidate replay results deterministically."""
        candidate_key = (
            candidate.get("active_hypotheses", 0),
            candidate.get("confidence_margin", 0.0),
            -candidate.get("entropy", 0.0),
            -getattr(candidate_spec, "group_size", 0),
        )
        best_key = (
            current_best.get("active_hypotheses", 0),
            current_best.get("confidence_margin", 0.0),
            -current_best.get("entropy", 0.0),
            -getattr(best_spec, "group_size", 0),
        )
        return candidate_key > best_key

    @staticmethod
    def _fit_score(result):
        if result.get("active_hypotheses", 0) <= 0:
            return -1.0
        return (
            float(result.get("active_hypotheses", 0))
            + float(result.get("confidence_margin", 0.0))
            - 0.01 * float(result.get("entropy", 0.0))
        )

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
            enable_post_adaptation_guarded_probe=self.enable_post_adaptation_guarded_probe,
            enable_post_probe_family_proposal=self.enable_post_probe_family_proposal,
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
        post_adaptation_probe_count = 0
        post_adaptation_probe_turn = -1
        contradiction_after_post_adaptation_probe = False
        untouched_item_count_at_probe = -1
        contradiction_surface_turn = -1
        recovery_attempt_started = False
        recovery_path_taken = ""
        recovery_blocker = ""
        family_proposal_opened_after_probe = False
        family_proposal_trigger_count = 0
        candidate_family_specs_tested = []
        adopted_family_spec = ""
        proposal_turn = -1
        proposal_search_outcome = ""
        fit_score_current_family = 0.0
        fit_score_candidate_family = 0.0
        family_search_exhausted = False
        post_probe_family_proposal_count = 0
        post_probe_family_candidates_tested = []
        post_probe_family_adopted = ""
        post_probe_family_fit_current = 0.0
        post_probe_family_fit_best_candidate = 0.0
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
            ws.post_adaptation_probe_count = post_adaptation_probe_count
            ws.post_adaptation_probe_turn = post_adaptation_probe_turn
            ws.contradiction_after_post_adaptation_probe = contradiction_after_post_adaptation_probe
            ws.untouched_item_count_at_probe = untouched_item_count_at_probe
            ws.contradiction_surface_turn = contradiction_surface_turn
            ws.recovery_attempt_started = recovery_attempt_started
            ws.recovery_path_taken = recovery_path_taken
            ws.recovery_blocker = recovery_blocker
            ws.family_proposal_opened_after_probe = family_proposal_opened_after_probe
            ws.family_proposal_trigger_count = family_proposal_trigger_count
            ws.candidate_family_specs_tested = list(candidate_family_specs_tested)
            ws.adopted_family_spec = adopted_family_spec
            ws.proposal_turn = proposal_turn
            ws.proposal_search_outcome = proposal_search_outcome
            ws.fit_score_current_family = fit_score_current_family
            ws.fit_score_candidate_family = fit_score_candidate_family
            ws.family_search_exhausted = family_search_exhausted
            ws.post_probe_family_proposal_count = post_probe_family_proposal_count
            ws.post_probe_family_candidates_tested = list(post_probe_family_candidates_tested)
            ws.post_probe_family_adopted = post_probe_family_adopted
            ws.post_probe_family_fit_current = post_probe_family_fit_current
            ws.post_probe_family_fit_best_candidate = post_probe_family_fit_best_candidate
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
                        "conscience_advisory": _annotate_conscience_advisory(ws, "COMMIT", "clinical")
                        if self.enable_conscience_advisory else None,
                    }
                )
                if engine.adaptation_count > 0:
                    post_adaptation_commit_turn = env.turn
                    post_adaptation_wrong_commit = not res.get("correct", False)
                    ws.post_adaptation_commit_turn = post_adaptation_commit_turn
                    ws.post_adaptation_wrong_commit = post_adaptation_wrong_commit
                if contradiction_surface_turn >= 0 and recovery_attempt_started and not recovery_path_taken:
                    recovery_path_taken = "adjacent_replay_then_commit"
                    ws.recovery_path_taken = recovery_path_taken
                ws.final_outcome_category = _final_outcome_category(
                    ws,
                    correct=res.get("correct", False),
                    escalated=False,
                )
                if self.enable_conscience_advisory:
                    _annotate_conscience_advisory(ws, "COMMIT", "clinical")
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
                        "conscience_advisory": _annotate_conscience_advisory(ws, "ESCALATE", "clinical")
                        if self.enable_conscience_advisory else None,
                    }
                )
                if engine.adaptation_count > 0:
                    post_adaptation_escalation_turn = env.turn
                    ws.post_adaptation_escalation_turn = post_adaptation_escalation_turn
                if contradiction_surface_turn >= 0 and not recovery_blocker:
                    if ws.get("trusted_shifted_count_lower_bound", 0) > ws.get("current_family_capacity", 0):
                        recovery_blocker = "adjacent_recovery_ceiling"
                    elif recovery_attempt_started:
                        recovery_blocker = "budget_exhausted_after_adjacent_recovery"
                    else:
                        recovery_blocker = "contradiction_surface_without_recovery_open"
                    if recovery_attempt_started and not recovery_path_taken:
                        recovery_path_taken = "adjacent_replay_then_escalate"
                    ws.recovery_blocker = recovery_blocker
                    ws.recovery_path_taken = recovery_path_taken
                ws.final_outcome_category = _final_outcome_category(ws, correct=False, escalated=True)
                if self.enable_conscience_advisory:
                    _annotate_conscience_advisory(ws, "ESCALATE", "clinical")
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
                is_post_adaptation_probe = engine.adaptation_count > 0
                if is_post_adaptation_probe:
                    post_adaptation_probe_count += 1
                    post_adaptation_probe_turn = env.turn
                    untouched_item_count_at_probe = len(untouched)
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
                        surfaced = len([h for h in engine._hypotheses if h["prob"] > 1e-6]) == 0
                        post_state = inspector.inspect(top_n=1)
                        post_adaptation_query_value_total += max(
                            0.0, pre_query_entropy - post_state["entropy"]
                        )
                        contradiction_after_post_adaptation_probe = (
                            contradiction_after_post_adaptation_probe
                            or surfaced
                        )
                        if surfaced and contradiction_surface_turn < 0:
                            contradiction_surface_turn = env.turn
                continue
            elif mode == "POST_PROBE_FAMILY_PROPOSAL":
                from deic_core.hypothesis import HypothesisGenerator

                family_proposal_opened_after_probe = True
                family_proposal_trigger_count += 1
                recovery_attempt_started = True
                recovery_path_taken = "post_probe_family_proposal"
                post_probe_family_proposal_count += 1
                post_probe_family_candidates_tested = []
                post_probe_family_adopted = ""
                candidate_family_specs_tested = []
                adopted_family_spec = ""
                proposal_turn = env.turn
                proposal_search_outcome = "opened"
                family_search_exhausted = False
                current_fit = {
                    "active_hypotheses": ws.get("active_hypotheses_count", 0),
                    "confidence_margin": ws.get("confidence_margin", 0.0),
                    "entropy": ws.get("entropy", 0.0),
                }
                post_probe_family_fit_current = self._fit_score(current_fit)
                fit_score_current_family = post_probe_family_fit_current

                gen = engine._current_generator
                candidates = []
                if gen is not None and hasattr(gen, "post_probe_proposal_families"):
                    candidates = gen.post_probe_proposal_families(
                        shifted_lb=ws.get("trusted_shifted_count_lower_bound", 0),
                        items_total=len(engine._items),
                        max_candidates=2,
                    )

                best_result = None
                best_spec = None
                saved_h = [dict(h) for h in engine._hypotheses]
                saved_q = dict(engine._queried_values)
                saved_g = engine._current_generator
                saved_ac = engine.adaptation_count
                trace_action = {"type": "post_probe_family_proposal", "candidates": []}

                for spec in candidates:
                    post_probe_family_candidates_tested.append(str(spec))
                    candidate_family_specs_tested.append(str(spec))
                    trace_action["candidates"].append(str(spec))
                    replay = engine.reinitialize_beliefs(HypothesisGenerator.from_spec(spec))
                    if replay["active_hypotheses"] <= 0:
                        continue
                    if best_result is None or self._is_better_fit(replay, best_result, spec, best_spec):
                        best_result = replay
                        best_spec = spec

                if best_result is not None and self._fit_score(best_result) > post_probe_family_fit_current:
                    post_probe_family_fit_best_candidate = self._fit_score(best_result)
                    fit_score_candidate_family = post_probe_family_fit_best_candidate
                    engine.reinitialize_beliefs(HypothesisGenerator.from_spec(best_spec))
                    engine.adaptation_count = saved_ac + 1
                    post_probe_family_adopted = str(best_spec)
                    adopted_family_spec = post_probe_family_adopted
                    family_search_trigger = "post_probe_family_proposal"
                    family_search_outcome = "adopted"
                    proposal_search_outcome = "adopted"
                    adaptation_turn = env.turn
                    remaining_budget_at_adaptation = max(0, remaining)
                    adaptation_before_full_coverage = (
                        len(engine._queried_values) < len(engine._items)
                    )
                    post_adaptation_queries = 0
                    post_adaptation_query_value_total = 0.0
                    post_adaptation_probe_count = max(post_adaptation_probe_count, engine.adaptation_count)
                    if self.enable_adapt_refine and engine._trusted_source is not None:
                        engine._suspicion_scores[engine._trusted_source] = 0
                    trace_action["outcome"] = "adopted"
                    trace_action["adopted_family"] = post_probe_family_adopted
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

                engine._hypotheses = saved_h
                engine._queried_values = saved_q
                engine._current_generator = saved_g
                engine.adaptation_count = saved_ac
                post_probe_family_fit_best_candidate = -1.0
                fit_score_candidate_family = post_probe_family_fit_best_candidate
                recovery_blocker = "post_probe_family_proposal_no_survivor"
                family_search_trigger = "post_probe_family_proposal"
                family_search_outcome = "escalated"
                proposal_search_outcome = "escalated"
                family_search_exhausted = True
                trace_action["outcome"] = "rejected"
                decision_trace.append(
                    {
                        "planner_mode": mode,
                        "rationale": decision.rationale,
                        "recommendation": decision.recommendation,
                        "remaining_budget": max(0, remaining),
                        "action": trace_action,
                    }
                )
                ws.family_search_trigger = family_search_trigger
                ws.family_search_outcome = family_search_outcome
                ws.recovery_blocker = recovery_blocker
                ws.recovery_path_taken = recovery_path_taken
                ws.family_proposal_opened_after_probe = family_proposal_opened_after_probe
                ws.family_proposal_trigger_count = family_proposal_trigger_count
                ws.candidate_family_specs_tested = list(candidate_family_specs_tested)
                ws.adopted_family_spec = adopted_family_spec
                ws.proposal_turn = proposal_turn
                ws.proposal_search_outcome = proposal_search_outcome
                ws.fit_score_current_family = fit_score_current_family
                ws.fit_score_candidate_family = fit_score_candidate_family
                ws.family_search_exhausted = family_search_exhausted
                ws.post_probe_family_proposal_count = post_probe_family_proposal_count
                ws.post_probe_family_candidates_tested = list(post_probe_family_candidates_tested)
                ws.post_probe_family_adopted = post_probe_family_adopted
                ws.post_probe_family_fit_current = post_probe_family_fit_current
                ws.post_probe_family_fit_best_candidate = post_probe_family_fit_best_candidate
                ws.final_outcome_category = _final_outcome_category(ws, correct=False, escalated=True)
                return {
                    "escalated": True,
                    "abstained": True,
                    "final_workspace": ws,
                    "decision_trace": decision_trace,
                }
            elif mode == "ADAPT_STRUCTURE":
                if planner.upward_capacity_trigger_ready(ws):
                    family_search_trigger = "precollapse_capacity_upward"
                else:
                    family_search_trigger = "rule0_structural_contradiction"
                if contradiction_surface_turn >= 0 and family_search_trigger == "rule0_structural_contradiction":
                    recovery_attempt_started = True
                    if not recovery_path_taken:
                        recovery_path_taken = "adjacent_replay"
                trace_action = {"type": "adapt_structure", "trigger": family_search_trigger}
                gen = engine._current_generator
                if gen is None or not hasattr(gen, 'adjacent_families'):
                    if contradiction_surface_turn >= 0 and not recovery_blocker:
                        recovery_blocker = "no_adjacent_candidates"
                    return {
                        "escalated": True,
                        "abstained": True,
                        "final_workspace": ws,
                        "decision_trace": decision_trace,
                    }
                candidates = gen.adjacent_families()
                if not candidates:
                    if contradiction_surface_turn >= 0 and not recovery_blocker:
                        recovery_blocker = "no_adjacent_candidates"
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
                    post_adaptation_queries = 0
                    post_adaptation_query_value_total = 0.0
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
