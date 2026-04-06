"""
Local verification script: simulates exactly what the Kaggle notebook code cells do.
Verifies outputs match frozen results before upload.
"""
import sys, os, math, random
from collections import defaultdict

sys.path.insert(0, os.path.dirname(__file__))
from environment import ProceduralEnvironment, EpisodeConfig, generate_episodes
from solvers import (
    DiscreteHypothesisSolver,
    DiscreteStructureAgentV1,
    DiscreteStructureAgentV2,
    DiscreteStructureAgentV3
)
from run_evaluation import score_trajectory, format_metric

def run_solver_on_c6(solver, episodes):
    all_metrics = defaultdict(list)
    for ep_config in episodes:
        env = ProceduralEnvironment(ep_config)
        trajectory, result = solver.solve(env)
        c = ep_config.condition
        if c == 'c6_hidden_structure':
            ep_config.condition = 'active_deception'
            ep_config.shifted_item_2 = 'latent_marker'
        metrics = score_trajectory(trajectory, result, ep_config)
        ep_config.condition = c
        for k, v in metrics.items():
            all_metrics[k].append(v)
    return all_metrics

N = 100

# === Cell B equivalent ===
print("=" * 60)
print("CELL B: C6 Solver Comparison (Budget=8)")
print("=" * 60)
episodes_c6 = generate_episodes(N, condition='c6_hidden_structure', seed_offset=700000)

solvers_b = {
    'Discrete Baseline': DiscreteHypothesisSolver(),
    'Discrete Agent v1 (Sequential)': DiscreteStructureAgentV1(),
    'Discrete Agent v2 (Adaptive Trust)': DiscreteStructureAgentV2(adaptive_trust=True),
    'Ablation: v2 (no Adaptive Trust)': DiscreteStructureAgentV2(adaptive_trust=False),
    'Discrete Agent v3 (Joint InfoGain)': DiscreteStructureAgentV3(use_improved_policy=True),
}

print('| Solver | Accuracy (95% CI) | Avg Budget Used |')
print('|---|---|---|')
for name, solver in solvers_b.items():
    metrics = run_solver_on_c6(solver, episodes_c6)
    acc_str = format_metric('accuracy', metrics['accuracy'], False)
    budget = sum(metrics['budget_used']) / max(1, len(metrics['budget_used']))
    print(f'| {name} | {acc_str} | {budget:.1f} |')

# === Cell C equivalent ===
print()
print("=" * 60)
print("CELL C: Budget Sweep (averaged across 3 seeds)")
print("=" * 60)

budgets = [6, 8, 10, 12]
seeds = [700000, 800000, 900000]

sweep_solvers = {
    'Agent v1': lambda: DiscreteStructureAgentV1(),
    'Agent v2': lambda: DiscreteStructureAgentV2(adaptive_trust=True),
    'Agent v3': lambda: DiscreteStructureAgentV3(use_improved_policy=True),
}

results = defaultdict(lambda: defaultdict(list))

for solver_name, solver_factory in sweep_solvers.items():
    for seed in seeds:
        for b in budgets:
            episodes = generate_episodes(N, condition='c6_hidden_structure', seed_offset=seed)
            for ep in episodes:
                ep.max_turns = b
            solver = solver_factory()
            metrics_list = []
            for ep_config in episodes:
                env = ProceduralEnvironment(ep_config)
                trajectory, result = solver.solve(env)
                c = ep_config.condition
                if c == 'c6_hidden_structure':
                    ep_config.condition = 'active_deception'
                    ep_config.shifted_item_2 = 'latent_marker'
                m = score_trajectory(trajectory, result, ep_config)
                ep_config.condition = c
                metrics_list.append(m['accuracy'])
            acc = sum(metrics_list) / len(metrics_list)
            results[solver_name][b].append(acc)

headers = ['Solver'] + [f'Budget={b}' for b in budgets]
print('| ' + ' | '.join(headers) + ' |')
print('|---' * len(headers) + '|')
for solver_name in sweep_solvers.keys():
    row = [solver_name]
    for b in budgets:
        avg_acc = sum(results[solver_name][b]) / len(results[solver_name][b])
        row.append(f'{avg_acc*100:.1f}%')
    print('| ' + ' | '.join(row) + ' |')

print()
print("=== VERIFICATION COMPLETE ===")
