"""
Benchmark Solvers: Baselines for belief revision under contradiction.

Each solver implements a solve(env) function that returns a trajectory log
compatible with the scoring harness.
"""
import random
from collections import defaultdict


def _trajectory_entry(action, agent_trust):
    return {"next_action": action, "confidence_scores": dict(agent_trust)}


# --------------------------------------------------------------------------
# Solver 1: Random Query
# --------------------------------------------------------------------------
class RandomSolver:
    """Queries agents at random, commits majority vote at the end."""
    def __init__(self, seed=0):
        self.rng = random.Random(seed)

    def solve(self, env):
        items = env.get_items()
        agents = env.get_agent_names()
        budget = env.config.max_turns - 1

        reports = defaultdict(lambda: defaultdict(list))
        trajectory = []
        trust = {a: 1.0 for a in agents}

        for _ in range(min(budget, len(items) * len(agents) * 2)):
            agent = self.rng.choice(agents)
            item = self.rng.choice(items)
            action = {"type": "query", "target_agent": agent, "item_id": item}
            trajectory.append(_trajectory_entry(action, trust))
            obs = env.step(action)
            if obs.get("status") == "budget_exhausted":
                break
            if "reported_quantity" in obs:
                reports[item][agent].append(obs["reported_quantity"])

        proposed = {}
        for item in items:
            values = []
            for agent in agents:
                if reports[item][agent]:
                    values.append(reports[item][agent][-1])
            proposed[item] = max(set(values), key=values.count) if values else 0

        commit_action = {"type": "commit_consensus", "proposed_inventory": proposed}
        trajectory.append(_trajectory_entry(commit_action, trust))
        result = env.step(commit_action)
        return trajectory, result


# --------------------------------------------------------------------------
# Solver 2: Round Robin
# --------------------------------------------------------------------------
class RoundRobinSolver:
    """Queries each agent about each item in order, commits majority vote."""
    def solve(self, env):
        items = env.get_items()
        agents = env.get_agent_names()
        reports = defaultdict(lambda: defaultdict(list))
        trajectory = []
        trust = {a: 1.0 for a in agents}

        for item in items:
            for agent in agents:
                action = {"type": "query", "target_agent": agent, "item_id": item}
                trajectory.append(_trajectory_entry(action, trust))
                obs = env.step(action)
                if obs.get("status") == "budget_exhausted":
                    break
                if "reported_quantity" in obs:
                    reports[item][agent].append(obs["reported_quantity"])

        proposed = {}
        for item in items:
            values = [reports[item][a][-1] for a in agents if reports[item][a]]
            proposed[item] = max(set(values), key=values.count) if values else 0

        commit_action = {"type": "commit_consensus", "proposed_inventory": proposed}
        trajectory.append(_trajectory_entry(commit_action, trust))
        result = env.step(commit_action)
        return trajectory, result


# --------------------------------------------------------------------------
# Solver 3: Flat Bayesian State Estimator (THE REAL BASELINE)
# --------------------------------------------------------------------------
class BayesianSolver:
    """
    Two-pass solver:
      Pass 1: Query every (agent, item) pair. Observe system alerts.
      Pass 2: After the rule shift, re-query all agents on any item that
              got a system alert. This guarantees we see the contradiction.
    
    Detection: When 2+ agents agree and 1 disagrees on a post-shift query,
    flag the disagreeing agent. Exclude it from the final commit.
    """
    def __init__(self, trust_lock=False):
        self.trust_lock = trust_lock

    def solve(self, env):
        items = env.get_items()
        agents = env.get_agent_names()
        n_agents = len(agents)

        fault_prior = {a: 1.0 / n_agents for a in agents}
        latest_report = {item: {} for item in items}
        alerted_items = set()  # items that got a system_alert
        trajectory = []
        detected_faulty = None

        # Pass 1: Initial sweep — query all agents on all items
        for item in items:
            for agent in agents:
                action = {"type": "query", "target_agent": agent, "item_id": item}
                trajectory.append(_trajectory_entry(action, fault_prior))
                obs = env.step(action)
                if obs.get("status") == "budget_exhausted":
                    break
                if "reported_quantity" in obs:
                    latest_report[item][agent] = obs["reported_quantity"]
                if "system_alert" in obs:
                    alert = obs["system_alert"]
                    if "item" in alert:
                        alerted_items.add(alert["item"])
                    elif "updated_item" in alert:
                        alerted_items.add(alert["updated_item"])

                # Check for contradictions after each query
                detected_faulty, fault_prior = self._update_beliefs(
                    items, agents, latest_report, fault_prior
                )

        # Pass 2: Re-query agents ONLY on items that received a system_alert.
        # The alert tells us the environment shifted; our earlier queries on
        # that item may be stale. Without an alert, there's no reason to requery.
        requery_items = set(alerted_items)

        for item in requery_items:
            for agent in agents:
                if detected_faulty and agent == detected_faulty:
                    continue
                action = {"type": "query", "target_agent": agent, "item_id": item}
                trajectory.append(_trajectory_entry(action, fault_prior))
                obs = env.step(action)
                if obs.get("status") == "budget_exhausted":
                    break
                if "reported_quantity" in obs:
                    latest_report[item][agent] = obs["reported_quantity"]

                detected_faulty, fault_prior = self._update_beliefs(
                    items, agents, latest_report, fault_prior
                )

        # Phase 3: Commit. Exclude suspected faulty agent.
        proposed = {}
        trusted = [a for a in agents if a != detected_faulty] if detected_faulty else agents

        for item in items:
            values = [latest_report[item][a] for a in trusted if a in latest_report[item]]
            if values:
                proposed[item] = max(set(values), key=values.count)
            else:
                all_vals = list(latest_report[item].values())
                proposed[item] = all_vals[0] if all_vals else 0

        commit_action = {"type": "commit_consensus", "proposed_inventory": proposed}
        trajectory.append(_trajectory_entry(commit_action, fault_prior))
        result = env.step(commit_action)
        return trajectory, result

    def _update_beliefs(self, items, agents, latest_report, fault_prior):
        fault_counts = {a: 0 for a in agents}
        checked = 0

        for item in items:
            reps = latest_report[item]
            if len(reps) < 2:
                continue
            checked += 1
            values = list(reps.values())
            majority_val = max(set(values), key=values.count)
            majority_count = values.count(majority_val)

            for agent, val in reps.items():
                if val != majority_val and majority_count >= 2:
                    fault_counts[agent] += 1

        if self.trust_lock:
            # Ablated mode: do not update prior, do not isolate anyone
            fault_prior = {a: 1.0 / len(agents) for a in agents}
            return None, fault_prior

        detected = None
        if checked > 0:
            for agent in agents:
                if fault_counts[agent] > 0:
                    fault_prior[agent] = min(0.99, fault_prior[agent] + 0.3 * fault_counts[agent])
                else:
                    fault_prior[agent] = max(0.01, fault_prior[agent] * 0.5)

            total = sum(fault_prior.values())
            fault_prior = {a: v / total for a, v in fault_prior.items()}

            max_agent = max(fault_prior, key=fault_prior.get)
            if fault_prior[max_agent] > 0.7:
                detected = max_agent

        return detected, fault_prior


# --------------------------------------------------------------------------
# Solver 4: Oracle (Diagnostic Ceiling)
# --------------------------------------------------------------------------
class OracleSolver:
    """Gets ground-truth access to the faulty agent identity after t_shift_1."""
    def solve(self, env):
        items = env.get_items()
        agents = env.get_agent_names()
        budget = env.config.max_turns - 1
        trajectory = []
        fault_prior = {a: 1.0 / len(agents) for a in agents}
        
        latest_report = {item: {} for item in items}
        
        turn_idx = 0
        for _ in range(min(budget, len(items) * len(agents))):
            # Oracle knows the faulty agent after t_shift_1
            if env.turn >= env.config.t_shift_1:
                known_fault = env.config.faulty_agent
                fault_prior = {a: 1.0 if a == known_fault else 0.0 for a in agents}
            
            # Query systematically among valid agents
            valid_agents = [a for a in agents if fault_prior.get(a, 0) < 1.0]
            if not valid_agents:
                valid_agents = agents
                
            # Sweep through items systematically to guarantee coverage
            agent = random.choice(valid_agents)
            item = items[turn_idx % len(items)]
            turn_idx += 1
            
            action = {"type": "query", "target_agent": agent, "item_id": item}
            trajectory.append(_trajectory_entry(action, fault_prior))
            obs = env.step(action)
            if obs.get("status") == "budget_exhausted":
                break
            if "reported_quantity" in obs:
                latest_report[item][agent] = obs["reported_quantity"]
                
        # Commit using only 0.0 fault prior agents
        proposed = {}
        trusted = [a for a in agents if fault_prior.get(a, 0) < 0.5] if any(fault_prior.get(a, 0) < 0.5 for a in agents) else agents
        
        for item in items:
            values = [latest_report[item][a] for a in trusted if a in latest_report[item]]
            proposed[item] = max(set(values), key=values.count) if values else 0

        commit_action = {"type": "commit_consensus", "proposed_inventory": proposed}
        trajectory.append(_trajectory_entry(commit_action, fault_prior))
        result = env.step(commit_action)
        return trajectory, result


# --------------------------------------------------------------------------
# Solver 5: Temporal Trust Updater
# --------------------------------------------------------------------------
class TemporalTrustSolver:
    """
    Maintains dynamic trust step-by-step. Weights incoming evidence by current trust,
    preventing a newly formed corrupted coalition from overriding a trusted node.
    """
    def solve(self, env):
        items = env.get_items()
        agents = env.get_agent_names()
        
        # We start with trust = {a: 1.0 / n_agents}. Note: lower is "more faulty" here,
        # but to match reporting convention we maintain fault_prob = 1 - trust.
        # Let's keep fault_prior (P_fault) as the metric.
        fault_prior = {a: 0.1 for a in agents} # Prior probability of fault
        
        latest_report = {item: {} for item in items}
        alerted_items = set()
        trajectory = []
        
        # Strategy: round-robin but update trust after every full sweep
        for sweep in range(2): # 2 passes to ensure we query post-shift
            for item in items:
                for agent in agents:
                    if fault_prior[agent] > 0.8:
                        continue # aggressively isolate known faulty
                        
                    action = {"type": "query", "target_agent": agent, "item_id": item}
                    trajectory.append(_trajectory_entry(action, fault_prior))
                    obs = env.step(action)
                    if obs.get("status") == "budget_exhausted":
                        break
                        
                    if "reported_quantity" in obs:
                        latest_report[item][agent] = obs["reported_quantity"]
                        
                    if "system_alert" in obs:
                        alert = obs["system_alert"]
                        if isinstance(alert, list):
                            for al in alert:
                                if "item" in al or "updated_item" in al:
                                    alerted_items.add(al.get("item", al.get("updated_item")))
                        else:
                            if "item" in alert or "updated_item" in alert:
                                alerted_items.add(alert.get("item", alert.get("updated_item")))
                            
                    # Explicit Temporal Update: does this new report contradict established trusted majority?
                    self._update_temporal_trust(item, agents, latest_report, fault_prior)

        # Final pass over alerted items just in case
        for item in alerted_items:
            for agent in agents:
                if fault_prior[agent] > 0.8: continue
                action = {"type": "query", "target_agent": agent, "item_id": item}
                trajectory.append(_trajectory_entry(action, fault_prior))
                obs = env.step(action)
                if obs.get("status") == "budget_exhausted": break
                if "reported_quantity" in obs:
                    latest_report[item][agent] = obs["reported_quantity"]
                self._update_temporal_trust(item, agents, latest_report, fault_prior)

        proposed = {}
        for item in items:
            # Weighted vote: weight = 1 - P_fault
            votes = defaultdict(float)
            for a, val in latest_report[item].items():
                votes[val] += max(0.01, 1.0 - fault_prior[a])
            
            if votes:
                proposed[item] = max(votes, key=votes.get)
            else:
                proposed[item] = 0

        commit_action = {"type": "commit_consensus", "proposed_inventory": proposed}
        trajectory.append(_trajectory_entry(commit_action, fault_prior))
        result = env.step(commit_action)
        return trajectory, result
        
    def _update_temporal_trust(self, item, agents, latest_report, fault_prior):
        reps = latest_report[item]
        if len(reps) < 2: return
        
        # Find the weighted majority value
        votes = defaultdict(float)
        for a, val in reps.items():
            votes[val] += max(0.01, 1.0 - fault_prior[a])
            
        winning_val = max(votes, key=votes.get)
        total_weight = sum(votes.values())
        
        if votes[winning_val] / total_weight > 0.6: # Clear consensus
            for a, val in reps.items():
                if val != winning_val:
                    fault_prior[a] = min(0.99, fault_prior[a] * 1.5) # exponentially increase suspicion
                else:
                    fault_prior[a] = max(0.01, fault_prior[a] * 0.8) # slowly regain trust


# --------------------------------------------------------------------------
# Solver 6: External-Ledger Tracker (Hard & Soft)
# --------------------------------------------------------------------------
class ExternalLedgerSolver:
    """
    Maintains a temporal history of queries to perform anomaly detection.
    If hard_flag=True, any discontinuous jump permanently zero-trusts the agent.
    If hard_flag=False, applies a decaying soft-suspicion penalty.
    """
    def __init__(self, hard_flag=False):
        self.hard_flag = hard_flag

    def solve(self, env):
        items = env.get_items()
        agents = env.get_agent_names()
        
        fault_prior = {a: 0.1 for a in agents}
        
        # History: agent -> item -> list of (turn, value)
        ledger = {a: {item: [] for item in items} for a in agents}
        latest_alerts = []
        
        trajectory = []
        
        # Sweep strategy
        sweep_plan = [(a, i) for i in items for a in agents] * 3
        
        for agent, item in sweep_plan:
            # If hard flagged, don't query (save budget)
            if self.hard_flag and fault_prior[agent] > 0.9:
                continue
                
            action = {"type": "query", "target_agent": agent, "item_id": item}
            trajectory.append(_trajectory_entry(action, fault_prior))
            obs = env.step(action)
            if obs.get("status") == "budget_exhausted":
                break
                
            if "system_alert" in obs:
                alert = obs["system_alert"]
                if isinstance(alert, list): latest_alerts.extend(alert)
                else: latest_alerts.append(alert)
                
            if "reported_quantity" in obs:
                val = obs["reported_quantity"]
                turn = env.turn
                
                # Anomaly detection logic
                history = ledger[agent][item]
                if history:
                    last_turn, last_val = history[-1]
                    # If value changed but no system update on this item occurred between last_turn and now
                    if val != last_val:
                        # Did an alert happen for this item?
                        alert_occurred = any(al.get("item", al.get("updated_item")) == item or al.get("category") for al in latest_alerts)
                        if not alert_occurred:
                            # Anomaly detected: spontaneous value shift
                            if self.hard_flag:
                                fault_prior[agent] = 0.99
                            else:
                                fault_prior[agent] = min(0.95, fault_prior[agent] + 0.5)
                
                ledger[agent][item].append((turn, val))
                
            # Cross-agent consensus check
            self._cross_check(item, agents, ledger, fault_prior)

        proposed = {}
        for item in items:
            votes = defaultdict(float)
            for a in agents:
                hist = ledger[a][item]
                if hist:
                    val = hist[-1][1]
                    votes[val] += max(0.01, 1.0 - fault_prior[a])
            if votes:
                proposed[item] = max(votes, key=votes.get)
            else:
                proposed[item] = 0

        commit_action = {"type": "commit_consensus", "proposed_inventory": proposed}
        trajectory.append(_trajectory_entry(commit_action, fault_prior))
        result = env.step(commit_action)
        return trajectory, result
        
    def _cross_check(self, item, agents, ledger, fault_prior):
        current_vals = {}
        for a in agents:
            if ledger[a][item]:
                current_vals[a] = ledger[a][item][-1][1]
                
        if len(current_vals) < 2: return
        
        votes = defaultdict(float)
        for a, val in current_vals.items():
            votes[val] += max(0.01, 1.0 - fault_prior[a])
            
        winning_val = max(votes, key=votes.get)
        total_weight = sum(votes.values())
        
        if votes[winning_val] / total_weight > 0.5:
            for a, val in current_vals.items():
                if val != winning_val:
                    if self.hard_flag:
                        fault_prior[a] = min(0.99, fault_prior[a] + 0.1)
                    else:
                        fault_prior[a] = min(0.95, fault_prior[a] + 0.2)
                else:
                    if not self.hard_flag:
                        fault_prior[a] = max(0.01, fault_prior[a] * 0.9)


# --------------------------------------------------------------------------
# Solver 7: Category Extrapolator (Factorized Latent)
# --------------------------------------------------------------------------
class CategoryExtrapolatorSolver:
    """
    Non-hierarchical structural baseline.
    Possesses static categorical knowledge and extrapolates learned multipliers.
    Queries 1 item per category deeply, then broadcasts to all items in that category.
    Tests if flat structural priors solve C5 without full hierarchical active inference.
    """
    def solve(self, env):
        try:
            initial_state = env.get_initial_state()
            items_list = list(initial_state.keys())
            # The static extrapolator assumes the fixed original mapping, regardless of C6 scrambling
            categories = {"Cat_1": items_list[:4], "Cat_2": items_list[4:]}
        except AttributeError:
            # Fallback for non-C5/C6
            return RoundRobinSolver().solve(env)

        agents = env.get_agent_names()
        trajectory = []
        fault_prior = {a: 0.1 for a in agents}
        
        # Pick one representative item from each category
        rep_items = {}
        for cat, items in categories.items():
            if items: rep_items[cat] = items[0]
            
        latest_report = {item: {} for item in rep_items.values()}
        
        # We have max 6 turns. 2 categories * 3 agents = 6 queries.
        # This completely exhausts the budget but gives us full majority context for 1 item per cat.
        for cat, rep_item in rep_items.items():
            for agent in agents:
                action = {"type": "query", "target_agent": agent, "item_id": rep_item}
                trajectory.append(_trajectory_entry(action, fault_prior))
                obs = env.step(action)
                if obs.get("status") == "budget_exhausted": break
                if "reported_quantity" in obs:
                    latest_report[rep_item][agent] = obs["reported_quantity"]
                    
        # Extrapolate
        proposed = {}
        for cat, items in categories.items():
            multiplier = 1.0
            rep_item = rep_items.get(cat)
            
            if rep_item and latest_report[rep_item]:
                reps = list(latest_report[rep_item].values())
                # Find majority reported value to dodge faulty agent
                majority_val = max(set(reps), key=reps.count) if reps else initial_state[rep_item]
                
                # Infer multiplier
                inferred_ratio = majority_val / initial_state[rep_item]
                # Snap to known possible multipliers or 1.0 to avoid noise
                possible_mults = [1.0, 1.2, 1.5, 2.0, 2.5]
                closest = min(possible_mults, key=lambda x: abs(x - inferred_ratio))
                
                # If the ratio is very close to a possible multiplier, accept it
                if abs(closest - inferred_ratio) < 0.1:
                    multiplier = closest
                    
            for item in items:
                proposed[item] = int(initial_state[item] * multiplier)
                
        commit_action = {"type": "commit_consensus", "proposed_inventory": proposed}
        trajectory.append(_trajectory_entry(commit_action, fault_prior))
        result = env.step(commit_action)
        return trajectory, result

# --------------------------------------------------------------------------
# Solver 8: Flat Structure Learner
# --------------------------------------------------------------------------
class FlatStructureLearnerSolver:
    """
    Attempts to infer item clusters from observed co-movement without knowing categories.
    Allocates budget to finding an honest agent, then querying remaining unqueried items.
    Groups items by observed multiplier. Unqueried items default to multiplier 1.0. 
    """
    def solve(self, env):
        try:
            initial_state = env.get_initial_state()
        except AttributeError:
            return RoundRobinSolver().solve(env)

        agents = env.get_agent_names()
        items = list(initial_state.keys())
        trajectory = []
        fault_prior = {a: 0.1 for a in agents}
        
        budget = env.config.max_turns
        
        # Step 1: Query all 3 agents for Item 0 to establish truth and find honest agent
        latest_report = {}
        for agent in agents:
            action = {"type": "query", "target_agent": agent, "item_id": items[0]}
            trajectory.append(_trajectory_entry(action, fault_prior))
            obs = env.step(action)
            if obs.get("status") == "budget_exhausted": break
            if "reported_quantity" in obs:
                latest_report[agent] = obs["reported_quantity"]
                
        # Find majority to dodge faulty agent
        reps = list(latest_report.values())
        majority_val = max(set(reps), key=reps.count) if reps else initial_state[items[0]]
        honest_agent = agents[0]
        for a, val in latest_report.items():
            if val == majority_val:
                honest_agent = a
                break
                
        # Step 2: Query the honest agent for as many remaining items as budget allows
        queried_vals = {items[0]: majority_val}
        idx = 1
        # Reserve 1 turn for commit
        while env.turn < budget - 1 and idx < len(items):
            action = {"type": "query", "target_agent": honest_agent, "item_id": items[idx]}
            trajectory.append(_trajectory_entry(action, fault_prior))
            obs = env.step(action)
            if obs.get("status") == "budget_exhausted": break
            if "reported_quantity" in obs:
                queried_vals[items[idx]] = obs["reported_quantity"]
            idx += 1
            
        # Step 3: Infer multiplier for queried items
        ratios = {}
        for it, val in queried_vals.items():
            ratio = val / initial_state[it]
            possible_mults = [1.0, 1.2, 1.5, 2.0, 2.5]
            closest = min(possible_mults, key=lambda x: abs(x - ratio))
            if abs(closest - ratio) < 0.1:
                ratios[it] = closest
            else:
                ratios[it] = 1.0
                
        # Step 4: Propose inventory, guessing 1.0 for unqueried items based on flat structure
        proposed = {}
        for it in items:
            if it in ratios:
                proposed[it] = int(initial_state[it] * ratios[it])
            else:
                proposed[it] = int(initial_state[it] * 1.0)
                
        commit_action = {"type": "commit_consensus", "proposed_inventory": proposed}
        trajectory.append(_trajectory_entry(commit_action, fault_prior))
        result = env.step(commit_action)
        return trajectory, result

# --------------------------------------------------------------------------
# Solver 9: Discrete Hypothesis Solver (Combinatorial State Tracker)
# --------------------------------------------------------------------------
class DiscreteHypothesisSolver:
    """
    Explicitly reasons over all permutations of latent categories and multipliers.
    A discrete inference bridge matching combinatorial hidden structures.
    """
    def solve(self, env):
        try:
            initial_state = env.get_initial_state()
        except AttributeError:
            return RoundRobinSolver().solve(env)

        agents = env.get_agent_names()
        items = list(initial_state.keys())
        trajectory = []
        fault_prior = {a: 0.1 for a in agents}
        
        budget = env.config.max_turns
        
        # Step 1: Majority check on first item to find an honest agent
        latest_report = {}
        for agent in agents:
            action = {"type": "query", "target_agent": agent, "item_id": items[0]}
            trajectory.append(_trajectory_entry(action, fault_prior))
            obs = env.step(action)
            if obs.get("status") == "budget_exhausted": break
            if "reported_quantity" in obs:
                latest_report[agent] = obs["reported_quantity"]
                
        reps = list(latest_report.values())
        majority_val = max(set(reps), key=reps.count) if reps else initial_state[items[0]]
        honest_agent = agents[0]
        for a, val in latest_report.items():
            if val == majority_val:
                honest_agent = a
                break
                
        # Step 2: Exhaust remaining budget to gather ground truth samples
        queried_vals = {items[0]: majority_val}
        idx = 1
        while env.turn < budget - 1 and idx < len(items):
            action = {"type": "query", "target_agent": honest_agent, "item_id": items[idx]}
            trajectory.append(_trajectory_entry(action, fault_prior))
            obs = env.step(action)
            if obs.get("status") == "budget_exhausted": break
            if "reported_quantity" in obs:
                queried_vals[items[idx]] = obs["reported_quantity"]
            idx += 1
            
        # Step 3: Hypothesis Scoring (Discrete Posterior Update)
        import itertools
        import random
        
        valid_multipliers = [1.2, 1.5, 2.0, 2.5]
        all_combos = list(itertools.combinations(items, 4)) # Assumes 4/4 split known
        
        best_hypothesis = None
        best_score = -float('inf')
        
        for shifted_group in all_combos:
            shifted_set = set(shifted_group)
            for mult in valid_multipliers:
                score = 0.0
                possible = True
                
                # Check consistency against observed sparse variables
                for it, val in queried_vals.items():
                    expected_val = int(initial_state[it] * mult) if it in shifted_set else initial_state[it]
                    if val == expected_val:
                        score += 1.0
                    else:
                        possible = False
                        break
                
                if possible:
                    # Break ties randomly among equally valid hypotheses
                    score += random.uniform(0, 0.01)
                    if score > best_score:
                        best_score = score
                        best_hypothesis = (shifted_set, mult)
                        
        # Step 4: Propose MAP hypothesis
        proposed = {}
        for it in items:
            if best_hypothesis:
                shifted_set, mult = best_hypothesis
                if it in shifted_set:
                    proposed[it] = int(initial_state[it] * mult)
                else:
                    proposed[it] = initial_state[it]
            else:
                proposed[it] = initial_state[it]
                
        commit_action = {"type": "commit_consensus", "proposed_inventory": proposed}
        trajectory.append(_trajectory_entry(commit_action, fault_prior))
        result = env.step(commit_action)
        return trajectory, result

# --------------------------------------------------------------------------
# Solver 10: Discrete Structure Agent v1 (Active Information Gain)
# --------------------------------------------------------------------------
class DiscreteStructureAgentV1:
    """
    Maintains a discrete hypothesis bank and actively selects the next query
    by maximizing expected information gain (minimizing posterior entropy).
    """
    def solve(self, env):
        try:
            initial_state = env.get_initial_state()
        except AttributeError:
            return RoundRobinSolver().solve(env)

        agents = env.get_agent_names()
        items = list(initial_state.keys())
        trajectory = []
        fault_prior = {a: 0.1 for a in agents}
        budget = env.config.max_turns
        
        # Step 1: Find an honest agent securely
        latest_report = {}
        for agent in agents:
            action = {"type": "query", "target_agent": agent, "item_id": items[0]}
            trajectory.append(_trajectory_entry(action, fault_prior))
            obs = env.step(action)
            if obs.get("status") == "budget_exhausted": break
            if "reported_quantity" in obs:
                latest_report[agent] = obs["reported_quantity"]
                
        reps = list(latest_report.values())
        majority_val = max(set(reps), key=reps.count) if reps else initial_state[items[0]]
        honest_agent = agents[0]
        for a, val in latest_report.items():
            if val == majority_val:
                honest_agent = a
                break
                
        queried_vals = {items[0]: majority_val}
        
        # Step 2: Build hypothesis bank
        import itertools
        import math
        
        valid_multipliers = [1.2, 1.5, 2.0, 2.5]
        all_combos = list(itertools.combinations(items, 4))
        
        # H is a list of dicts: {'S': set(items), 'm': mult, 'prob': 1.0/280}
        hypotheses = []
        for S in all_combos:
            for m in valid_multipliers:
                hypotheses.append({'S': set(S), 'm': m, 'prob': 1.0})
                
        def update_posterior(hyps, observations):
            for h in hyps:
                possible = True
                for it, val in observations.items():
                    exp = int(initial_state[it] * h['m']) if it in h['S'] else initial_state[it]
                    if val != exp:
                        possible = False
                        break
                h['prob'] = 1.0 if possible else 0.0
            total = sum(h['prob'] for h in hyps)
            if total > 0:
                for h in hyps: h['prob'] /= total
            return total > 0

        update_posterior(hypotheses, queried_vals)
        
        # Step 3: Active Query Phase via Expected Information Gain
        while env.turn < budget - 1:
            unqueried = [it for it in items if it not in queried_vals]
            if not unqueried: break
            
            # Filter to active hypotheses
            active_h = [h for h in hypotheses if h['prob'] > 0]
            if len(active_h) <= 1:
                # Fully resolved, no need to query more
                break
                
            best_item = unqueried[0]
            min_expected_entropy = float('inf')
            
            for test_item in unqueried:
                # Group active hypotheses by what they predict for test_item
                predictions = {}
                for h in active_h:
                    exp = int(initial_state[test_item] * h['m']) if test_item in h['S'] else initial_state[test_item]
                    if exp not in predictions:
                        predictions[exp] = []
                    predictions[exp].append(h)
                
                expected_entropy = 0.0
                for exp_val, matching_h in predictions.items():
                    p_val = sum(h['prob'] for h in matching_h)
                    # Entropy if this value is observed
                    ent = 0.0
                    if p_val > 0:
                        for h in matching_h:
                            p_h_given_val = h['prob'] / p_val
                            if p_h_given_val > 0:
                                ent -= p_h_given_val * math.log2(p_h_given_val)
                    expected_entropy += p_val * ent
                    
                if expected_entropy < min_expected_entropy:
                    min_expected_entropy = expected_entropy
                    best_item = test_item
                    
            # Query the item that minimizes expected posterior entropy
            action = {"type": "query", "target_agent": honest_agent, "item_id": best_item}
            trajectory.append(_trajectory_entry(action, fault_prior))
            obs = env.step(action)
            if obs.get("status") == "budget_exhausted": break
            if "reported_quantity" in obs:
                queried_vals[best_item] = obs["reported_quantity"]
                update_posterior(hypotheses, queried_vals)
                
        # Step 4: MAP Proposal
        active_h = [h for h in hypotheses if h['prob'] > 0]
        if active_h:
            # Pick MAP randomly among ties to preserve uniformity
            import random
            best_h = random.choice(active_h)
            shifted_set, mult = best_h['S'], best_h['m']
        else:
            shifted_set, mult = set(), 1.0
            
        proposed = {}
        for it in items:
            proposed[it] = int(initial_state[it] * mult) if it in shifted_set else initial_state[it]
            
        commit_action = {"type": "commit_consensus", "proposed_inventory": proposed}
        trajectory.append(_trajectory_entry(commit_action, fault_prior))
        result = env.step(commit_action)
        return trajectory, result

# --------------------------------------------------------------------------
# Solver 12: Discrete Structure Agent v3 (Joint Posterior InfoGain)
# --------------------------------------------------------------------------
class DiscreteStructureAgentV3:
    """
    Maintains a joint hypothesis space over both structural groupings and faulty
    agent assignment. Uses active Information Gain over the full joint space to
    seamlessly interleave trust and structure discrimination.
    """
    def __init__(self, use_improved_policy=True):
        self.use_improved_policy = use_improved_policy

    def solve(self, env):
        try:
            initial_state = env.get_initial_state()
        except AttributeError:
            return RoundRobinSolver().solve(env)

        agents = env.get_agent_names()
        items = list(initial_state.keys())
        trajectory = []
        fault_prior = {a: 0.1 for a in agents}
        budget = env.config.max_turns
        
        import itertools
        import math
        import random
        
        valid_multipliers = [1.2, 1.5, 2.0, 2.5]
        all_combos = list(itertools.combinations(items, 4))
        
        # Joint hypotheses: (T, S, m) where T is faulty agent, S is shifted set
        hypotheses = []
        for T in agents:
            for S in all_combos:
                for m in valid_multipliers:
                    hypotheses.append({'T': T, 'S': set(S), 'm': m, 'prob': 1.0})
                    
        def normalize(hyps):
            total = sum(h['prob'] for h in hyps)
            if total > 0:
                for h in hyps: h['prob'] /= total
            return total
            
        normalize(hypotheses)
        
        queried_pairs = set()
        
        while env.turn < budget - 1:
            active_h = [h for h in hypotheses if h['prob'] > 0]
            if len(active_h) <= 1: break
            
            # Check if structural part (S, m) is fully resolved
            unique_structures = set( (tuple(sorted(list(h['S']))), h['m']) for h in active_h )
            if len(unique_structures) == 1:
                break # We don't care about identifying T if structure is known
                
            best_action_pair = None
            available_actions = [(a, i) for a in agents for i in items if (a, i) not in queried_pairs]
            
            if not self.use_improved_policy:
                # Ablation: Random pair sampling (no InfoGain active policy)
                best_action_pair = random.choice(available_actions)
            else:
                min_expected_entropy = float('inf')
                random.shuffle(available_actions)
                
                for test_a, test_i in available_actions:
                    predictions = {}
                    for h in active_h:
                        if test_a == h['T']:
                            exp_val = initial_state[test_i]
                        else:
                            exp_val = int(initial_state[test_i] * h['m']) if test_i in h['S'] else initial_state[test_i]
                            
                        if exp_val not in predictions:
                            predictions[exp_val] = []
                        predictions[exp_val].append(h)
                        
                    expected_entropy = 0.0
                    for exp_val, matching_h in predictions.items():
                        p_val = sum(h['prob'] for h in matching_h)
                        ent = 0.0
                        if p_val > 0:
                            for h in matching_h:
                                p_h_given_val = h['prob'] / p_val
                                if p_h_given_val > 0:
                                    ent -= p_h_given_val * math.log2(p_h_given_val)
                        expected_entropy += p_val * ent
                        
                    if expected_entropy < min_expected_entropy:
                        min_expected_entropy = expected_entropy
                        best_action_pair = (test_a, test_i)
                        
            target_agent, target_item = best_action_pair
            action = {"type": "query", "target_agent": target_agent, "item_id": target_item}
            trajectory.append(_trajectory_entry(action, fault_prior))
            obs = env.step(action)
            queried_pairs.add(best_action_pair)
            
            if obs.get("status") == "budget_exhausted": break
            if "reported_quantity" in obs:
                val = obs["reported_quantity"]
                for h in hypotheses:
                    if h['prob'] == 0: continue
                    if target_agent == h['T']:
                        expected = initial_state[target_item]
                    else:
                        expected = int(initial_state[target_item] * h['m']) if target_item in h['S'] else initial_state[target_item]
                    if val != expected:
                        h['prob'] = 0.0
                normalize(hypotheses)
                
        # Propose MAP
        active_h = [h for h in hypotheses if h['prob'] > 0]
        if active_h:
            h_scores = {}
            for h in active_h:
                struct_key = (tuple(sorted(list(h['S']))), h['m'])
                if struct_key not in h_scores: h_scores[struct_key] = 0.0
                h_scores[struct_key] += h['prob']
                
            best_struct = max(h_scores.items(), key=lambda x: x[1])[0]
            shifted_set, mult = set(best_struct[0]), best_struct[1]
        else:
            shifted_set, mult = set(), 1.0
            
        proposed = {}
        for it in items:
            proposed[it] = int(initial_state[it] * mult) if it in shifted_set else initial_state[it]
            
        commit_action = {"type": "commit_consensus", "proposed_inventory": proposed}
        trajectory.append(_trajectory_entry(commit_action, fault_prior))
        result = env.step(commit_action)
        return trajectory, result

# --------------------------------------------------------------------------
# Solver 11: Discrete Structure Agent v2 (Adaptive Trust)
# --------------------------------------------------------------------------
class DiscreteStructureAgentV2:
    """
    Combines explicit posterior scoring with an adaptive trust policy that
    leverages the known structural constraints to skip full consensus checks.
    """
    def __init__(self, adaptive_trust=True):
        self.adaptive_trust = adaptive_trust
        
    def solve(self, env):
        try:
            initial_state = env.get_initial_state()
        except AttributeError:
            return RoundRobinSolver().solve(env)

        agents = env.get_agent_names()
        items = list(initial_state.keys())
        trajectory = []
        fault_prior = {a: 0.1 for a in agents}
        budget = env.config.max_turns
        
        queried_vals = {}
        honest_agent = None
        
        # Step 1: Adaptive Trust Discovery
        while env.turn < budget - 1 and honest_agent is None:
            unqueried = [it for it in items if it not in queried_vals]
            if not unqueried: break
            
            test_item = unqueried[0]
            vals_for_item = []
            
            for a in agents:
                if env.turn >= budget - 1: break
                
                action = {"type": "query", "target_agent": a, "item_id": test_item}
                trajectory.append(_trajectory_entry(action, fault_prior))
                obs = env.step(action)
                
                if "reported_quantity" in obs:
                    val = obs["reported_quantity"]
                    
                    if self.adaptive_trust:
                        # In C6, the faulty agent returns unshifted/stale values.
                        # IF we observe a multiplier, this agent MUST be honest!
                        if val != initial_state[test_item]:
                            honest_agent = a
                            queried_vals[test_item] = val
                            break
                        else:
                            vals_for_item.append(val)
                    else:
                        vals_for_item.append(val)
            
            if test_item not in queried_vals and vals_for_item:
                majority_val = max(set(vals_for_item), key=vals_for_item.count)
                queried_vals[test_item] = majority_val
                
                # If non-adaptive, lock the first agent matching majority
                if not self.adaptive_trust and len(vals_for_item) == len(agents):
                    for a_idx, v in enumerate(vals_for_item):
                        if v == majority_val:
                            honest_agent = agents[a_idx]
                            break

        # Step 2: Build hypothesis bank & Posterior update logic
        import itertools
        import math
        
        valid_multipliers = [1.2, 1.5, 2.0, 2.5]
        all_combos = list(itertools.combinations(items, 4))
        
        hypotheses = []
        for S in all_combos:
            for m in valid_multipliers:
                hypotheses.append({'S': set(S), 'm': m, 'prob': 1.0})
                
        def update_posterior(hyps, observations):
            for h in hyps:
                possible = True
                for it, val in observations.items():
                    exp = int(initial_state[it] * h['m']) if it in h['S'] else initial_state[it]
                    if val != exp:
                        possible = False
                        break
                h['prob'] = 1.0 if possible else 0.0
            total = sum(h['prob'] for h in hyps)
            if total > 0:
                for h in hyps: h['prob'] /= total
            return total > 0

        update_posterior(hypotheses, queried_vals)
        
        # Step 3: Active Query Phase via Expected Information Gain
        while env.turn < budget - 1 and honest_agent is not None:
            unqueried = [it for it in items if it not in queried_vals]
            if not unqueried: break
            
            active_h = [h for h in hypotheses if h['prob'] > 0]
            if len(active_h) <= 1: break
                
            best_item = unqueried[0]
            min_expected_entropy = float('inf')
            
            for test_item in unqueried:
                predictions = {}
                for h in active_h:
                    exp = int(initial_state[test_item] * h['m']) if test_item in h['S'] else initial_state[test_item]
                    if exp not in predictions: predictions[exp] = []
                    predictions[exp].append(h)
                
                expected_entropy = 0.0
                for exp_val, matching_h in predictions.items():
                    p_val = sum(h['prob'] for h in matching_h)
                    ent = 0.0
                    if p_val > 0:
                        for h in matching_h:
                            p_h_given_val = h['prob'] / p_val
                            if p_h_given_val > 0:
                                ent -= p_h_given_val * math.log2(p_h_given_val)
                    expected_entropy += p_val * ent
                    
                if expected_entropy < min_expected_entropy:
                    min_expected_entropy = expected_entropy
                    best_item = test_item
                    
            action = {"type": "query", "target_agent": honest_agent, "item_id": best_item}
            trajectory.append(_trajectory_entry(action, fault_prior))
            obs = env.step(action)
            if obs.get("status") == "budget_exhausted": break
            if "reported_quantity" in obs:
                queried_vals[best_item] = obs["reported_quantity"]
                update_posterior(hypotheses, queried_vals)
                
        # Step 4: MAP Proposal
        active_h = [h for h in hypotheses if h['prob'] > 0]
        if active_h:
            import random
            best_h = random.choice(active_h)
            shifted_set, mult = best_h['S'], best_h['m']
        else:
            shifted_set, mult = set(), 1.0
            
        proposed = {}
        for it in items:
            proposed[it] = int(initial_state[it] * mult) if it in shifted_set else initial_state[it]
            
        commit_action = {"type": "commit_consensus", "proposed_inventory": proposed}
        trajectory.append(_trajectory_entry(commit_action, fault_prior))
        result = env.step(commit_action)
        return trajectory, result
