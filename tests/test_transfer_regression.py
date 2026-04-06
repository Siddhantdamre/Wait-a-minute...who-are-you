"""
Transfer Regression Test Suite

Validates DEIC transfer behavior across three configurations:
1. C6 benchmark (golden regression, group_size=4)
2. Cyber incident (isomorphic transfer, group_size=4)
3. Clinical deterioration (non-isomorphic transfer, variable group_sizes)
"""

import sys
import os
import importlib.util

# Absolute project root
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, PROJECT_ROOT)

from deic_core import DEIC


def _load_module(name, filepath):
    """Load a module from an explicit file path to avoid import collisions."""
    spec = importlib.util.spec_from_file_location(name, filepath)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# Load domain-specific modules by explicit path
cyber_env_mod = _load_module('cyber_env', os.path.join(PROJECT_ROOT, 'experiments', 'cyber_transfer', 'environment.py'))
cyber_adp_mod = _load_module('cyber_adp', os.path.join(PROJECT_ROOT, 'experiments', 'cyber_transfer', 'adapter.py'))
clinical_env_mod = _load_module('clinical_env', os.path.join(PROJECT_ROOT, 'experiments', 'clinical_transfer', 'environment.py'))
clinical_adp_mod = _load_module('clinical_adp', os.path.join(PROJECT_ROOT, 'experiments', 'clinical_transfer', 'adapter.py'))


def run_cyber_accuracy(n, budget, seed):
    episodes = cyber_env_mod.generate_cyber_episodes(n, seed_offset=seed)
    solver = cyber_adp_mod.CyberDEICAdapter(adaptive_trust=True)
    correct = 0
    for cfg in episodes:
        cfg.max_queries = budget
        env = cyber_env_mod.CyberIncidentEnvironment(cfg)
        result = solver.diagnose(env)
        if result["correct"]:
            correct += 1
    return correct / n


def run_clinical_accuracy(n, budget, seed):
    episodes = clinical_env_mod.generate_clinical_episodes(n, seed_offset=seed)
    solver = clinical_adp_mod.ClinicalDEICAdapter(adaptive_trust=True)
    correct = 0
    for cfg in episodes:
        cfg.max_queries = budget
        env = clinical_env_mod.ClinicalEnvironment(cfg)
        result = solver.diagnose(env)
        if result["correct"]:
            correct += 1
    return correct / n


def test_cyber_parity():
    print("\n[Test] Cyber Transfer Parity (Budget=8)")
    accs = []
    for seed in [100000, 200000, 300000]:
        acc = run_cyber_accuracy(100, 8, seed)
        accs.append(acc)
        print(f"  Seed={seed}: {acc*100:.1f}%")
    avg = sum(accs) / len(accs)
    print(f"  Average: {avg*100:.1f}%")
    assert 0.45 <= avg <= 0.70, f"CYBER REGRESSION: avg={avg*100:.1f}% outside [45%, 70%]"
    print("  PASS")
    return avg


def test_clinical_budget8():
    print("\n[Test] Clinical Transfer (Budget=8, variable group_sizes)")
    accs = []
    for seed in [500000, 600000, 700000]:
        acc = run_clinical_accuracy(200, 8, seed)
        accs.append(acc)
        print(f"  Seed={seed}: {acc*100:.1f}%")
    avg = sum(accs) / len(accs)
    print(f"  Average: {avg*100:.1f}%")
    assert avg > 0.15, f"CLINICAL REGRESSION: avg={avg*100:.1f}% below 15%"
    print("  PASS")
    return avg


def test_clinical_budget12():
    print("\n[Test] Clinical Transfer (Budget=12, variable group_sizes)")
    accs = []
    for seed in [500000, 600000, 700000]:
        acc = run_clinical_accuracy(200, 12, seed)
        accs.append(acc)
        print(f"  Seed={seed}: {acc*100:.1f}%")
    avg = sum(accs) / len(accs)
    print(f"  Average: {avg*100:.1f}%")
    assert avg > 0.70, f"CLINICAL B12 REGRESSION: avg={avg*100:.1f}% below 70%"
    print("  PASS")
    return avg


if __name__ == '__main__':
    print("=" * 60)
    print("TRANSFER REGRESSION SUITE")
    print("=" * 60)

    cyber = test_cyber_parity()
    clin8 = test_clinical_budget8()
    clin12 = test_clinical_budget12()

    print("\n" + "=" * 60)
    print("ALL TRANSFER TESTS PASSED")
    print(f"  Cyber Budget=8:    {cyber*100:.1f}%")
    print(f"  Clinical Budget=8: {clin8*100:.1f}%")
    print(f"  Clinical Budget=12:{clin12*100:.1f}%")
    print("=" * 60)
