"""
Focused analysis for surfaced contradictions that still end in escalation.

This uses the guarded post-adaptation probe path and asks a narrower
question than the earlier validation harness:

When contradiction is surfaced on hard gs=7 cases, why does recovery still
fail to produce a correct commit?
"""

from __future__ import annotations

import argparse
import json
import os
import random
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, PROJECT_ROOT)
sys.path.insert(0, os.path.join(PROJECT_ROOT, "benchmark"))

from benchmark.deic_adapter import DEICBenchmarkAdapter
from benchmark.environment import ProceduralEnvironment, generate_episodes
from deic_core import FixedPartitionGenerator
from experiments.clinical_transfer.adapter import ClinicalDEICAdapter
from experiments.clinical_transfer.environment import (
    ClinicalEnvironment,
    ClinicalEpisodeConfig,
    STATION_NAMES,
)
from experiments.cyber_transfer.adapter import CyberDEICAdapter
from experiments.cyber_transfer.environment import CyberIncidentEnvironment, generate_cyber_episodes
from experiments.structure_anomaly import generate_anomaly_episodes


@dataclass(frozen=True)
class AnalysisCase:
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


def _make_cases(budgets: Iterable[int]) -> List[AnalysisCase]:
    cases: List[AnalysisCase] = []
    for budget in budgets:
        cases.extend(
            [
                AnalysisCase(f"cyber_gs4_b{budget}", "cyber", budget, 4, "standard_inference"),
                AnalysisCase(f"c6_standard_b{budget}", "benchmark", budget, 4, "standard_inference"),
                AnalysisCase(f"cyber_gs7_b{budget}", "cyber", budget, 7, "adaptive_mismatch"),
                AnalysisCase(f"clinical_gs7_b{budget}", "clinical", budget, 7, "adaptive_mismatch"),
            ]
        )
    return cases


def _episodes_for_case(case: AnalysisCase, n_episodes: int):
    if case.domain == "benchmark":
        episodes = generate_episodes(n_episodes, condition="c6_hidden_structure", seed_offset=700000)
        for ep in episodes:
            ep.max_turns = case.budget
        return episodes, ProceduralEnvironment
    if case.domain == "cyber":
        if case.true_gs == 4:
            episodes = generate_cyber_episodes(n_episodes, seed_offset=2000)
        else:
            episodes = generate_anomaly_episodes(n_episodes, group_size=case.true_gs, seed_offset=5000 if case.budget == 8 else 50100)
        for ep in episodes:
            ep.max_queries = case.budget
        return episodes, CyberIncidentEnvironment
    episodes = generate_clinical_anomaly_episodes(
        n_episodes,
        group_size=case.true_gs,
        seed_offset=111000 if case.budget == 8 else 112000,
    )
    for ep in episodes:
        ep.max_queries = case.budget
    return episodes, ClinicalEnvironment


def _make_adapters() -> Dict[str, Any]:
    return {
        "benchmark": DEICBenchmarkAdapter(
            use_planner=True,
            confidence_threshold=0.999,
            enable_adapt_refine=True,
            enable_final_contradiction_probe=True,
            enable_post_adaptation_guarded_probe=True,
        ),
        "cyber": CyberDEICAdapter(
            use_planner=True,
            confidence_threshold=0.999,
            coverage_threshold=1.0,
            enable_adapt_refine=True,
            enable_final_contradiction_probe=True,
            enable_post_adaptation_guarded_probe=True,
        ),
        "clinical": ClinicalDEICAdapter(
            use_planner=True,
            confidence_threshold=0.999,
            coverage_threshold=1.0,
            enable_adapt_refine=True,
            enable_final_contradiction_probe=True,
            enable_post_adaptation_guarded_probe=True,
            hypothesis_generator=FixedPartitionGenerator(group_size=4, multipliers=[1.3, 1.8, 2.5]),
        ),
    }


def _run_episode(adapter, env_cls, cfg) -> Dict[str, Any]:
    env = env_cls(cfg)
    if hasattr(adapter, "diagnose"):
        return adapter.diagnose(env)
    _, result = adapter.solve(env)
    return result


def _extract_correct(result: Dict[str, Any]) -> bool:
    if "correct" in result:
        return bool(result.get("correct"))
    return bool(result.get("consensus_reached"))


def _top_counter_label(counter: Counter[str]) -> str:
    if not counter:
        return ""
    label, count = counter.most_common(1)[0]
    return f"{label}:{count}"


def _trace_tail(trace: List[Dict[str, Any]], limit: int = 6) -> List[str]:
    tail = trace[-limit:]
    rendered = []
    for step in tail:
        planner_mode = step.get("planner_mode", "")
        action = step.get("action", {})
        rendered.append(f"{planner_mode}:{action.get('type', '')}")
    return rendered


def _aggregate_case(case: AnalysisCase, results: List[Dict[str, Any]]) -> Dict[str, Any]:
    total = len(results)
    accuracy = 0
    escalation = 0
    surfaced = 0
    recovery_started = 0
    family_proposal_opened = 0
    blocker_counts: Counter[str] = Counter()
    path_counts: Counter[str] = Counter()
    outcome_counts: Counter[str] = Counter()
    trace_examples: List[Dict[str, Any]] = []

    for result in results:
        ws = result.get("final_workspace", {})
        correct = _extract_correct(result)
        if correct:
            accuracy += 1
        if result.get("escalated"):
            escalation += 1
        if ws.get("contradiction_surface_turn", -1) >= 0:
            surfaced += 1
        if ws.get("recovery_attempt_started", False):
            recovery_started += 1
        if ws.get("family_proposal_opened_after_probe", False):
            family_proposal_opened += 1
        blocker = ws.get("recovery_blocker", "")
        if blocker:
            blocker_counts[blocker] += 1
        path = ws.get("recovery_path_taken", "")
        if path:
            path_counts[path] += 1
        outcome = ws.get("final_outcome_category", "")
        if outcome:
            outcome_counts[outcome] += 1
        if result.get("escalated") and ws.get("contradiction_surface_turn", -1) >= 0 and len(trace_examples) < 2:
            trace_examples.append(
                {
                    "final_outcome_category": outcome,
                    "recovery_blocker": blocker,
                    "recovery_path_taken": path,
                    "trace_tail": _trace_tail(result.get("decision_trace", [])),
                }
            )

    return {
        "domain": case.domain,
        "budget": case.budget,
        "true_gs": case.true_gs,
        "task_class": case.task_class,
        "episodes": total,
        "final_accuracy": round(accuracy / total, 4),
        "escalation_rate": round(escalation / total, 4),
        "contradiction_surface_rate": round(surfaced / total, 4),
        "recovery_attempt_rate": round(recovery_started / total, 4),
        "family_proposal_opened_after_probe_rate": round(family_proposal_opened / total, 4),
        "top_recovery_path": _top_counter_label(path_counts),
        "top_recovery_blocker": _top_counter_label(blocker_counts),
        "top_outcome_category": _top_counter_label(outcome_counts),
        "recovery_path_counts": dict(path_counts),
        "recovery_blocker_counts": dict(blocker_counts),
        "outcome_counts": dict(outcome_counts),
        "trace_examples": trace_examples,
    }


def run_analysis(episodes_per_case: int, budgets: Iterable[int]) -> Dict[str, Any]:
    cases = _make_cases(budgets)
    adapters = _make_adapters()
    results: Dict[str, Any] = {}
    for case in cases:
        episodes, env_cls = _episodes_for_case(case, episodes_per_case)
        case_results = []
        for cfg in episodes:
            case_results.append(_run_episode(adapters[case.domain], env_cls, cfg))
        results[case.name] = _aggregate_case(case, case_results)
    return {
        "episodes_per_case": episodes_per_case,
        "budgets": list(budgets),
        "results": results,
    }


def _print_summary(analysis: Dict[str, Any]) -> None:
    headers = [
        "case",
        "acc",
        "esc",
        "surface",
        "recover",
        "proposal",
        "path",
        "blocker",
    ]
    print("| " + " | ".join(headers) + " |")
    print("|" + "|".join(["---"] * len(headers)) + "|")
    for case_name, row in analysis["results"].items():
        print(
            "| "
            + " | ".join(
                [
                    case_name,
                    f"{row['final_accuracy']:.2f}",
                    f"{row['escalation_rate']:.2f}",
                    f"{row['contradiction_surface_rate']:.2f}",
                    f"{row['recovery_attempt_rate']:.2f}",
                    f"{row['family_proposal_opened_after_probe_rate']:.2f}",
                    row["top_recovery_path"] or "-",
                    row["top_recovery_blocker"] or "-",
                ]
            )
            + " |"
        )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--episodes", type=int, default=100)
    parser.add_argument("--budgets", type=int, nargs="+", default=[8, 12])
    args = parser.parse_args()

    analysis = run_analysis(args.episodes, args.budgets)
    output_dir = Path(PROJECT_ROOT) / "results" / "post_contradiction_recovery_analysis"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "analysis.json"
    output_path.write_text(json.dumps(analysis, indent=2))

    _print_summary(analysis)
    print(f"\nSaved analysis to {output_path}")


if __name__ == "__main__":
    main()
