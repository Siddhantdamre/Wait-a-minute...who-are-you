"""
Lean Benchmark Evaluation for fast decision making.
"""
import sys
import os
import math
import random
from collections import defaultdict

sys.path.insert(0, os.path.dirname(__file__))
from environment import EpisodeConfig, ProceduralEnvironment, generate_episodes
from solvers import (
    BayesianSolver, TemporalTrustSolver, ExternalLedgerSolver, OracleSolver
)
from run_evaluation import score_trajectory, format_metric

def run_evaluation(solver, episodes):
    all_metrics = defaultdict(list)
    for ep_config in episodes:
        # C5 smoke has the exact same failure criteria as C4 to score escape rate
        if ep_config.condition == "c5_smoke":
            ep_config.shifted_item_2 = ep_config.shifted_item_2 # ensure it exists
            
        env = ProceduralEnvironment(ep_config)
        trajectory, result = solver.solve(env)
        
        # We need score_trajectory to handle c5_smoke as active deception
        c = ep_config.condition
        if c == "c5_smoke": ep_config.condition = "active_deception"
        metrics = score_trajectory(trajectory, result, ep_config)
        ep_config.condition = c
        
        for k, v in metrics.items():
            all_metrics[k].append(v)
    return all_metrics

def main():
    N_lean = 150
    N_smoke = 100
    
    print(f"Generating N={N_lean} for C3/C4, and N={N_smoke} for C5 Smoke...")
    episodes_c3 = generate_episodes(N_lean, condition="stale_state", seed_offset=50000)
    episodes_c4 = generate_episodes(N_lean, condition="active_deception", seed_offset=60000)
    episodes_c5 = generate_episodes(N_smoke, condition="c5_smoke", seed_offset=70000)
    
    solvers_lean = {
        "Bayesian (Full)": BayesianSolver(trust_lock=False),
        "Bayesian (Ablated)": BayesianSolver(trust_lock=True),
        "Temporal Trust": TemporalTrustSolver(),
        "Ledger (Soft)": ExternalLedgerSolver(hard_flag=False),
        "Oracle": OracleSolver()
    }
    
    solvers_c5 = {
        "Temporal Trust": TemporalTrustSolver(),
        "Ledger (Soft)": ExternalLedgerSolver(hard_flag=False),
        "Oracle": OracleSolver()
    }

    conditions = [
        ("C3", episodes_c3, False, solvers_lean),
        ("C4", episodes_c4, True, solvers_lean),
        ("C5 (Smoke)", episodes_c5, True, solvers_c5)
    ]

    print("\n# Lean Benchmark Validation Results")
    headers = ["Solver", "Cond", "Accuracy (95% CI)", "Escape Rate (95% CI)", "Latency", "Belief Rev"]
    print("| " + " | ".join(headers) + " |")
    print("|---" * len(headers) + "|")

    for condition_name, eps, is_c4, condition_solvers in conditions:
        for solver_name, solver in condition_solvers.items():
            metrics = run_evaluation(solver, eps)
            acc_str = format_metric("accuracy", metrics["accuracy"], is_c4)
            esc_str = format_metric("escape_rate", metrics["escape_rate"], is_c4)
            lat_str = format_metric("detection_latency", metrics["detection_latency"], is_c4)
            rev_str = format_metric("belief_revision_rate", metrics["belief_revision_rate"], is_c4)
            
            # format escapes string to match table headers
            if "±" in lat_str:
                lat_str = "inf" if "inf(100%)" in lat_str.replace(" ","") else "finite"
                
            row = f"| {solver_name} | {condition_name} | {acc_str} | {esc_str} | {lat_str} | {rev_str} |"
            print(row)

if __name__ == "__main__":
    main()
