"""
Focused validation for the post-adaptation guarded untouched-item probe.

Compares the frozen bounded-adaptive planner against a variant that adds
one post-adaptation probe when the adapted family is saturated and
untouched items remain.
"""

from __future__ import annotations

import argparse
import json
import os
import random
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, PROJECT_ROOT)
sys.path.insert(0, os.path.join(PROJECT_ROOT, "benchmark"))

from benchmark.deic_adapter import DEICBenchmarkAdapter
from benchmark.environment import ProceduralEnvironment, generate_episodes
from experiments.cyber_transfer.adapter import CyberDEICAdapter
from experiments.cyber_transfer.environment import CyberIncidentEnvironment, generate_cyber_episodes
from experiments.structure_anomaly import generate_anomaly_episodes
from experiments.clinical_transfer.adapter import ClinicalDEICAdapter
from experiments.clinical_transfer.environment import (
    ClinicalEnvironment,
    ClinicalEpisodeConfig,
    STATION_NAMES,
)
from deic_core import FixedPartitionGenerator


@dataclass(frozen=True)
class ValidationCase:
    name: str
    domain: str
    budget: int
    true_gs: int
    task_class: str


class FixedClinicalAnomalyConfig(ClinicalEpisodeConfig):
    def __init__(self, seed: int, group_size: int, n_patients: int = 8):
        rng = random.Random(seed)
        self.patients = ClinicalEpisodeConfig(seed, n_patients=n_patients).patients
        self.baseline_vitals = {p: rng.randint(60, 120) for p in self.patients}
        shuffled = list(self.patients)
        rng.shuffle(shuffled)
        self.deteriorating = shuffled[:group_size]
        self.stable = shuffled[group_size:]
        self.severity = rng.choice([1.3, 1.8, 2.5])
        self.faulty_station = rng.choice(STATION_NAMES)
        self.max_queries = 8
        self.seed = seed


def generate_clinical_anomaly_episodes(n: int, group_size: int, seed_offset: int) -> List[FixedClinicalAnomalyConfig]:
    return [FixedClinicalAnomalyConfig(seed_offset + i, group_size=group_size) for i in range(n)]


def compute_silent_failure(committed: bool, abstained: bool, confidence_margin: float, threshold: float = 0.95) -> bool:
    if abstained or not committed:
        return False
    return confidence_margin < threshold


def _extract_correct(result: Dict[str, Any]) -> bool:
    if "correct" in result:
        return bool(result.get("correct"))
    if "consensus_reached" in result:
        return bool(result.get("consensus_reached"))
    return False


def _make_cases(budgets: Iterable[int]) -> List[ValidationCase]:
    cases: List[ValidationCase] = []
    for budget in budgets:
        cases.extend(
            [
                ValidationCase(f"cyber_gs4_b{budget}", "cyber", budget, 4, "standard_inference"),
                ValidationCase(f"c6_standard_b{budget}", "benchmark", budget, 4, "standard_inference"),
                ValidationCase(f"cyber_gs5_b{budget}", "cyber", budget, 5, "adaptive_mismatch"),
                ValidationCase(f"cyber_gs7_b{budget}", "cyber", budget, 7, "adaptive_mismatch"),
                ValidationCase(f"clinical_gs5_b{budget}", "clinical", budget, 5, "adaptive_mismatch"),
                ValidationCase(f"clinical_gs7_b{budget}", "clinical", budget, 7, "adaptive_mismatch"),
            ]
        )
    return cases


def _episodes_for_case(case: ValidationCase, n_episodes: int):
    if case.domain == "benchmark":
        episodes = generate_episodes(n_episodes, condition="c6_hidden_structure", seed_offset=700000)
        for ep in episodes:
            ep.max_turns = case.budget
        return episodes, ProceduralEnvironment
    if case.domain == "cyber":
        if case.true_gs == 4:
            episodes = generate_cyber_episodes(n_episodes, seed_offset=2000)
        else:
            seed_offset = {5: 7000, 7: 5000}[case.true_gs]
            episodes = generate_anomaly_episodes(n_episodes, group_size=case.true_gs, seed_offset=seed_offset)
        for ep in episodes:
            ep.max_queries = case.budget
        return episodes, CyberIncidentEnvironment
    episodes = generate_clinical_anomaly_episodes(n_episodes, group_size=case.true_gs, seed_offset={5: 91000, 7: 111000}[case.true_gs])
    for ep in episodes:
        ep.max_queries = case.budget
    return episodes, ClinicalEnvironment


def _make_adapters(enable_guarded_probe: bool) -> Dict[str, Any]:
    return {
        "benchmark": DEICBenchmarkAdapter(
            use_planner=True,
            confidence_threshold=0.999,
            enable_adapt_refine=True,
            enable_final_contradiction_probe=True,
            enable_post_adaptation_guarded_probe=enable_guarded_probe,
        ),
        "cyber": CyberDEICAdapter(
            use_planner=True,
            confidence_threshold=0.999,
            coverage_threshold=1.0,
            enable_adapt_refine=True,
            enable_final_contradiction_probe=True,
            enable_post_adaptation_guarded_probe=enable_guarded_probe,
        ),
        "clinical": ClinicalDEICAdapter(
            use_planner=True,
            confidence_threshold=0.999,
            coverage_threshold=1.0,
            enable_adapt_refine=True,
            enable_final_contradiction_probe=True,
            enable_post_adaptation_guarded_probe=enable_guarded_probe,
            hypothesis_generator=FixedPartitionGenerator(group_size=4, multipliers=[1.3, 1.8, 2.5]),
        ),
    }


def _run_episode(adapter, env_cls, cfg) -> Dict[str, Any]:
    env = env_cls(cfg)
    if hasattr(adapter, "diagnose"):
        result = adapter.diagnose(env)
    else:
        _, result = adapter.solve(env)
    return result


def _aggregate_case(case: ValidationCase, results: List[Dict[str, Any]]) -> Dict[str, Any]:
    total = len(results)
    correct = 0
    escalated = 0
    wrong_commit = 0
    wrong_commit_after_adaptation = 0
    false_adaptation = 0
    silent_failure = 0
    post_probe = 0
    contradiction_after_probe = 0
    for result in results:
        ws = result.get("final_workspace", {})
        is_correct = _extract_correct(result)
        is_escalated = bool(result.get("escalated"))
        is_committed = not is_escalated
        if is_correct:
            correct += 1
        if is_escalated:
            escalated += 1
        elif not is_correct:
            wrong_commit += 1
            if ws.get("adaptation_count", 0) > 0:
                wrong_commit_after_adaptation += 1
        if ws.get("post_adaptation_probe_count", 0) > 0:
            post_probe += 1
        if ws.get("contradiction_after_post_adaptation_probe", False):
            contradiction_after_probe += 1
        if case.true_gs == 4:
            false_adaptation += int(ws.get("adaptation_count", 0) > 0)
        elif ws.get("adaptation_count", 0) > 0:
            false_adaptation += int(f"gs={case.true_gs}" not in ws.get("current_family_spec", ""))
        silent_failure += int(
            compute_silent_failure(
                committed=is_committed,
                abstained=bool(result.get("abstained")),
                confidence_margin=float(ws.get("confidence_margin", 0.0)),
            )
        )
    return {
        "domain": case.domain,
        "budget": case.budget,
        "true_gs": case.true_gs,
        "task_class": case.task_class,
        "episodes": total,
        "final_accuracy": round(correct / total, 4),
        "wrong_commit_rate": round(wrong_commit / total, 4),
        "wrong_commit_after_adaptation_rate": round(wrong_commit_after_adaptation / total, 4),
        "escalation_rate": round(escalated / total, 4),
        "false_adaptation_rate": round(false_adaptation / total, 4),
        "silent_failure_rate": round(silent_failure / total, 4),
        "post_adaptation_probe_rate": round(post_probe / total, 4),
        "contradiction_after_probe_rate": round(contradiction_after_probe / total, 4),
    }


def run_validation(n_episodes: int, budgets: Iterable[int]) -> Dict[str, Any]:
    cases = _make_cases(budgets)
    configs = {
        "before": _make_adapters(enable_guarded_probe=False),
        "after": _make_adapters(enable_guarded_probe=True),
    }
    results: Dict[str, Dict[str, Any]] = {label: {} for label in configs}
    for label, adapters in configs.items():
        for case in cases:
            episodes, env_cls = _episodes_for_case(case, n_episodes)
            case_results = []
            for cfg in episodes:
                case_results.append(_run_episode(adapters[case.domain], env_cls, cfg))
            results[label][case.name] = _aggregate_case(case, case_results)

    comparison_rows = []
    for case in cases:
        before = results["before"][case.name]
        after = results["after"][case.name]
        comparison_rows.append(
            {
                "case": case.name,
                "budget": case.budget,
                "before_final_accuracy": before["final_accuracy"],
                "after_final_accuracy": after["final_accuracy"],
                "accuracy_delta": round(after["final_accuracy"] - before["final_accuracy"], 4),
                "before_wrong_commit_rate": before["wrong_commit_rate"],
                "after_wrong_commit_rate": after["wrong_commit_rate"],
                "wrong_commit_delta": round(after["wrong_commit_rate"] - before["wrong_commit_rate"], 4),
                "before_wrong_commit_after_adaptation_rate": before["wrong_commit_after_adaptation_rate"],
                "after_wrong_commit_after_adaptation_rate": after["wrong_commit_after_adaptation_rate"],
                "wrong_commit_after_adaptation_delta": round(
                    after["wrong_commit_after_adaptation_rate"] - before["wrong_commit_after_adaptation_rate"], 4
                ),
                "before_escalation_rate": before["escalation_rate"],
                "after_escalation_rate": after["escalation_rate"],
                "before_false_adaptation_rate": before["false_adaptation_rate"],
                "after_false_adaptation_rate": after["false_adaptation_rate"],
                "before_silent_failure_rate": before["silent_failure_rate"],
                "after_silent_failure_rate": after["silent_failure_rate"],
                "after_post_adaptation_probe_rate": after["post_adaptation_probe_rate"],
                "after_contradiction_after_probe_rate": after["contradiction_after_probe_rate"],
            }
        )

    return {
        "episodes_per_case": n_episodes,
        "budgets": list(budgets),
        "results": results,
        "comparison_rows": comparison_rows,
    }


def render_summary(payload: Dict[str, Any]) -> str:
    lines = [
        "# Post-Adaptation Guarded Probe Validation",
        "",
        f"Episodes per case: {payload['episodes_per_case']}",
        f"Budgets: {payload['budgets']}",
        "",
        "| Case | Before Acc | After Acc | Acc Delta | Before Wrong | After Wrong | Wrong-After-Adapt Delta | Probe Rate | Contradiction After Probe |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in payload["comparison_rows"]:
        lines.append(
            f"| {row['case']} | {row['before_final_accuracy']:.2f} | {row['after_final_accuracy']:.2f} | "
            f"{row['accuracy_delta']:+.2f} | {row['before_wrong_commit_rate']:.2f} | "
            f"{row['after_wrong_commit_rate']:.2f} | {row['wrong_commit_after_adaptation_delta']:+.2f} | "
            f"{row['after_post_adaptation_probe_rate']:.2f} | {row['after_contradiction_after_probe_rate']:.2f} |"
        )
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate the post-adaptation guarded probe.")
    parser.add_argument("--episodes", type=int, default=100)
    parser.add_argument("--budgets", type=int, nargs="+", default=[8, 12])
    parser.add_argument(
        "--output",
        type=str,
        default=os.path.join("results", "post_adaptation_guarded_probe", "validation.json"),
    )
    args = parser.parse_args()

    payload = run_validation(args.episodes, args.budgets)
    print(render_summary(payload))
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Saved raw results to {output_path}")


if __name__ == "__main__":
    main()
