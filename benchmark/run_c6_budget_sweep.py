"""
Lean C6 Budget Sweep: Robustness and Ceiling Validation
"""
import sys
import os
from collections import defaultdict

sys.path.insert(0, os.path.dirname(__file__))
from environment import ProceduralEnvironment, generate_episodes
from solvers import DiscreteStructureAgentV1, DiscreteStructureAgentV2, DiscreteStructureAgentV3
from run_evaluation import score_trajectory

def run_evaluation(solver, episodes):
    metrics_list = []
    for ep_config in episodes:
        env = ProceduralEnvironment(ep_config)
        trajectory, result = solver.solve(env)
        
        c = ep_config.condition
        if c == "c6_hidden_structure": 
            ep_config.condition = "active_deception"
            ep_config.shifted_item_2 = "latent_marker" 
        
        metrics = score_trajectory(trajectory, result, ep_config)
        ep_config.condition = c
        metrics_list.append(metrics["accuracy"])
    return sum(metrics_list) / len(metrics_list)

def main():
    N = 100 # per seed
    budgets = [6, 8, 10, 12]
    seeds = [700000, 800000, 900000]
    
    solvers = {
        "Discrete Agent v1": lambda: DiscreteStructureAgentV1(),
        "Discrete Agent v2": lambda: DiscreteStructureAgentV2(adaptive_trust=True),
        "Discrete Agent v3": lambda: DiscreteStructureAgentV3(use_improved_policy=True)
    }

    print("--- C6 Robustness and Budget Sweep ---")
    
    # Store aggregated results: dict[solver][budget] = list of accuracies
    results = defaultdict(lambda: defaultdict(list))
    
    for solver_name, solver_factory in solvers.items():
        for seed in seeds:
            for b in budgets:
                episodes = generate_episodes(N, condition="c6_hidden_structure", seed_offset=seed)
                for ep in episodes:
                    ep.max_turns = b
                solver = solver_factory()
                acc = run_evaluation(solver, episodes)
                results[solver_name][b].append(acc)

    # Print averaged table
    print("\n# Averaged Accuracy Across Seeds")
    headers = ["Solver"] + [f"Budget={b}" for b in budgets]
    print("| " + " | ".join(headers) + " |")
    print("|---" * len(headers) + "|")
    
    for solver_name in solvers.keys():
        row = [solver_name]
        for b in budgets:
            avg_acc = sum(results[solver_name][b]) / len(results[solver_name][b])
            row.append(f"{avg_acc*100:.1f}%")
        print("| " + " | ".join(row) + " |")

    # Print raw data for robustness check
    print("\n# Raw Seed Data (Budget 8)")
    for solver_name in solvers.keys():
        row = f"{solver_name}: " + ", ".join([f"{acc*100:.1f}%" for acc in results[solver_name][8]])
        print(row)

if __name__ == "__main__":
    main()
