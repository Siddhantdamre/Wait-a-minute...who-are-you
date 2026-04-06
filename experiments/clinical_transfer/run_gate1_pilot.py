"""
Gate 1: Zero-Modification Clinical Transfer Test

Tests DEIC — completely unchanged — on a clinical deterioration
environment where the number of affected patients varies (2-6)
instead of being fixed at 4.

This is the strongest available test of DEIC's generalization.
DEIC may fail because its hypothesis bank assumes exactly 4
items are affected. If it fails, we learn which assumption
breaks and how badly.

Outputs:
  1. Head-to-head comparison table (Budget=8)
  2. Budget sweep table
  3. Failure-mode breakdown by true group size
  4. Explicit answer: does DEIC generalize?
"""

import sys
import os
import random
from collections import defaultdict

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from environment import ClinicalEnvironment, generate_clinical_episodes
from adapter import ClinicalDEICAdapter


class RandomDiagnoser:
    def diagnose(self, env):
        baseline = env.get_baseline_vitals()
        patients = env.get_patients()
        rng = random.Random(env.config.seed + 9999)
        shuffled = list(patients)
        rng.shuffle(shuffled)
        n = rng.randint(2, 6)
        affected = set(shuffled[:n])
        mult = rng.choice([1.3, 1.8, 2.5])
        proposed = {}
        for p in patients:
            proposed[p] = int(baseline[p] * mult) if p in affected else baseline[p]
        return env.submit_assessment(proposed)


def run_evaluation(diagnoser, episode_configs, budget=8):
    results = []
    for cfg in episode_configs:
        cfg.max_queries = budget
        env = ClinicalEnvironment(cfg)
        result = diagnoser.diagnose(env)
        result['true_group_size'] = len(cfg.deteriorating)
        result['severity'] = cfg.severity
        results.append(result)
    return results


def main():
    N = 200  # more episodes for per-group-size analysis
    seeds = [500000, 600000, 700000]
    budgets = [6, 8, 10, 12]

    print("=" * 65)
    print("GATE 1: Zero-Modification Clinical Transfer")
    print("DEIC core.py: UNCHANGED (group_size=4 hardcoded)")
    print("Clinical domain: variable group size (2-6)")
    print("=" * 65)

    # --- Head-to-head at Budget=8 ---
    print("\n## Head-to-Head (Budget=8, N=200, 3 seeds)")
    print("| Solver | Seed 1 | Seed 2 | Seed 3 | Average |")
    print("|---|---|---|---|---|")

    solvers = {
        "Random Baseline": lambda: RandomDiagnoser(),
        "DEIC (no trust)": lambda: ClinicalDEICAdapter(adaptive_trust=False),
        "DEIC (adaptive trust)": lambda: ClinicalDEICAdapter(adaptive_trust=True),
    }

    for name, factory in solvers.items():
        accs = []
        for seed in seeds:
            episodes = generate_clinical_episodes(N, seed_offset=seed)
            solver = factory()
            results = run_evaluation(solver, episodes, budget=8)
            acc = sum(1 for r in results if r['correct']) / len(results)
            accs.append(acc)
        avg = sum(accs) / len(accs)
        cols = " | ".join([f"{a*100:.1f}%" for a in accs])
        print(f"| {name} | {cols} | {avg*100:.1f}% |")

    # --- Budget sweep ---
    print("\n## Budget Sweep (DEIC Adaptive Trust, averaged across 3 seeds)")
    print("| Solver | Budget=6 | Budget=8 | Budget=10 | Budget=12 |")
    print("|---|---|---|---|---|")

    sweep = defaultdict(list)
    for seed in seeds:
        for b in budgets:
            episodes = generate_clinical_episodes(N, seed_offset=seed)
            solver = ClinicalDEICAdapter(adaptive_trust=True)
            results = run_evaluation(solver, episodes, budget=b)
            acc = sum(1 for r in results if r['correct']) / len(results)
            sweep[b].append(acc)

    row = ["DEIC (adaptive trust)"]
    for b in budgets:
        avg = sum(sweep[b]) / len(sweep[b])
        row.append(f"{avg*100:.1f}%")
    print("| " + " | ".join(row) + " |")

    # --- Failure-mode breakdown by true group size ---
    print("\n## Accuracy by True Group Size (Budget=8, all seeds pooled)")
    print("| True Group Size | Episodes | DEIC Accuracy | Expectation |")
    print("|---|---|---|---|")

    all_results = []
    for seed in seeds:
        episodes = generate_clinical_episodes(N, seed_offset=seed)
        solver = ClinicalDEICAdapter(adaptive_trust=True)
        results = run_evaluation(solver, episodes, budget=8)
        all_results.extend(results)

    by_size = defaultdict(list)
    for r in all_results:
        by_size[r['true_group_size']].append(r['correct'])

    for gs in sorted(by_size.keys()):
        count = len(by_size[gs])
        acc = sum(by_size[gs]) / count
        expectation = "matches DEIC assumption" if gs == 4 else "MISMATCHED"
        print(f"| {gs} | {count} | {acc*100:.1f}% | {expectation} |")

    # --- Failure-mode breakdown by severity ---
    print("\n## Accuracy by Severity (Budget=8, all seeds pooled)")
    print("| Severity | Episodes | DEIC Accuracy |")
    print("|---|---|---|")

    by_sev = defaultdict(list)
    for r in all_results:
        by_sev[r['severity']].append(r['correct'])

    for sev in sorted(by_sev.keys()):
        count = len(by_sev[sev])
        acc = sum(by_sev[sev]) / count
        print(f"| {sev}x | {count} | {acc*100:.1f}% |")

    # --- Verdict ---
    overall_acc = sum(1 for r in all_results if r['correct']) / len(all_results)
    gs4_results = [r for r in all_results if r['true_group_size'] == 4]
    gs4_acc = sum(1 for r in gs4_results if r['correct']) / len(gs4_results) if gs4_results else 0
    non4_results = [r for r in all_results if r['true_group_size'] != 4]
    non4_acc = sum(1 for r in non4_results if r['correct']) / len(non4_results) if non4_results else 0

    print("\n## Verdict")
    print(f"  Overall accuracy (Budget=8): {overall_acc*100:.1f}%")
    print(f"  Group-size=4 episodes:       {gs4_acc*100:.1f}% ({len(gs4_results)} episodes)")
    print(f"  Group-size!=4 episodes:      {non4_acc*100:.1f}% ({len(non4_results)} episodes)")

    if overall_acc > 0.40:
        print("  DEIC shows meaningful generalization even with mismatched group-size assumption.")
    elif gs4_acc > 0.40 and non4_acc < 0.20:
        print("  DEIC succeeds ONLY when group size matches assumption (4). Clear structural bottleneck.")
    else:
        print("  DEIC does not generalize to the clinical domain in its current form.")

    print(f"\n  Does DEIC generalize without modification? ", end="")
    if overall_acc > 0.40:
        print("PARTIALLY YES — meaningful performance despite assumption mismatch.")
    elif gs4_acc > 0.40:
        print("NO — performance is contingent on the group_size=4 assumption holding.")
    else:
        print("NO — fundamental failure across all group sizes.")

    print("\n" + "=" * 65)
    print("GATE 1 COMPLETE — STOP HERE")
    print("Do not modify deic_core/core.py until results are reviewed.")
    print("=" * 65)


if __name__ == "__main__":
    main()
