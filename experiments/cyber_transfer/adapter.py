"""
Cyber Incident Adapter for DEIC

Bridges the CyberIncidentEnvironment to the domain-agnostic
DEIC engine. Uses CyberHypothesisGenerator for domain-specific
hypothesis setup.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from deic_core import DEIC, cyber_generator, BeliefInspector, CommitController, MinimalPlanner, SelfModel


class CyberDEICAdapter:
    """
    Uses DEIC to diagnose a cyber incident by mapping:
      service  -> item
      monitor  -> source
      latency  -> value
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
        enable_upward_capacity_trigger=False,
        enable_final_contradiction_probe=True,
    ):
        self.adaptive_trust = adaptive_trust
        self.use_controller = use_controller
        self.use_planner = use_planner
        self.memory = memory
        self.confidence_threshold = confidence_threshold
        self.entropy_floor = entropy_floor
        self.coverage_threshold = coverage_threshold
        self.enable_adapt_refine = enable_adapt_refine
        self.enable_upward_capacity_trigger = enable_upward_capacity_trigger
        self.enable_final_contradiction_probe = enable_final_contradiction_probe

    @staticmethod
    def _is_better_fit(candidate, current_best):
        """Rank candidate replay results. Better = more active hyps, then higher margin."""
        if candidate['active_hypotheses'] > current_best['active_hypotheses']:
            return True
        if candidate['active_hypotheses'] == current_best['active_hypotheses']:
            return candidate['confidence_margin'] > current_best['confidence_margin']
        return False

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

        if self.use_planner:
            return self._diagnose_with_planner(env, engine, budget)
        elif self.use_controller:
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
                res = env.submit_diagnosis(proposed)
                res["final_workspace"] = inspector_state
                return res
            elif decision == CommitController.ACTION_ESCALATE:
                res = env.escalate_ambiguity()
                res["final_workspace"] = inspector_state
                return res
            
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
        monitors = env.get_monitors()

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
        post_adaptation_queries = 0
        post_adaptation_commit_turn = -1
        post_adaptation_escalation_turn = -1
        post_adaptation_wrong_commit = False
        post_adaptation_query_value_total = 0.0

        while True:
            remaining = budget - 1 - env.turn
            ws = inspector.workspace()
            # Inject adaptation telemetry into workspace
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
                res = env.submit_diagnosis(proposed)
                if engine.adaptation_count > 0:
                    post_adaptation_commit_turn = env.turn
                    post_adaptation_wrong_commit = not res.get("correct", False)
                    ws.post_adaptation_commit_turn = post_adaptation_commit_turn
                    ws.post_adaptation_wrong_commit = post_adaptation_wrong_commit
                # Final analytical telemetry pass
                self._enrich_telemetry(ws, res, env, engine)
                res["final_workspace"] = ws
                return res

            if mode == "ESCALATE":
                ws.family_search_outcome = family_search_outcome or "escalated"
                if engine.adaptation_count > 0:
                    post_adaptation_escalation_turn = env.turn
                    ws.post_adaptation_escalation_turn = post_adaptation_escalation_turn
                res = {"escalated": True, "abstained": True}
                self._enrich_telemetry(ws, res, env, engine)
                res["final_workspace"] = ws
                return res

            elif mode == "RESET_TRUST":
                engine.reset_trust()
                continue
            elif mode == "CONTRADICTION_PROBE":
                if contradiction_probe_trigger_turn < 0:
                    contradiction_probe_trigger_turn = env.turn
                contradiction_probe_count += 1
                untouched = [it for it in engine._items if it not in engine._queried_values]
                if untouched and engine._trusted_source is not None:
                    service = min(untouched, key=lambda it: (len(item_queries.get(it, set())), engine._items.index(it)))
                    monitor = engine._trusted_source
                else:
                    monitor, service = engine.select_query({'remaining_turns': remaining, 'queried_pairs': queried_pairs})

                pre_query_entropy = ws.entropy
                result = env.query(monitor, service)
                queried_pairs.add((monitor, service))
                item_queries[service].add(monitor)

                if "reported_latency" in result:
                    engine.update_observation(monitor, service, result["reported_latency"], env.turn)
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
                gen = engine._current_generator
                if gen is None or not hasattr(gen, 'adjacent_families'):
                    family_search_outcome = "exhausted"
                    continue

                candidates = gen.adjacent_families()
                if not candidates:
                    family_search_outcome = "exhausted"
                    continue

                # Save current state for rollback
                saved_hypotheses = [dict(h) for h in engine._hypotheses]
                saved_queried = dict(engine._queried_values)
                saved_generator = engine._current_generator
                saved_adaptation_count = engine.adaptation_count

                # Test each candidate, rank by structural fit
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
                        replay_result = engine.reinitialize_beliefs(HypothesisGenerator.from_spec(spec))
                        if replay_result['active_hypotheses'] > 0:
                            if best_result is None or self._is_better_fit(replay_result, best_result):
                                best_result, best_spec = replay_result, spec

                if best_spec is not None:
                    engine.reinitialize_beliefs(HypothesisGenerator.from_spec(best_spec))
                    engine.adaptation_count = saved_adaptation_count + 1
                    if self.enable_adapt_refine and engine._trusted_source is not None:
                        # The prior contradiction is now explained by the
                        # adapted family, so don't let the old Rule 0 spike
                        # force an immediate post-adaptation escalation.
                        engine._suspicion_scores[engine._trusted_source] = 0
                    family_search_outcome = "adopted"
                    adaptation_turn = env.turn
                    remaining_budget_at_adaptation = max(0, remaining)
                    adaptation_before_full_coverage = (
                        len(engine._queried_values) < len(engine._items)
                    )
                else:
                    engine._hypotheses, engine._queried_values, engine._current_generator = saved_hypotheses, saved_queried, saved_generator
                    engine.adaptation_count = saved_adaptation_count + 1
                    family_search_outcome = family_search_outcome or "rejected"
                continue

            elif mode in ("EXPLORE", "REFINE", "ADAPT_REFINE"):
                if engine.adaptation_count > 0:
                    post_adaptation_queries += 1

                monitor, service = None, None
                if mode == "EXPLORE" and engine._trusted_source is None:
                    # DIAGONAL PROBING
                    monitor = monitors[env.turn % len(monitors)]
                    unqueried = [it for it in engine._items if it not in engine._queried_values]
                    service = unqueried[0] if unqueried else engine._items[env.turn % len(engine._items)]
                    
                    if (monitor, service) in queried_pairs:
                        monitor, service = engine.select_query({'remaining_turns': remaining, 'queried_pairs': queried_pairs})
                else: 
                    monitor, service = engine.select_query({'remaining_turns': remaining, 'queried_pairs': queried_pairs})

                pre_query_entropy = ws.entropy
                result = env.query(monitor, service)
                queried_pairs.add((monitor, service))
                item_queries[service].add(monitor)

                if "reported_latency" in result:
                    engine.update_observation(monitor, service, result["reported_latency"], env.turn)
                    if engine._trusted_source is None and not self.adaptive_trust:
                        engine.update_trust()
                    if engine.adaptation_count > 0:
                        post_state = inspector.inspect(top_n=1)
                        post_adaptation_query_value_total += max(
                            0.0, pre_query_entropy - post_state["entropy"]
                        )

    def _enrich_telemetry(self, ws, res, env, engine):
        """Analytical-only ground-truth comparison for failure diagnosis."""
        affected = set(env.config.affected_group)
        # nodes queried by THE trusted source
        trusted = engine._trusted_source
        queried_by_trusted = set()
        if trusted:
            queried_by_trusted = {item for (item, val) in engine._source_observations.get(trusted, [])}
        
        missed = affected - queried_by_trusted
        ws.missed_anomalous_node = len(missed) > 0
        
        is_success = res.get("correct", False)
        is_escalated = res.get("escalated", False)
        
        # Blind-spot: Failure + missed node + no adaptation
        if not is_success and ws.missed_anomalous_node and ws.adaptation_count == 0:
            ws.coverage_blindspot_triggered = True
            ws.final_outcome_category = "BLIND_SPOT_FAILURE"
        elif is_success and ws.adaptation_count > 0:
            ws.final_outcome_category = "CORRECT_ADAPT_RECOVERY"
        elif not is_success and ws.adaptation_count > 0:
            if ws.family_search_outcome == "adopted":
                # Check if correct family adopted
                # (Assuming Fixed(gs=X) label format)
                true_gs = len(affected)
                adopted_label = ws.current_family_spec
                if f"gs={true_gs}" in adopted_label:
                    ws.final_outcome_category = "RECOVERY_FAILURE_POST_ADOPTION"
                else:
                    ws.final_outcome_category = "WRONG_FAMILY_ADOPTION"
            else:
                ws.final_outcome_category = "ADAPTATION_REJECTED"
        elif is_escalated:
            ws.final_outcome_category = "ESCALATED"
        elif not is_success:
            ws.final_outcome_category = "STABLE_WRONG_COMMIT"
        else:
            ws.final_outcome_category = "STABLE_CORRECT"
