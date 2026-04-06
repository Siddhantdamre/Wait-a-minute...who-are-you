"""
Lean C5 Pilot evaluating Latent Coupling.
Tests whether flat structural inference solves partial observability before
invoking hierarchical active inference.
"""
import sys
import os
from collections import defaultdict

sys.path.insert(0, os.path.dirname(__file__))
from environment import EpisodeConfig, ProceduralEnvironment, generate_episodes
from solvers import (
    BayesianSolver, TemporalTrustSolver, ExternalLedgerSolver, 
    CategoryExtrapolatorSolver, OracleSolver
)
from run_evaluation import score_trajectory, format_metric

def run_evaluation(solver, episodes):
    all_metrics = defaultdict(list)
    for ep_config in episodes:
        env = ProceduralEnvironment(ep_config)
        trajectory, result = solver.solve(env)
        
        c = ep_config.condition
        if c == "latent_coupling": 
            # Force escape_rate scoring by spoofing active deception condition mapping
            ep_config.condition = "active_deception"
            ep_config.shifted_item_2 = "latent_marker" 
            # We don't care about escape rate on C5 currently, only final accuracy
        
        metrics = score_trajectory(trajectory, result, ep_config)
        
        if solver.__class__.__name__ == "CategoryExtrapolatorSolver" and not metrics["accuracy"]:
            if len(all_metrics["accuracy"]) == 0:
                print("EXTRAPOLATOR FAILED. Diff:", result.get("true_state_diff"))
                print("Config c5_multiplier:", ep_config.c5_multiplier)
                
        ep_config.condition = c
        
        for k, v in metrics.items():
            all_metrics[k].append(v)
    return all_metrics

def main():
    N = 100
    print(f"Generating N={N} episodes for C5 Latent Coupling...")
    episodes_c5 = generate_episodes(N, condition="latent_coupling", seed_offset=80000)
    
    solvers = {
        "Bayesian (Full)": BayesianSolver(trust_lock=False),
        "Temporal Trust": TemporalTrustSolver(),
        "Ledger (Soft)": ExternalLedgerSolver(hard_flag=False),
        "Category Extrapolator": CategoryExtrapolatorSolver(),
        "Oracle": OracleSolver()
    }

    print("\n# C5 Latent Coupling (Factorized Baseline Check)")
    headers = ["Solver", "Cond", "Accuracy (95% CI)", "Latency", "Belief Rev", "Avg Budget Used"]
    print("| " + " | ".join(headers) + " |")
    print("|---" * len(headers) + "|")

    for solver_name, solver in solvers.items():
        metrics = run_evaluation(solver, episodes_c5)
        # For C5, the truest metric is simply accuracy (did it match the 8 hidden items?)
        acc_str = format_metric("accuracy", metrics["accuracy"], False)
        lat_str = format_metric("detection_latency", metrics["detection_latency"], False)
        rev_str = format_metric("belief_revision_rate", metrics["belief_revision_rate"], False)
        
        # Format latency roughly
        lat_str = "inf" if "inf" in lat_str else "finite"
        budget = sum(metrics["budget_used"]) / max(1, len(metrics["budget_used"]))
        
        row = f"| {solver_name} | C5 | {acc_str} | {lat_str} | {rev_str} | {budget:.1f} |"
        print(row)

if __name__ == "__main__":
    main()
