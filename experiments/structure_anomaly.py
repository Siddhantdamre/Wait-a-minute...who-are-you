"""
Phase 14 Evaluation: Structure Anomaly Tests

Tests DEIC's dynamic structure adaptation by creating episodes
where the hidden group size differs from the generator's assumption.

Test cases:
  1. cyber_group_size_5: 5 services affected (generator assumes 4)
  2. cyber_group_size_3: 3 services affected (generator assumes 4)
  3. Regression: standard cyber (group_size=4, should be unaffected)
"""

import sys
import os
import json
import numpy as np

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, PROJECT_ROOT)

import random
from experiments.cyber_transfer.environment import (
    CyberEpisodeConfig, CyberIncidentEnvironment,
    SERVICE_NAMES, MONITOR_NAMES, generate_cyber_episodes,
)
from experiments.cyber_transfer.adapter import CyberDEICAdapter


# ── Anomalous Episode Configs ──────────────────────────────────────

class AnomalyCyberConfig(CyberEpisodeConfig):
    """CyberEpisodeConfig with a non-standard affected group size."""

    def __init__(self, seed, group_size, n_services=8):
        rng = random.Random(seed)
        self.services = SERVICE_NAMES[:n_services]
        self.baseline_latency = {svc: rng.randint(10, 200) for svc in self.services}

        shuffled = list(self.services)
        rng.shuffle(shuffled)
        self.affected_group = shuffled[:group_size]
        self.unaffected_group = shuffled[group_size:]
        self.severity_multiplier = rng.choice([1.5, 2.0, 3.0, 5.0])
        self.faulty_monitor = rng.choice(MONITOR_NAMES)
        self.max_queries = 20  # Budget raised to guarantee trust lock + structure collapse
        self.seed = seed


def generate_anomaly_episodes(n, group_size, seed_offset=7000):
    return [AnomalyCyberConfig(seed=seed_offset + i, group_size=group_size) for i in range(n)]


# ── Evaluation ─────────────────────────────────────────────────────

def run_test(episodes, adapter):
    escalates = 0
    correct_commits = 0
    silent_failures = 0
    adaptations = []
    outcomes = []
    
    # Phase 15 Metrics
    missed_nodes = []
    blindspots = []
    categories = []
    post_adapt_queries = []

    for config in episodes:
        env = CyberIncidentEnvironment(config)
        res = adapter.diagnose(env)

        ws = res.get("final_workspace", {})
        is_escalated = res.get("escalated") or False

        if is_escalated:
            escalates += 1
        else:
            if res.get("correct"):
                correct_commits += 1
            if ws.get("confidence_margin", 0.0) < 0.95:
                silent_failures += 1

        adaptations.append(ws.get("adaptation_count", 0))
        outcomes.append(ws.get("family_search_outcome", ""))
        
        # New Telemetry
        missed_nodes.append(ws.get("missed_anomalous_node", False))
        blindspots.append(ws.get("coverage_blindspot_triggered", False))
        categories.append(ws.get("final_outcome_category", "unknown"))
        if ws.get("adaptation_count", 0) > 0:
            post_adapt_queries.append(ws.get("post_adaptation_queries", 0))

    total = len(episodes)
    commits = total - escalates
    
    unique_cats, cat_counts = np.unique(categories, return_counts=True)
    category_summary = dict(zip(unique_cats, cat_counts))

    return {
        "total": total,
        "escalate_rate": escalates / total,
        "commit_coverage": commits / total,
        "accuracy_on_commit": correct_commits / max(1, commits),
        "silent_failure_rate": silent_failures / total,
        "avg_adaptations": np.mean(adaptations),
        "outcomes": dict(zip(
            *np.unique([o or "none" for o in outcomes], return_counts=True)
        )),
        "missed_node_rate": np.mean(missed_nodes),
        "blindspot_rate": np.mean(blindspots),
        "avg_post_adapt_queries": np.mean(post_adapt_queries) if post_adapt_queries else 0,
        "categories": category_summary
    }


if __name__ == "__main__":
    N = 100 # Keep N=100 for final A/B check
    
    # Configure two adapters for A/B testing
    adapter_v85 = CyberDEICAdapter(
        use_planner=True,
        confidence_threshold=0.999,
        coverage_threshold=0.85,
        enable_final_contradiction_probe=False,
    )
    adapter_v100 = CyberDEICAdapter(
        use_planner=True,
        confidence_threshold=0.999,
        coverage_threshold=1.0,
        enable_final_contradiction_probe=False,
    )

    print("=" * 60)
    print("PHASE 15 — ADAPTATION RECOVERY A/B TEST (85% vs 100% COVERAGE)")
    print("=" * 60)

    # 1. Group Size 5
    print("\n--- Test 1: group_size=5 (anomaly) ---")
    gs5_episodes = generate_anomaly_episodes(N, group_size=5, seed_offset=7000)
    print("Running Baseline (85%)...")
    gs5_v85 = run_test(gs5_episodes, adapter_v85)
    print("Running Strict (100%)...")
    gs5_v100 = run_test(gs5_episodes, adapter_v100)

    # 2. Group Size 3
    print("\n--- Test 2: group_size=3 (anomaly) ---")
    gs3_episodes = generate_anomaly_episodes(N, group_size=3, seed_offset=8000)
    print("Running Baseline (85%)...")
    gs3_v85 = run_test(gs3_episodes, adapter_v85)
    print("Running Strict (100%)...")
    gs3_v100 = run_test(gs3_episodes, adapter_v100)

    # 3. Regression
    print("\n--- Test 3: group_size=4 (regression baseline) ---")
    gs4_episodes = generate_cyber_episodes(N, seed_offset=2000)
    for ep in gs4_episodes:
        ep.max_queries = 20
    print("Running Baseline (85%)...")
    gs4_v85 = run_test(gs4_episodes, adapter_v85)
    print("Running Strict (100%)...")
    gs4_v100 = run_test(gs4_episodes, adapter_v100)

    # Detailed Comparison Table
    print("\n" + "=" * 60)
    print("A/B TEST COMPARISON: ACCURACY & TRIGGER RATE")
    print("=" * 60)
    print(f"{'Test':<20} | {'Mode':<6} | {'Acc%':<6} | {'Blind%':<6} | {'Adapt':<6}")
    for name, v85, v100 in [
        ("gs=5 anomaly", gs5_v85, gs5_v100),
        ("gs=3 anomaly", gs3_v85, gs3_v100),
        ("gs=4 regression", gs4_v85, gs4_v100)
    ]:
        print(f"{name:<20} | {'v85':<6} | {v85['accuracy_on_commit']*100:<6.1f} | {v85.get('blindspot_rate',0)*100:<6.1f} | {v85['avg_adaptations']:<6.2f}")
        print(f"{name:<20} | {'v100':<6} | {v100['accuracy_on_commit']*100:<6.1f} | {v100.get('blindspot_rate',0)*100:<6.1f} | {v100['avg_adaptations']:<6.2f}")
        print("-" * 55)

    # Category Shifts
    print("\nCATEGORY SHIFT (gs=5 anomaly):")
    print(f"  v85 Categories:  {gs5_v85['categories']}")
    print(f"  v100 Categories: {gs5_v100['categories']}")

    # Save all
    all_results = {
        "v85": {"gs5": gs5_v85, "gs3": gs3_v85, "gs4": gs4_v85},
        "v100": {"gs5": gs5_v100, "gs3": gs3_v100, "gs4": gs4_v100}
    }

    # Save results
    def convert(obj):
        if isinstance(obj, (np.integer,)):
            return int(obj)
        if isinstance(obj, (np.floating,)):
            return float(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return obj

    with open("phase15_ab_results.json", "w") as f:
        json.dump(all_results, f, indent=2, default=convert)
    print(f"\nResults saved to phase15_ab_results.json")
