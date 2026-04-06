"""
Golden Regression Test for DEIC Extraction.

Validates that the extracted DEIC engine (via the benchmark adapter)
reproduces the frozen C6 performance within explicit tolerance bands.

Frozen targets (averaged across 3 seed batches):
  Budget=8  -> ~61.3%  (acceptable: 55.0% - 68.0%)
  Budget=12 -> ~93.0%  (acceptable: 88.0% - 98.0%)

Tolerance is wider than runtime variance to account for random
tie-breaking in propose_state(). The important invariant is that
the adapter does NOT silently degrade below the baseline range.
"""
import sys
import os
from collections import defaultdict

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'benchmark'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from environment import ProceduralEnvironment, generate_episodes
from deic_adapter import DEICBenchmarkAdapter
from run_evaluation import score_trajectory


def run_c6_accuracy(adapter, n_episodes, budget, seed_offset):
    episodes = generate_episodes(n_episodes, condition='c6_hidden_structure', seed_offset=seed_offset)
    for ep in episodes:
        ep.max_turns = budget

    correct = 0
    for ep_config in episodes:
        env = ProceduralEnvironment(ep_config)
        trajectory, result = adapter.solve(env)

        c = ep_config.condition
        ep_config.condition = 'active_deception'
        ep_config.shifted_item_2 = 'latent_marker'
        metrics = score_trajectory(trajectory, result, ep_config)
        ep_config.condition = c

        correct += metrics['accuracy']

    return correct / n_episodes


def test_budget_8():
    seeds = [700000, 800000, 900000]
    n = 100
    accs = []
    for seed in seeds:
        adapter = DEICBenchmarkAdapter(adaptive_trust=True)
        acc = run_c6_accuracy(adapter, n, budget=8, seed_offset=seed)
        accs.append(acc)
        print(f"  Budget=8, Seed={seed}: {acc*100:.1f}%")

    avg = sum(accs) / len(accs)
    print(f"  Budget=8 Average: {avg*100:.1f}%")
    assert 0.55 <= avg <= 0.68, f"REGRESSION FAILURE: Budget=8 avg={avg*100:.1f}% outside [55.0%, 68.0%]"
    print("  Budget=8: PASS")
    return avg


def test_budget_12():
    seeds = [700000, 800000, 900000]
    n = 100
    accs = []
    for seed in seeds:
        adapter = DEICBenchmarkAdapter(adaptive_trust=True)
        acc = run_c6_accuracy(adapter, n, budget=12, seed_offset=seed)
        accs.append(acc)
        print(f"  Budget=12, Seed={seed}: {acc*100:.1f}%")

    avg = sum(accs) / len(accs)
    print(f"  Budget=12 Average: {avg*100:.1f}%")
    assert 0.88 <= avg <= 0.98, f"REGRESSION FAILURE: Budget=12 avg={avg*100:.1f}% outside [88.0%, 98.0%]"
    print("  Budget=12: PASS")
    return avg


if __name__ == '__main__':
    print("=" * 60)
    print("GOLDEN REGRESSION TEST: DEIC Extraction Parity")
    print("=" * 60)

    print("\n[Test 1] Budget=8 (frozen target: ~61.3%)")
    avg8 = test_budget_8()

    print("\n[Test 2] Budget=12 (frozen target: ~93.0%)")
    avg12 = test_budget_12()

    print("\n" + "=" * 60)
    print("ALL GOLDEN REGRESSION TESTS PASSED")
    print(f"  Budget=8:  {avg8*100:.1f}%")
    print(f"  Budget=12: {avg12*100:.1f}%")
    print("=" * 60)
