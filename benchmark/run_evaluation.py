"""
Benchmark Evaluation Harness.

Runs N procedurally generated episodes across multiple solvers.
Reports median, mean, and 95% Confidence Intervals (Wilson for rates).
Produces a markdown-compatible cross-condition table.
"""
import sys
import os
import math
import random
from collections import defaultdict

sys.path.insert(0, os.path.dirname(__file__))
from environment import EpisodeConfig, ProceduralEnvironment, generate_episodes
from solvers import (
    RandomSolver, RoundRobinSolver, BayesianSolver,
    TemporalTrustSolver, ExternalLedgerSolver, OracleSolver
)


def wilson_score_interval(p_hat, n, z=1.96):
    """Calculates the 95% Wilson Score Interval for a binomial proportion."""
    if n == 0:
        return 0, 0
    denominator = 1 + z**2 / n
    center = (p_hat + z**2 / (2 * n)) / denominator
    spread = z * math.sqrt((p_hat * (1 - p_hat) / n) + (z**2 / (4 * n**2))) / denominator
    return center - spread, center + spread


def score_trajectory(trajectory, result, config):
    faulty_agent = config.faulty_agent
    t_fault = config.t_shift_1

    accuracy = 1.0 if result.get("consensus_reached", False) else 0.0

    escape_rate = 0.0
    if config.condition == "active_deception":
        diff = result.get("true_state_diff", {})
        if config.shifted_item_2 not in diff:
            escape_rate = 1.0

    detection_turn = None
    for i, entry in enumerate(trajectory):
        scores = entry.get("confidence_scores", {})
        # Depending on convention, we look for fault_prior > 0.8 or trust < 0.2
        # Some solvers output trust, some fault_prior. The base ones output fault_prior... 
        # Actually random, RR output trust=1. Bayesian outputs fault_prior (which goes >0.8).
        # Wait, if Bayesian outputs fault_prior, higher means faulty. We previously checked < 0.2.
        # Let's check the trajectory. In Bayesian solver: fault_prior[agent] > 0.8 -> isolated.
        val = scores.get(faulty_agent, 0.5)
        if val > 0.8:  # if metric is fault probability
            detection_turn = i
            break
        elif val < 0.2: # if metric is trust
            detection_turn = i
            break

    if detection_turn is not None:
        latency = max(0, detection_turn - t_fault)
    else:
        latency = float('inf')

    perseveration = 0
    if detection_turn is not None:
        for entry in trajectory[detection_turn + 1:]:
            act = entry.get("next_action", {})
            if act.get("type") == "query" and act.get("target_agent") == faulty_agent:
                perseveration += 1

    budget_used = len(trajectory)
    budget_max = config.max_turns
    efficiency = budget_used / budget_max if budget_max > 0 else 1.0

    belief_revision = 0.0
    if len(trajectory) > 1:
        prev_scores = trajectory[0].get("confidence_scores", {})
        for entry in trajectory[1:]:
            curr_scores = entry.get("confidence_scores", {})
            l1_dist = sum(abs(curr_scores.get(a, 0) - prev_scores.get(a, 0)) for a in curr_scores)
            belief_revision += l1_dist
            prev_scores = curr_scores

    return {
        "accuracy": accuracy,
        "escape_rate": escape_rate,
        "detection_latency": latency,
        "perseveration": perseveration,
        "belief_revision_rate": belief_revision,
        "budget_efficiency": efficiency,
        "budget_used": budget_used,
    }

def run_evaluation(solver, episodes):
    all_metrics = defaultdict(list)
    for ep_config in episodes:
        env = ProceduralEnvironment(ep_config)
        trajectory, result = solver.solve(env)
        metrics = score_trajectory(trajectory, result, ep_config)
        for k, v in metrics.items():
            all_metrics[k].append(v)
    return all_metrics

def format_metric(key, values, is_c4):
    if key == "escape_rate" and not is_c4:
        return "N/A"
        
    finite_vals = [v for v in values if v != float('inf')]
    n = len(values)
    
    if key in ["accuracy", "escape_rate"]:
        p_hat = sum(values) / n if n > 0 else 0
        ci_lower, ci_upper = wilson_score_interval(p_hat, n)
        return f"{p_hat*100:.1f}% [{ci_lower*100:.1f}-{ci_upper*100:.1f}]"
        
    if not finite_vals:
        return "inf (100%)"
        
    mean = sum(finite_vals) / len(finite_vals)
    finite_vals.sort()
    mid = len(finite_vals) // 2
    median = (finite_vals[mid] + finite_vals[~mid]) / 2.0
    
    if key in ["detection_latency", "belief_revision_rate"]:
        # Standard error for continuous
        variance = sum((x - mean)**2 for x in finite_vals) / max(len(finite_vals)-1, 1)
        stderr = math.sqrt(variance) / math.sqrt(len(finite_vals))
        ci_half = 1.96 * stderr
        inf_pct = (n - len(finite_vals)) / n * 100
        inf_str = f" (inf:{inf_pct:.0f}%)" if inf_pct > 0 else ""
        return f"Mean={mean:.1f} Med={median:.1f} ±{ci_half:.1f}{inf_str}"
        
    return f"{mean:.2f}"

def main():
    N = 500
    print(f"Generating N={N} episodes per condition...")
    episodes_c1 = generate_episodes(N, condition="cooperative", seed_offset=10000)
    episodes_c2 = generate_episodes(N, condition="obvious_noise", seed_offset=20000)
    episodes_c3 = generate_episodes(N, condition="stale_state", seed_offset=30000)
    episodes_c4 = generate_episodes(N, condition="active_deception", seed_offset=40000)

    solvers = {
        "Random": RandomSolver(seed=99),
        "Round-Robin": RoundRobinSolver(),
        "Bayesian (Full)": BayesianSolver(trust_lock=False),
        "Bayesian (Ablated)": BayesianSolver(trust_lock=True),
        "Temporal Trust": TemporalTrustSolver(),
        "Ledger (Soft)": ExternalLedgerSolver(hard_flag=False),
        "Ledger (Hard)": ExternalLedgerSolver(hard_flag=True),
        "Oracle": OracleSolver()
    }

    conditions = [
        ("C1", episodes_c1, False),
        ("C2", episodes_c2, False),
        ("C3", episodes_c3, False),
        ("C4", episodes_c4, True)
    ]

    # Generate Markdown Table
    print("\n# Benchmark Comprehensive Results (N=500 per condition)")
    
    headers = ["Solver", "Cond", "Accuracy (95% CI)", "Escape Rate", "Latency (Mean, Med)", "Belief Rev"]
    print("| " + " | ".join(headers) + " |")
    print("|---" * len(headers) + "|")

    for condition_name, eps, is_c4 in conditions:
        for solver_name, solver in solvers.items():
            metrics = run_evaluation(solver, eps)
            acc_str = format_metric("accuracy", metrics["accuracy"], is_c4)
            esc_str = format_metric("escape_rate", metrics["escape_rate"], is_c4)
            lat_str = format_metric("detection_latency", metrics["detection_latency"], is_c4)
            rev_str = format_metric("belief_revision_rate", metrics["belief_revision_rate"], is_c4)
            
            row = f"| {solver_name} | {condition_name} | {acc_str} | {esc_str} | {lat_str} | {rev_str} |"
            print(row)

if __name__ == "__main__":
    main()
