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
from deic_core import (
    DEIC,
    BeliefInspector,
    CommitController,
    MinimalPlanner,
    SelfModel,
    benchmark_generator,
)


def _trajectory_entry(action, fault_prior):
    return {"next_action": action, "confidence_scores": dict(fault_prior)}


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


def _fit_score(result):
    if result.get("active_hypotheses", 0) <= 0:
        return -1.0
    return (
        float(result.get("active_hypotheses", 0))
        + float(result.get("confidence_margin", 0.0))
        - 0.01 * float(result.get("entropy", 0.0))
    )


def _is_better_replay_result(candidate, current_best, candidate_spec, best_spec):
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


class DEICBenchmarkAdapter:
    """
    Drop-in replacement for DiscreteStructureAgentV2 that delegates
    all inference to the standalone DEIC module.
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
        enable_adapt_refine=True,
        enable_upward_capacity_trigger=False,
        enable_final_contradiction_probe=True,
        enable_post_adaptation_guarded_probe=False,
        enable_post_probe_family_proposal=False,
    ):
        self.adaptive_trust = adaptive_trust
        self.use_controller = use_controller
        self.use_planner = use_planner
        self.memory = memory
        self.enable_self_model = enable_self_model
        self.confidence_threshold = confidence_threshold
        self.entropy_floor = entropy_floor
        self.enable_adapt_refine = enable_adapt_refine
        self.enable_upward_capacity_trigger = enable_upward_capacity_trigger
        self.enable_final_contradiction_probe = enable_final_contradiction_probe
        self.enable_post_adaptation_guarded_probe = enable_post_adaptation_guarded_probe
        self.enable_post_probe_family_proposal = enable_post_probe_family_proposal

    def solve(self, env):
        initial_state = env.get_initial_state()
        agents = env.get_agent_names()
        items = list(initial_state.keys())
        budget = env.config.max_turns

        # 1. Initialize DEIC
        engine = DEIC(adaptive_trust=self.adaptive_trust)
        engine.initialize_beliefs(
            {
                'items': items,
                'sources': agents,
                'initial_values': dict(initial_state),
            },
            hypothesis_generator=benchmark_generator(),
            memory=self.memory,
        )

        if self.use_planner:
            return self._solve_with_planner(env, engine, budget, agents)
        elif self.use_controller:
            return self._solve_with_controller(env, engine, budget, agents)
        else:
            return self._solve_legacy(env, engine, budget, agents)

    def _solve_legacy(self, env, engine, budget, agents):
        trajectory = []
        fault_prior = {a: 0.1 for a in agents}
        queried_pairs = set()
        inspector = BeliefInspector(engine)

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
        result["final_workspace"] = inspector.workspace(memory=self.memory)
        return trajectory, result

    def _solve_with_controller(self, env, engine, budget, agents):
        trajectory = []
        fault_prior = {a: 0.1 for a in agents}
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
                commit_action = {"type": "commit_consensus", "proposed_inventory": proposed}
                trajectory.append(_trajectory_entry(commit_action, fault_prior))
                result = env.step(commit_action)
                result["final_workspace"] = inspector.workspace(memory=self.memory)
                return trajectory, result
            elif decision == CommitController.ACTION_ESCALATE:
                escalate_action = {"type": "escalate_c6_unresolved"}
                trajectory.append(_trajectory_entry(escalate_action, fault_prior))
                result = env.step(escalate_action)
                result["final_workspace"] = inspector.workspace(memory=self.memory)
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

    def _solve_with_planner(self, env, engine, budget, agents):
        trajectory = []
        fault_prior = {a: 0.1 for a in agents}
        queried_pairs = set()
        inspector = BeliefInspector(engine)
        planner = MinimalPlanner(
            confidence_threshold=self.confidence_threshold,
            entropy_floor=self.entropy_floor,
            enable_adapt_refine=self.enable_adapt_refine,
            enable_upward_capacity_trigger=self.enable_upward_capacity_trigger,
            enable_final_contradiction_probe=self.enable_final_contradiction_probe,
            enable_post_adaptation_guarded_probe=self.enable_post_adaptation_guarded_probe,
            enable_post_probe_family_proposal=self.enable_post_probe_family_proposal,
        )
        item_queries = {it: set() for it in engine._items}

        # Telemetry for structure adaptation
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

        while True:
            remaining = budget - 1 - env.turn
            ws = inspector.workspace(memory=self.memory)
            ws.adaptation_count = engine.adaptation_count
            ws.current_family_spec = str(engine._current_generator.family_spec()) if engine._current_generator and hasattr(engine._current_generator, 'family_spec') else ""
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
                commit_action = {"type": "commit_consensus", "proposed_inventory": proposed}
                entry = _trajectory_entry(commit_action, fault_prior)
                entry["planner_mode"] = mode
                entry["rationale"] = decision.rationale
                entry["recommendation"] = decision.recommendation
                entry["action"] = commit_action
                entry["remaining_budget"] = max(0, remaining)
                trajectory.append(entry)
                result = env.step(commit_action)
                if engine.adaptation_count > 0:
                    post_adaptation_commit_turn = env.turn
                    post_adaptation_wrong_commit = not result.get("consensus_reached", False)
                    ws.post_adaptation_commit_turn = post_adaptation_commit_turn
                    ws.post_adaptation_wrong_commit = post_adaptation_wrong_commit
                if contradiction_surface_turn >= 0 and recovery_attempt_started and not recovery_path_taken:
                    recovery_path_taken = "adjacent_replay_then_commit"
                    ws.recovery_path_taken = recovery_path_taken
                ws.final_outcome_category = _final_outcome_category(
                    ws,
                    correct=result.get("consensus_reached", False),
                    escalated=False,
                )
                result["final_workspace"] = ws
                return trajectory, result
            elif mode == "ESCALATE":
                escalate_action = {"type": "escalate_c6_unresolved"}
                entry = _trajectory_entry(escalate_action, fault_prior)
                entry["planner_mode"] = mode
                entry["rationale"] = decision.rationale
                entry["recommendation"] = decision.recommendation
                entry["action"] = escalate_action
                entry["remaining_budget"] = max(0, remaining)
                trajectory.append(entry)
                result = env.step(escalate_action)
                ws.family_search_outcome = family_search_outcome or "escalated"
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
                result["final_workspace"] = ws
                return trajectory, result
            elif mode == "RESET_TRUST":
                engine.reset_trust()
                entry = _trajectory_entry({"type": "reset_trust"}, fault_prior)
                entry["planner_mode"] = mode
                entry["rationale"] = decision.rationale
                entry["recommendation"] = decision.recommendation
                entry["action"] = {"type": "reset_trust"}
                entry["remaining_budget"] = max(0, remaining)
                trajectory.append(entry)
                continue
            elif mode == "CONTRADICTION_PROBE":
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
                    item = min(untouched, key=lambda it: (len(item_queries.get(it, set())), engine._items.index(it)))
                    source = engine._trusted_source
                else:
                    source, item = engine.select_query({
                        'remaining_turns': remaining,
                        'queried_pairs': queried_pairs,
                    })
                action = {"type": "query", "target_agent": source, "item_id": item}
                entry = _trajectory_entry(action, fault_prior)
                entry["planner_mode"] = mode
                entry["rationale"] = decision.rationale
                entry["recommendation"] = decision.recommendation
                entry["action"] = action
                entry["remaining_budget"] = max(0, remaining)
                trajectory.append(entry)
                pre_query_entropy = ws.entropy
                obs = env.step(action)
                queried_pairs.add((source, item))
                item_queries[item].add(source)
                if obs.get("status") == "budget_exhausted":
                    pass
                elif "reported_quantity" in obs:
                    engine.update_observation(source, item, obs["reported_quantity"], env.turn)
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
                recovery_attempt_started = True
                recovery_path_taken = "post_probe_family_proposal"
                post_probe_family_proposal_count += 1
                post_probe_family_candidates_tested = []
                post_probe_family_adopted = ""

                current_fit = {
                    "active_hypotheses": ws.get("active_hypotheses_count", 0),
                    "confidence_margin": ws.get("confidence_margin", 0.0),
                    "entropy": ws.get("entropy", 0.0),
                }
                post_probe_family_fit_current = _fit_score(current_fit)

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

                for spec in candidates:
                    post_probe_family_candidates_tested.append(str(spec))
                    replay = engine.reinitialize_beliefs(HypothesisGenerator.from_spec(spec))
                    if replay["active_hypotheses"] <= 0:
                        continue
                    if best_result is None or _is_better_replay_result(replay, best_result, spec, best_spec):
                        best_result = replay
                        best_spec = spec

                if best_result is not None:
                    post_probe_family_fit_best_candidate = _fit_score(best_result)
                    engine.reinitialize_beliefs(HypothesisGenerator.from_spec(best_spec))
                    engine.adaptation_count = saved_ac + 1
                    post_probe_family_adopted = str(best_spec)
                    family_search_trigger = "post_probe_family_proposal"
                    family_search_outcome = "adopted"
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
                    entry = _trajectory_entry(
                        {
                            "type": "post_probe_family_proposal",
                            "outcome": "adopted",
                            "adopted_family": post_probe_family_adopted,
                            "candidates": list(post_probe_family_candidates_tested),
                        },
                        fault_prior,
                    )
                    entry["planner_mode"] = mode
                    entry["rationale"] = decision.rationale
                    entry["recommendation"] = decision.recommendation
                    entry["action"] = {
                        "type": "post_probe_family_proposal",
                        "outcome": "adopted",
                        "adopted_family": post_probe_family_adopted,
                        "candidates": list(post_probe_family_candidates_tested),
                    }
                    entry["remaining_budget"] = max(0, remaining)
                    trajectory.append(entry)
                    continue

                engine._hypotheses = saved_h
                engine._queried_values = saved_q
                engine._current_generator = saved_g
                engine.adaptation_count = saved_ac
                post_probe_family_fit_best_candidate = -1.0
                recovery_blocker = "post_probe_family_proposal_no_survivor"
                family_search_trigger = "post_probe_family_proposal"
                family_search_outcome = "escalated"
                escalate_action = {"type": "escalate_c6_unresolved"}
                entry = _trajectory_entry(
                    {
                        "type": "post_probe_family_proposal",
                        "outcome": "rejected",
                        "candidates": list(post_probe_family_candidates_tested),
                    },
                    fault_prior,
                )
                entry["planner_mode"] = mode
                entry["rationale"] = decision.rationale
                entry["recommendation"] = decision.recommendation
                entry["action"] = {
                    "type": "post_probe_family_proposal",
                    "outcome": "rejected",
                    "candidates": list(post_probe_family_candidates_tested),
                }
                entry["remaining_budget"] = max(0, remaining)
                trajectory.append(entry)
                escalate_entry = _trajectory_entry(escalate_action, fault_prior)
                escalate_entry["planner_mode"] = "ESCALATE"
                escalate_entry["rationale"] = "No post-probe family candidate survived trusted replay."
                escalate_entry["recommendation"] = "Escalate honestly after bounded proposal failure."
                escalate_entry["action"] = escalate_action
                escalate_entry["remaining_budget"] = max(0, remaining)
                trajectory.append(escalate_entry)
                result = env.step(escalate_action)
                ws.family_search_trigger = family_search_trigger
                ws.family_search_outcome = family_search_outcome
                ws.recovery_blocker = recovery_blocker
                ws.recovery_path_taken = recovery_path_taken
                ws.family_proposal_opened_after_probe = family_proposal_opened_after_probe
                ws.post_probe_family_proposal_count = post_probe_family_proposal_count
                ws.post_probe_family_candidates_tested = list(post_probe_family_candidates_tested)
                ws.post_probe_family_adopted = post_probe_family_adopted
                ws.post_probe_family_fit_current = post_probe_family_fit_current
                ws.post_probe_family_fit_best_candidate = post_probe_family_fit_best_candidate
                ws.final_outcome_category = _final_outcome_category(ws, correct=False, escalated=True)
                result["final_workspace"] = ws
                return trajectory, result
            elif mode == "ADAPT_STRUCTURE":
                if planner.upward_capacity_trigger_ready(ws):
                    family_search_trigger = "precollapse_capacity_upward"
                else:
                    family_search_trigger = "rule0_structural_contradiction"
                if contradiction_surface_turn >= 0 and family_search_trigger == "rule0_structural_contradiction":
                    recovery_attempt_started = True
                    if not recovery_path_taken:
                        recovery_path_taken = "adjacent_replay"
                gen = engine._current_generator
                if gen is None or not hasattr(gen, 'adjacent_families'):
                    family_search_outcome = "exhausted"
                    if contradiction_surface_turn >= 0 and not recovery_blocker:
                        recovery_blocker = "no_adjacent_candidates"
                    continue
                candidates = gen.adjacent_families()
                if not candidates:
                    family_search_outcome = "exhausted"
                    if contradiction_surface_turn >= 0 and not recovery_blocker:
                        recovery_blocker = "no_adjacent_candidates"
                    continue
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
                            if best_result is None or (replay['active_hypotheses'] > best_result['active_hypotheses'] or (replay['active_hypotheses'] == best_result['active_hypotheses'] and replay['confidence_margin'] > best_result['confidence_margin'])):
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
                entry = _trajectory_entry({"type": "adapt_structure", "outcome": family_search_outcome}, fault_prior)
                entry["planner_mode"] = mode
                entry["rationale"] = decision.rationale
                entry["recommendation"] = decision.recommendation
                entry["action"] = {"type": "adapt_structure", "outcome": family_search_outcome}
                entry["remaining_budget"] = max(0, remaining)
                trajectory.append(entry)
                continue

            elif mode in ("EXPLORE", "REFINE", "ADAPT_REFINE"):
                if engine.adaptation_count > 0:
                    post_adaptation_queries += 1
                source, item = None, None
                
                if mode == "EXPLORE" and engine._trusted_source is None:
                    # DIAGONAL PROBING: Query different sources on unique items
                    # to maximize the chance of hitting a shifted value early.
                    # We pick an agent and give them an item they haven't seen.
                    source = agents[env.turn % len(agents)]
                    
                    # Pick an unqueried item, or rotate
                    unqueried = [it for it in engine._items if it not in engine._queried_values]
                    if unqueried:
                        item = unqueried[0]
                    else:
                        item = engine._items[env.turn % len(engine._items)]
                    
                    # Ensure this specific (source, item) hasn't been queried
                    if (source, item) in queried_pairs:
                        # Fallback to engine's suggestion if diagonal is blocked
                        source, item = engine.select_query({
                            'remaining_turns': remaining,
                            'queried_pairs': queried_pairs,
                        })
                elif mode == "EXPLORE":
                    # Trust locked but still in EXPLORE? Fallback to engine.
                    source, item = engine.select_query({
                        'remaining_turns': remaining,
                        'queried_pairs': queried_pairs,
                    })
                else: 
                    # REFINE mode: InfoGain query
                    source, item = engine.select_query({
                        'remaining_turns': remaining,
                        'queried_pairs': queried_pairs,
                    })

                action = {"type": "query", "target_agent": source, "item_id": item}
                entry = _trajectory_entry(action, fault_prior)
                entry["planner_mode"] = mode
                entry["rationale"] = decision.rationale
                entry["recommendation"] = decision.recommendation
                entry["action"] = action
                entry["remaining_budget"] = max(0, remaining)
                trajectory.append(entry)
                
                pre_query_entropy = ws.entropy
                obs = env.step(action)
                queried_pairs.add((source, item))
                item_queries[item].add(source)

                if obs.get("status") == "budget_exhausted":
                    pass
                elif "reported_quantity" in obs:
                    engine.update_observation(source, item, obs["reported_quantity"], env.turn)
                    if engine._trusted_source is None and not self.adaptive_trust:
                        engine.update_trust()
                    if engine.adaptation_count > 0:
                        post_state = inspector.inspect(top_n=1)
                        post_adaptation_query_value_total += max(
                            0.0, pre_query_entropy - post_state["entropy"]
                        )
