import sys
import os
import math
from collections import defaultdict

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from benchmark.environment import generate_episodes, ProceduralEnvironment
from benchmark.deic_adapter import DEICBenchmarkAdapter
from benchmark.run_evaluation import score_trajectory

from experiments.cyber_transfer.environment import CyberIncidentEnvironment
from experiments.cyber_transfer.adapter import CyberDEICAdapter

from experiments.clinical_transfer.environment import ClinicalEnvironment
from experiments.clinical_transfer.adapter import ClinicalDEICAdapter

def run_c6(budget=8, seed=123, use_planner=False, n_episodes=100):
    episodes = generate_episodes(n_episodes, condition='c6_hidden_structure', seed_offset=seed)
    adapter = DEICBenchmarkAdapter(use_planner=use_planner)
    
    accuracies = []
    budgets_used = []
    escalations = 0

    for config in episodes:
        config.max_turns = budget
        env = ProceduralEnvironment(config)
        traj, res = adapter.solve(env)
        
        # Determine if escalated
        esc = False
        if traj and traj[-1].get("next_action", {}).get("escalated", False):
            esc = True
            escalations += 1

        # Use score_trajectory to easily get metrics
        # Adjust config temporarily to trick score_trajectory into correctly scoring it
        c = config.condition
        config.condition = "active_deception"
        config.shifted_item_2 = "latent_marker"
        metrics = score_trajectory(traj, res, config)
        config.condition = c
        
        accuracies.append(metrics["accuracy"])
        budgets_used.append(metrics["budget_used"])

    return {
        "accuracy": sum(accuracies) / len(accuracies),
        "avg_budget": sum(budgets_used) / len(budgets_used),
        "escalations": escalations
    }

def run_cyber(budget=10, seed=123, use_planner=False, n_episodes=100):
    import random
    rng = random.Random(seed)
    adapter = CyberDEICAdapter(use_planner=use_planner)
    
    correct = 0
    budgets_used = []
    
    for i in range(n_episodes):
        from experiments.cyber_transfer.environment import CyberEpisodeConfig
        cfg = CyberEpisodeConfig(seed=seed+i, n_services=6)
        cfg.max_queries = budget
        env = CyberIncidentEnvironment(cfg)
        
        res = adapter.diagnose(env)
        
        if res.get("correct", False):
            correct += 1
        budgets_used.append(env.turn)

    return {
        "accuracy": correct / n_episodes,
        "avg_budget": sum(budgets_used) / len(budgets_used),
        "escalations": 0 # Not cleanly tracked in diagnosis payload without trajectory
    }

def run_clinical(budget=10, seed=123, use_planner=False, n_episodes=100):
    import random
    rng = random.Random(seed)
    adapter = ClinicalDEICAdapter(use_planner=use_planner)
    
    correct = 0
    budgets_used = []
    
    for i in range(n_episodes):
        from experiments.clinical_transfer.environment import ClinicalEpisodeConfig
        cfg = ClinicalEpisodeConfig(seed=seed+i, n_patients=6)
        cfg.max_queries = budget
        env = ClinicalEnvironment(cfg)
        
        res = adapter.diagnose(env)
        
        if res.get("correct", False):
            correct += 1
        budgets_used.append(env.turn)

    return {
        "accuracy": correct / n_episodes,
        "avg_budget": sum(budgets_used) / len(budgets_used),
        "escalations": 0
    }

if __name__ == "__main__":
    n = 100
    with open("planner_comparison_metrics.txt", "w", encoding='utf-8') as f:
        f.write(f"--- PLANNER INTEGRATION METRICS (N={n}) ---\n")
        
        for name, run_fn, args in [
            ("C6 Benchmark", run_c6, {"budget": 12}),
            ("Cyber Transfer", run_cyber, {"budget": 8}), # tightened budget for cyber
            ("Clinical Transfer", run_clinical, {"budget": 8})
        ]:
            f.write(f"\n{name} (Budget={args['budget']})\n")
            off = run_fn(**args, use_planner=False)
            on = run_fn(**args, use_planner=True)
            
            f.write(f"                OFF          | ON\n")
            f.write(f"  Accuracy:     {off['accuracy']:.1%}        | {on['accuracy']:.1%}\n")
            f.write(f"  Avg Budget:   {off['avg_budget']:.2f}         | {on['avg_budget']:.2f}\n")
            if 'escalations' in off and (off['escalations'] > 0 or on['escalations'] > 0):
                f.write(f"  Escalations:  {off['escalations']}            | {on['escalations']}\n")
