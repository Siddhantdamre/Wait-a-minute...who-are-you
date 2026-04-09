import json
from dataclasses import asdict
from statistics import mean
from typing import Dict, Iterable, List, Optional

from benchmarks.exec_meta_adapt.schemas import EpisodeResult, TaskAggregate


def final_status_from_flags(committed: bool, abstained: bool, accuracy: float) -> str:
    if abstained and not committed:
        return "ESCALATED"
    if committed and accuracy >= 1.0:
        return "CORRECT_COMMIT"
    return "WRONG_COMMIT"


def truthy_turn(value: Optional[int]) -> Optional[int]:
    if value is None:
        return None
    return value if value >= 0 else None


def compute_silent_failure(
    committed: bool,
    abstained: bool,
    confidence_margin: Optional[float],
    threshold: float = 0.95,
) -> bool:
    if abstained or not committed:
        return False
    return (confidence_margin or 0.0) < threshold


def compute_false_adaptation(task_class: str, adaptation_count: int) -> bool:
    if task_class in ("standard_inference", "adversarial_trust", "heldout_transfer", "budget_starvation"):
        return adaptation_count > 0
    return False


def average_or_none(values: Iterable[Optional[int]]) -> Optional[float]:
    filtered = [v for v in values if v is not None]
    if not filtered:
        return None
    return round(mean(filtered), 4)


def aggregate_episode_results(results: List[EpisodeResult]) -> TaskAggregate:
    committed = [r for r in results if r.committed]
    adapted = [r for r in results if r.adaptation_trigger_turn is not None]
    contradiction_hits = [r for r in results if r.contradiction_trigger_turn is not None]

    return TaskAggregate(
        task_name=results[0].task_name,
        domain=results[0].domain,
        task_class=results[0].task_class,
        split=results[0].split,
        n_episodes=len(results),
        final_accuracy=round(mean(r.accuracy for r in results), 4),
        accuracy_on_commit=round(mean(r.accuracy for r in committed), 4) if committed else 0.0,
        abstention_rate=round(mean(1.0 if r.abstained else 0.0 for r in results), 4),
        silent_failure_rate=round(mean(1.0 if r.silent_failure else 0.0 for r in results), 4),
        false_adaptation_rate=round(mean(1.0 if r.false_adaptation else 0.0 for r in results), 4),
        avg_trust_lock_turn=average_or_none(r.trust_lock_turn for r in results),
        contradiction_trigger_rate=round(len(contradiction_hits) / len(results), 4),
        adaptation_trigger_rate=round(len(adapted) / len(results), 4),
        post_adaptation_recovery_rate=round(mean(r.accuracy for r in adapted), 4) if adapted else 0.0,
        planner_trace_availability=round(mean(1.0 if r.planner_trace_available else 0.0 for r in results), 4),
        self_model_snapshot_availability=round(
            mean(1.0 if r.self_model_snapshot_available else 0.0 for r in results), 4
        ),
        explanation_trace_availability=round(
            mean(1.0 if r.explanation_trace_available else 0.0 for r in results), 4
        ),
    )


def render_markdown_report(split_name: str, task_aggregates: List[TaskAggregate], suite_metadata: Dict[str, str]) -> str:
    lines = ["# DEIC-CogBench v1 Report", "", f"Split: `{split_name}`", "", "## Run Metadata", ""]
    for key, value in suite_metadata.items():
        lines.append(f"- {key}: `{value}`")

    lines.extend(
        [
            "",
            "## Task Summary",
            "",
            "| Task | Domain | Class | Episodes | Final Acc | Commit Acc | Abstain | Silent Failure | False Adapt | Adapt Trigger |",
            "|---|---|---|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for agg in task_aggregates:
        lines.append(
            f"| {agg.task_name} | {agg.domain} | {agg.task_class} | {agg.n_episodes} | "
            f"{agg.final_accuracy:.2f} | {agg.accuracy_on_commit:.2f} | {agg.abstention_rate:.2f} | "
            f"{agg.silent_failure_rate:.2f} | {agg.false_adaptation_rate:.2f} | {agg.adaptation_trigger_rate:.2f} |"
        )

    lines.extend(
        [
            "",
            "## Notes",
            "",
            "- Silent failure is reported explicitly and remains distinct from escalation.",
            "- Standard and anomaly-style tasks are reported separately by task class.",
            "- Trace availability metrics reflect what the current frozen adapters expose today.",
        ]
    )
    return "\n".join(lines) + "\n"


def serialize_run(
    split_name: str,
    suite_metadata: Dict[str, str],
    task_aggregates: List[TaskAggregate],
    episode_results: Dict[str, List[EpisodeResult]],
) -> str:
    payload = {
        "split": split_name,
        "metadata": suite_metadata,
        "task_aggregates": [asdict(agg) for agg in task_aggregates],
        "episodes": {
            task_name: [episode.to_dict() for episode in task_results]
            for task_name, task_results in episode_results.items()
        },
    }
    return json.dumps(payload, indent=2)
