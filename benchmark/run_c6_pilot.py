"""
Lean C6 Pilot: Unknown / Drifting Category Structure
Tests whether solvers can infer latent structure when categorization is hidden and budget is tight.
"""
import sys
import os
from collections import defaultdict

sys.path.insert(0, os.path.dirname(__file__))
from environment import EpisodeConfig, ProceduralEnvironment, generate_episodes
from solvers import (
    BayesianSolver, TemporalTrustSolver, ExternalLedgerSolver, 
    CategoryExtrapolatorSolver, FlatStructureLearnerSolver
)
from run_evaluation import score_trajectory, format_metric

def run_evaluation(solver, episodes):
    all_metrics = defaultdict(list)
    for ep_config in episodes:
        env = ProceduralEnvironment(ep_config)
        trajectory, result = solver.solve(env)
        
        c = ep_config.condition
        if c == "c6_hidden_structure": 
            # Force escape_rate scoring by spoofing active deception condition mapping
            ep_config.condition = "active_deception"
            ep_config.shifted_item_2 = "latent_marker" 
        
        metrics = score_trajectory(trajectory, result, ep_config)
        ep_config.condition = c
        
        for k, v in metrics.items():
            all_metrics[k].append(v)
    return all_metrics

def main():
    N = 100
    print(f"Generating N={N} episodes for C6 Hidden Structure...")
    episodes_c6 = generate_episodes(N, condition="c6_hidden_structure", seed_offset=90000)
    
    solvers = {
        "Ledger (Soft)": ExternalLedgerSolver(hard_flag=False),
        "Temporal Trust": TemporalTrustSolver(),
        "Category Extrapolator": CategoryExtrapolatorSolver(),
        "Flat Structure Learner": FlatStructureLearnerSolver()
    }

    print("\n# C6 Hidden Structure (Unknown Categories Check)")
    headers = ["Solver", "Cond", "Accuracy (95% CI)", "Latency", "Belief Rev", "Avg Budget Used"]
    print("| " + " | ".join(headers) + " |")
    print("|---" * len(headers) + "|")

    for solver_name, solver in solvers.items():
        metrics = run_evaluation(solver, episodes_c6)
        acc_str = format_metric("accuracy", metrics["accuracy"], False)
        lat_str = format_metric("detection_latency", metrics["detection_latency"], False)
        rev_str = format_metric("belief_revision_rate", metrics["belief_revision_rate"], False)
        
        lat_str = "inf" if "inf" in lat_str else "finite"
        budget = sum(metrics["budget_used"]) / max(1, len(metrics["budget_used"]))
        
        row = f"| {solver_name} | C6 | {acc_str} | {lat_str} | {rev_str} | {budget:.1f} |"
        print(row)

if __name__ == "__main__":
    main()
