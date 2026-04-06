"""
Lean Transfer Pilot: DEIC on Cyber Incident Diagnosis

Tests whether the DEIC engine — extracted from the Byzantine
Executive Belief Benchmark — transfers to a structurally
isomorphic but domain-different environment with zero code
changes to deic_core/core.py.

Comparison:
  1. DEIC (adaptive trust) on cyber domain
  2. DEIC (no adaptive trust) on cyber domain
  3. Random baseline on cyber domain
  4. Budget sweep {6, 8, 10, 12}
"""

import sys
import os
from collections import defaultdict

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from environment import CyberIncidentEnvironment, generate_cyber_episodes
from adapter import CyberDEICAdapter
from deic_core import DEIC
import random


class RandomDiagnoser:
    """Baseline: random diagnosis with no inference."""

    def diagnose(self, env):
        baseline = env.get_baseline_latency()
        services = env.get_services()
        # Randomly guess: pick 4 services as affected, random multiplier
        rng = random.Random(env.config.seed + 9999)
        shuffled = list(services)
        rng.shuffle(shuffled)
        affected = set(shuffled[:4])
        mult = rng.choice([1.5, 2.0, 3.0, 5.0])
        proposed = {}
        for svc in services:
            if svc in affected:
                proposed[svc] = int(baseline[svc] * mult)
            else:
                proposed[svc] = baseline[svc]
        return env.submit_diagnosis(proposed)


def run_evaluation(diagnoser, episodes_configs, budget=8):
    correct = 0
    total = len(episodes_configs)
    for cfg in episodes_configs:
        cfg.max_queries = budget
        env = CyberIncidentEnvironment(cfg)
        result = diagnoser.diagnose(env)
        if result["correct"]:
            correct += 1
    return correct / total


def main():
    N = 100
    seeds = [100000, 200000, 300000]
    budgets = [6, 8, 10, 12]

    print("=" * 65)
    print("PHASE 3: DEIC Transfer Pilot — Cyber Incident Diagnosis")
    print("=" * 65)

    # --- Test 1: Head-to-head at Budget=8 ---
    print("\n## Head-to-Head Comparison (Budget=8, N=100, 3 seeds)")
    print("| Solver | Seed 1 | Seed 2 | Seed 3 | Average |")
    print("|---|---|---|---|---|")

    solvers = {
        "Random Baseline": lambda: RandomDiagnoser(),
        "DEIC (no trust)": lambda: CyberDEICAdapter(adaptive_trust=False),
        "DEIC (adaptive trust)": lambda: CyberDEICAdapter(adaptive_trust=True),
    }

    for name, factory in solvers.items():
        accs = []
        for seed in seeds:
            episodes = generate_cyber_episodes(N, seed_offset=seed)
            solver = factory()
            acc = run_evaluation(solver, episodes, budget=8)
            accs.append(acc)
        avg = sum(accs) / len(accs)
        cols = " | ".join([f"{a*100:.1f}%" for a in accs])
        print(f"| {name} | {cols} | {avg*100:.1f}% |")

    # --- Test 2: Budget sweep ---
    print("\n## Budget Sweep (DEIC Adaptive Trust, averaged across 3 seeds)")
    headers = ["Solver"] + [f"Budget={b}" for b in budgets]
    print("| " + " | ".join(headers) + " |")
    print("|---" * len(headers) + "|")

    sweep_results = defaultdict(list)
    for seed in seeds:
        for b in budgets:
            episodes = generate_cyber_episodes(N, seed_offset=seed)
            solver = CyberDEICAdapter(adaptive_trust=True)
            acc = run_evaluation(solver, episodes, budget=b)
            sweep_results[b].append(acc)

    row = ["DEIC (adaptive trust)"]
    for b in budgets:
        avg = sum(sweep_results[b]) / len(sweep_results[b])
        row.append(f"{avg*100:.1f}%")
    print("| " + " | ".join(row) + " |")

    # --- Verdict ---
    avg_b8 = sum(sweep_results[8]) / len(sweep_results[8])
    avg_b12 = sum(sweep_results[12]) / len(sweep_results[12])
    print("\n## Transfer Verdict")
    print(f"  Budget=8  accuracy: {avg_b8*100:.1f}%")
    print(f"  Budget=12 accuracy: {avg_b12*100:.1f}%")

    if avg_b8 > 0.40:
        print("  RESULT: DEIC transfers to cyber domain with meaningful performance.")
        print("  Zero changes were made to deic_core/core.py.")
    else:
        print("  RESULT: Transfer did not produce meaningful performance.")

    print("\n" + "=" * 65)


if __name__ == "__main__":
    main()
