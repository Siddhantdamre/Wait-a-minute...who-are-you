"""
Phase 15d: Cross-domain adaptive validation

Runs before/after validation for the guarded ADAPT_REFINE path across:
  - cyber fixed-family anomalies (gs=3 / gs=5)
  - clinical closest structural mismatch cases using a fixed-family adapter
  - standard cyber gs=4 baseline
  - planner-integrated C6 standard cases
"""

import json
import os
import sys
import random

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, PROJECT_ROOT)
sys.path.insert(0, os.path.join(PROJECT_ROOT, "benchmark"))

from benchmark.environment import generate_episodes, ProceduralEnvironment
from benchmark.deic_adapter import DEICBenchmarkAdapter
from experiments.cyber_transfer.environment import (
    CyberIncidentEnvironment,
    generate_cyber_episodes,
)
from experiments.cyber_transfer.adapter import CyberDEICAdapter
from experiments.structure_anomaly import generate_anomaly_episodes
from experiments.clinical_transfer.environment import (
    ClinicalEnvironment,
    ClinicalEpisodeConfig,
)
from experiments.clinical_transfer.adapter import ClinicalDEICAdapter
from deic_core import FixedPartitionGenerator


BUDGETS = [8, 12, 16, 20]
N = 100


class FixedClinicalAnomalyConfig(ClinicalEpisodeConfig):
    """Clinical closest structural mismatch harness with fixed true group size."""

    def __init__(self, seed, group_size, n_patients=8):
        rng = random.Random(seed)
        self.patients = ClinicalEpisodeConfig(seed, n_patients=n_patients).patients
        self.baseline_vitals = {p: rng.randint(60, 120) for p in self.patients}
        shuffled = list(self.patients)
        rng.shuffle(shuffled)
        self.deteriorating = shuffled[:group_size]
        self.stable = shuffled[group_size:]
        self.severity = rng.choice([1.3, 1.8, 2.5])
        from experiments.clinical_transfer.environment import STATION_NAMES
        self.faulty_station = rng.choice(STATION_NAMES)
        self.max_queries = 8
        self.seed = seed


def generate_clinical_anomaly_episodes(n, group_size, seed_offset):
    return [FixedClinicalAnomalyConfig(seed_offset + i, group_size=group_size) for i in range(n)]


def _extract_correct(res):
    if "correct" in res:
        return bool(res.get("correct"))
    if "consensus_reached" in res:
        return bool(res.get("consensus_reached"))
    return False


def run_env_episodes(episodes, env_cls, adapter, true_gs=None):
    total = len(episodes)
    triggered = correct_family_adoptions = correct = escalated = wrong_commits = commits = 0
    recovered_post_adaptation = 0
    for cfg in episodes:
        env = env_cls(cfg)
        out = adapter.diagnose(env) if hasattr(adapter, "diagnose") else adapter.solve(env)[1]
        ws = out.get("final_workspace", {})
        did_trigger = ws.get("adaptation_count", 0) > 0
        if did_trigger:
            triggered += 1
            if true_gs is not None and ws.get("family_search_outcome") == "adopted" and f"gs={true_gs}" in ws.get("current_family_spec", ""):
                correct_family_adoptions += 1
        is_escalated = bool(out.get("escalated"))
        if is_escalated:
            escalated += 1
        else:
            commits += 1
            if _extract_correct(out):
                correct += 1
                if did_trigger:
                    recovered_post_adaptation += 1
            else:
                wrong_commits += 1
    return {
        "trigger_rate": round(triggered / total, 4),
        "correct_family_adoption_rate": round(correct_family_adoptions / total, 4) if true_gs is not None else None,
        "final_accuracy": round(correct / total, 4),
        "escalation_rate": round(escalated / total, 4),
        "wrong_commit_rate": round(wrong_commits / total, 4),
        "post_adaptation_recovery_rate": round(recovered_post_adaptation / total, 4),
        "commit_coverage": round(commits / total, 4),
    }


def run_c6_standard(adapter, budget):
    episodes = generate_episodes(N, condition="c6_hidden_structure", seed_offset=700000)
    for ep in episodes:
        ep.max_turns = budget
    return run_env_episodes(episodes, ProceduralEnvironment, adapter, true_gs=4)


def main():
    results = {"before": {}, "after": {}}

    configs = {
        "before": {
            "cyber": CyberDEICAdapter(
                use_planner=True,
                confidence_threshold=0.999,
                coverage_threshold=1.0,
                enable_adapt_refine=False,
                enable_final_contradiction_probe=False,
            ),
            "clinical": ClinicalDEICAdapter(
                use_planner=True,
                confidence_threshold=0.999,
                coverage_threshold=1.0,
                enable_adapt_refine=False,
                enable_final_contradiction_probe=False,
                hypothesis_generator=FixedPartitionGenerator(group_size=4, multipliers=[1.3, 1.8, 2.5]),
            ),
            "benchmark": DEICBenchmarkAdapter(
                use_planner=True,
                confidence_threshold=0.999,
                enable_adapt_refine=False,
                enable_final_contradiction_probe=False,
            ),
        },
        "after": {
            "cyber": CyberDEICAdapter(
                use_planner=True,
                confidence_threshold=0.999,
                coverage_threshold=1.0,
                enable_adapt_refine=True,
                enable_final_contradiction_probe=False,
            ),
            "clinical": ClinicalDEICAdapter(
                use_planner=True,
                confidence_threshold=0.999,
                coverage_threshold=1.0,
                enable_adapt_refine=True,
                enable_final_contradiction_probe=False,
                hypothesis_generator=FixedPartitionGenerator(group_size=4, multipliers=[1.3, 1.8, 2.5]),
            ),
            "benchmark": DEICBenchmarkAdapter(
                use_planner=True,
                confidence_threshold=0.999,
                enable_adapt_refine=True,
                enable_final_contradiction_probe=False,
            ),
        },
    }

    for label, adapter_set in configs.items():
        results[label]["cyber_gs3"] = {}
        results[label]["cyber_gs5"] = {}
        results[label]["clinical_gs3"] = {}
        results[label]["clinical_gs5"] = {}
        results[label]["cyber_gs4_baseline"] = {}
        results[label]["c6_standard"] = {}
        for budget in BUDGETS:
            cyber3 = generate_anomaly_episodes(N, group_size=3, seed_offset=8000)
            for ep in cyber3:
                ep.max_queries = budget
            results[label]["cyber_gs3"][str(budget)] = run_env_episodes(cyber3, CyberIncidentEnvironment, adapter_set["cyber"], true_gs=3)

            cyber5 = generate_anomaly_episodes(N, group_size=5, seed_offset=7000)
            for ep in cyber5:
                ep.max_queries = budget
            results[label]["cyber_gs5"][str(budget)] = run_env_episodes(cyber5, CyberIncidentEnvironment, adapter_set["cyber"], true_gs=5)

            clin3 = generate_clinical_anomaly_episodes(N, group_size=3, seed_offset=81000)
            for ep in clin3:
                ep.max_queries = budget
            results[label]["clinical_gs3"][str(budget)] = run_env_episodes(clin3, ClinicalEnvironment, adapter_set["clinical"], true_gs=3)

            clin5 = generate_clinical_anomaly_episodes(N, group_size=5, seed_offset=91000)
            for ep in clin5:
                ep.max_queries = budget
            results[label]["clinical_gs5"][str(budget)] = run_env_episodes(clin5, ClinicalEnvironment, adapter_set["clinical"], true_gs=5)

            gs4 = generate_cyber_episodes(N, seed_offset=2000)
            for ep in gs4:
                ep.max_queries = budget
            results[label]["cyber_gs4_baseline"][str(budget)] = run_env_episodes(gs4, CyberIncidentEnvironment, adapter_set["cyber"], true_gs=4)

            results[label]["c6_standard"][str(budget)] = run_c6_standard(adapter_set["benchmark"], budget)

    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
