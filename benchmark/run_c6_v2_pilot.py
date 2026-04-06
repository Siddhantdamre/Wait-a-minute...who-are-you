"""
Lean C6 Pilot: Discrete Structure Agent v2 Adaptive Trust Validation
"""
import sys
import os
from collections import defaultdict

sys.path.insert(0, os.path.dirname(__file__))
from environment import ProceduralEnvironment, generate_episodes
from solvers import DiscreteHypothesisSolver, DiscreteStructureAgentV1, DiscreteStructureAgentV2
from run_evaluation import score_trajectory, format_metric

def run_evaluation(solver, episodes):
    all_metrics = defaultdict(list)
    for ep_config in episodes:
        env = ProceduralEnvironment(ep_config)
        trajectory, result = solver.solve(env)
        
        c = ep_config.condition
        if c == "c6_hidden_structure": 
            ep_config.condition = "active_deception"
            ep_config.shifted_item_2 = "latent_marker" 
        
        metrics = score_trajectory(trajectory, result, ep_config)
        ep_config.condition = c
        
        for k, v in metrics.items():
            all_metrics[k].append(v)
    return all_metrics

def main():
    N = 100
    print(f"Generating N={N} episodes for C6 Adaptive Trust v2 Pilot...")
    # Use standard offset
    episodes_c6 = generate_episodes(N, condition="c6_hidden_structure", seed_offset=500000)
    
    solvers = {
        "1. Discrete Baseline": DiscreteHypothesisSolver(),
        "2. Discrete Agent v1": DiscreteStructureAgentV1(),
        "3. Discrete Agent v2 (with Adaptive Trust)": DiscreteStructureAgentV2(adaptive_trust=True),
        "4. Ablation: v2 (without Adaptive Trust)": DiscreteStructureAgentV2(adaptive_trust=False)
    }

    print("\n# C6 Discrete v2 Adaptive Trust Pilot Results")
    headers = ["Solver", "Cond", "Accuracy (95% CI)", "Avg Budget Used"]
    print("| " + " | ".join(headers) + " |")
    print("|---" * len(headers) + "|")

    for solver_name, solver in solvers.items():
        metrics = run_evaluation(solver, episodes_c6)
        acc_str = format_metric("accuracy", metrics["accuracy"], False)
        budget = sum(metrics["budget_used"]) / max(1, len(metrics["budget_used"]))
        
        row = f"| {solver_name} | C6 | {acc_str} | {budget:.1f} |"
        print(row)

if __name__ == "__main__":
    main()
