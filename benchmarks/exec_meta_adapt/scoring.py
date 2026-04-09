import json
from dataclasses import asdict
from statistics import mean
from typing import Dict, Iterable, List, Optional

from benchmarks.exec_meta_adapt.schemas import (
    ANOMALY_TASK_CLASSES,
    BASELINE_TASK_CLASSES,
    CONTRACT_VERSION,
    DEFAULT_SUITE_NAME,
    TRANSFER_TASK_CLASSES,
    EpisodeResult,
    TaskAggregate,
)


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
    if task_class in ("standard_inference", "adversarial_trust", "heldout_transfer", "budget_noise_stress"):
        return adaptation_count > 0
    return False


def average_or_none(values: Iterable[Optional[int]]) -> Optional[float]:
    filtered = [v for v in values if v is not None]
    if not filtered:
        return None
    return round(mean(filtered), 4)


def flatten_episode_results(results_by_task: Dict[str, List[EpisodeResult]]) -> List[EpisodeResult]:
    flattened = []
    for task_name in sorted(results_by_task):
        flattened.extend(results_by_task[task_name])
    return flattened


def filter_episode_results(
    results: List[EpisodeResult],
    *,
    task_classes: Optional[Iterable[str]] = None,
    domain: Optional[str] = None,
    adapter_variant: Optional[str] = None,
) -> List[EpisodeResult]:
    allowed_classes = set(task_classes) if task_classes is not None else None
    filtered = []
    for result in results:
        if allowed_classes is not None and result.task_class not in allowed_classes:
            continue
        if domain is not None and result.domain != domain:
            continue
        if adapter_variant is not None and result.adapter_variant != adapter_variant:
            continue
        filtered.append(result)
    return filtered


def _metrics_from_results(results: List[EpisodeResult]) -> Dict[str, Optional[float]]:
    if not results:
        return {
            "n_episodes": 0,
            "final_accuracy": 0.0,
            "accuracy_on_commit": 0.0,
            "abstention_rate": 0.0,
            "silent_failure_rate": 0.0,
            "false_adaptation_rate": 0.0,
            "avg_trust_lock_turn": None,
            "contradiction_trigger_rate": 0.0,
            "adaptation_trigger_rate": 0.0,
            "post_adaptation_recovery_rate": 0.0,
            "planner_trace_availability": 0.0,
            "self_model_snapshot_availability": 0.0,
            "explanation_trace_availability": 0.0,
        }

    committed = [r for r in results if r.committed]
    adapted = [r for r in results if r.adaptation_trigger_turn is not None]
    contradiction_hits = [r for r in results if r.contradiction_trigger_turn is not None]

    return {
        "n_episodes": len(results),
        "final_accuracy": round(mean(r.accuracy for r in results), 4),
        "accuracy_on_commit": round(mean(r.accuracy for r in committed), 4) if committed else 0.0,
        "abstention_rate": round(mean(1.0 if r.abstained else 0.0 for r in results), 4),
        "silent_failure_rate": round(mean(1.0 if r.silent_failure else 0.0 for r in results), 4),
        "false_adaptation_rate": round(mean(1.0 if r.false_adaptation else 0.0 for r in results), 4),
        "avg_trust_lock_turn": average_or_none(r.trust_lock_turn for r in results),
        "contradiction_trigger_rate": round(len(contradiction_hits) / len(results), 4),
        "adaptation_trigger_rate": round(len(adapted) / len(results), 4),
        "post_adaptation_recovery_rate": round(mean(r.accuracy for r in adapted), 4) if adapted else 0.0,
        "planner_trace_availability": round(mean(1.0 if r.planner_trace_available else 0.0 for r in results), 4),
        "self_model_snapshot_availability": round(
            mean(1.0 if r.self_model_snapshot_available else 0.0 for r in results), 4
        ),
        "explanation_trace_availability": round(
            mean(1.0 if r.explanation_trace_available else 0.0 for r in results), 4
        ),
    }


def aggregate_episode_results(results: List[EpisodeResult]) -> TaskAggregate:
    metrics = _metrics_from_results(results)
    return TaskAggregate(
        task_name=results[0].task_name,
        domain=results[0].domain,
        task_class=results[0].task_class,
        split=results[0].split,
        adapter_variant=results[0].adapter_variant,
        n_episodes=metrics["n_episodes"],
        final_accuracy=metrics["final_accuracy"],
        accuracy_on_commit=metrics["accuracy_on_commit"],
        abstention_rate=metrics["abstention_rate"],
        silent_failure_rate=metrics["silent_failure_rate"],
        false_adaptation_rate=metrics["false_adaptation_rate"],
        avg_trust_lock_turn=metrics["avg_trust_lock_turn"],
        contradiction_trigger_rate=metrics["contradiction_trigger_rate"],
        adaptation_trigger_rate=metrics["adaptation_trigger_rate"],
        post_adaptation_recovery_rate=metrics["post_adaptation_recovery_rate"],
        planner_trace_availability=metrics["planner_trace_availability"],
        self_model_snapshot_availability=metrics["self_model_snapshot_availability"],
        explanation_trace_availability=metrics["explanation_trace_availability"],
    )


def build_summary_rows(train_results: List[EpisodeResult], heldout_results: List[EpisodeResult]) -> List[Dict[str, Optional[float]]]:
    cohorts = [
        ("baseline_train", filter_episode_results(train_results, task_classes=BASELINE_TASK_CLASSES)),
        ("anomaly_train", filter_episode_results(train_results, task_classes=ANOMALY_TASK_CLASSES)),
        ("heldout_transfer", filter_episode_results(heldout_results, task_classes=TRANSFER_TASK_CLASSES)),
        ("full_package", train_results + heldout_results),
    ]
    rows = []
    for cohort_name, episodes in cohorts:
        metrics = _metrics_from_results(episodes)
        metrics["cohort"] = cohort_name
        rows.append(metrics)
    return rows


def build_domain_rows(train_results: List[EpisodeResult], heldout_results: List[EpisodeResult]) -> List[Dict[str, Optional[float]]]:
    rows = []
    for domain in ("benchmark", "cyber", "clinical"):
        baseline = _metrics_from_results(
            filter_episode_results(train_results, task_classes=BASELINE_TASK_CLASSES, domain=domain)
        )
        anomaly = _metrics_from_results(
            filter_episode_results(train_results, task_classes=ANOMALY_TASK_CLASSES, domain=domain)
        )
        heldout = _metrics_from_results(
            filter_episode_results(heldout_results, task_classes=TRANSFER_TASK_CLASSES, domain=domain)
        )
        overall = _metrics_from_results(
            filter_episode_results(train_results + heldout_results, domain=domain)
        )
        rows.append(
            {
                "domain": domain,
                "baseline_accuracy": baseline["final_accuracy"],
                "anomaly_accuracy": anomaly["final_accuracy"],
                "heldout_accuracy": heldout["final_accuracy"],
                "abstention_rate": overall["abstention_rate"],
                "silent_failure_rate": overall["silent_failure_rate"],
                "false_adaptation_rate": overall["false_adaptation_rate"],
                "planner_trace_availability": overall["planner_trace_availability"],
            }
        )
    return rows


def build_ablation_rows(variant_summaries: List[Dict[str, Optional[float]]]) -> List[Dict[str, Optional[float]]]:
    frozen_full = next((row for row in variant_summaries if row["adapter_variant"] == "frozen_full"), None)
    baseline_accuracy = frozen_full["final_accuracy"] if frozen_full else 0.0
    rows = []
    for summary in variant_summaries:
        row = dict(summary)
        row["delta_vs_frozen_full"] = round(row["final_accuracy"] - baseline_accuracy, 4)
        rows.append(row)
    return rows


def _trace_priority(result: EpisodeResult) -> tuple:
    class_order = {
        "adaptive_mismatch": 0,
        "budget_noise_stress": 1,
        "adversarial_trust": 2,
        "heldout_transfer": 3,
        "standard_inference": 4,
    }
    split_order = {"train": 0, "heldout": 1}
    return (
        class_order.get(result.task_class, 99),
        split_order.get(result.split, 99),
        result.domain,
        result.seed,
    )


def select_trace_examples(
    train_results: List[EpisodeResult],
    heldout_results: List[EpisodeResult],
    limit: int = 3,
) -> List[Dict[str, str]]:
    candidates = sorted(
        [result for result in train_results + heldout_results if result.planner_trace],
        key=_trace_priority,
    )
    selected = []
    covered_domains = set()
    for result in candidates:
        if result.domain in covered_domains and len(selected) + (3 - len(covered_domains)) >= limit:
            continue
        planner_modes = [
            entry.get("planner_mode", entry.get("action", {}).get("type", "UNKNOWN"))
            for entry in result.planner_trace[:6]
        ]
        selected.append(
            {
                "domain": result.domain,
                "task_class": result.task_class,
                "split": result.split,
                "seed": str(result.seed),
                "final_status": result.final_status,
                "planner_modes": " -> ".join(planner_modes),
                "explanation_excerpt": (result.explanation_trace or ["no explanation trace"])[0][:240],
            }
        )
        covered_domains.add(result.domain)
        if len(selected) >= limit:
            break
    return selected


def _format_number(value: Optional[float]) -> str:
    if value is None:
        return "-"
    if isinstance(value, int):
        return str(value)
    return f"{value:.2f}"


def render_markdown_report(
    train_metadata: Dict[str, str],
    heldout_metadata: Dict[str, str],
    summary_rows: List[Dict[str, Optional[float]]],
    domain_rows: List[Dict[str, Optional[float]]],
    ablation_rows: List[Dict[str, Optional[float]]],
    trace_examples: List[Dict[str, str]],
    verdict: str,
) -> str:
    lines = [
        "# DEIC-CogBench v1 Report",
        "",
        "## Contract",
        "",
        f"- contract_version: `{CONTRACT_VERSION}`",
        f"- suite_name: `{DEFAULT_SUITE_NAME}`",
        f"- train_split: `{train_metadata['split_file']}`",
        f"- heldout_split: `{heldout_metadata['split_file']}`",
        f"- train_tasks: `{train_metadata['task_count']}`",
        f"- heldout_tasks: `{heldout_metadata['task_count']}`",
        "",
        "## Summary Table",
        "",
        "| Cohort | Episodes | Final Acc | Commit Acc | Abstain | Silent Failure | False Adapt | Adapt Trigger |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in summary_rows:
        lines.append(
            f"| {row['cohort']} | {row['n_episodes']} | {_format_number(row['final_accuracy'])} | "
            f"{_format_number(row['accuracy_on_commit'])} | {_format_number(row['abstention_rate'])} | "
            f"{_format_number(row['silent_failure_rate'])} | {_format_number(row['false_adaptation_rate'])} | "
            f"{_format_number(row['adaptation_trigger_rate'])} |"
        )

    lines.extend(
        [
            "",
            "## Per-Domain Table",
            "",
            "| Domain | Baseline Acc | Anomaly Acc | Held-out Acc | Abstain | Silent Failure | False Adapt | Trace Avail |",
            "|---|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for row in domain_rows:
        lines.append(
            f"| {row['domain']} | {_format_number(row['baseline_accuracy'])} | {_format_number(row['anomaly_accuracy'])} | "
            f"{_format_number(row['heldout_accuracy'])} | {_format_number(row['abstention_rate'])} | "
            f"{_format_number(row['silent_failure_rate'])} | {_format_number(row['false_adaptation_rate'])} | "
            f"{_format_number(row['planner_trace_availability'])} |"
        )

    lines.extend(
        [
            "",
            "## Ablation Table",
            "",
            "| Variant | Episodes | Final Acc | Delta vs Full | Commit Acc | Abstain | Silent Failure | False Adapt |",
            "|---|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for row in ablation_rows:
        lines.append(
            f"| {row['adapter_variant']} | {row['n_episodes']} | {_format_number(row['final_accuracy'])} | "
            f"{_format_number(row['delta_vs_frozen_full'])} | {_format_number(row['accuracy_on_commit'])} | "
            f"{_format_number(row['abstention_rate'])} | {_format_number(row['silent_failure_rate'])} | "
            f"{_format_number(row['false_adaptation_rate'])} |"
        )

    lines.extend(["", "## Trace Examples", ""])
    if not trace_examples:
        lines.append("- No trace examples were available for this run.")
    else:
        for index, trace in enumerate(trace_examples, start=1):
            lines.extend(
                [
                    f"### Trace {index}",
                    "",
                    f"- domain: `{trace['domain']}`",
                    f"- task_class: `{trace['task_class']}`",
                    f"- split: `{trace['split']}`",
                    f"- seed: `{trace['seed']}`",
                    f"- final_status: `{trace['final_status']}`",
                    f"- planner_modes: `{trace['planner_modes']}`",
                    f"- explanation_excerpt: `{trace['explanation_excerpt']}`",
                    "",
                ]
            )

    lines.extend(
        [
            "## Verdict",
            "",
            f"- {verdict}",
            "",
            "## Notes",
            "",
            "- Silent failure is first-class and remains distinct from escalation.",
            "- Baseline and anomaly cohorts are reported separately rather than blended.",
            "- Held-out transfer remains an explicit split, not an in-place seed reuse trick.",
            "- Ablations stay on the frozen architecture surface and do not reopen core inference design.",
        ]
    )
    return "\n".join(lines) + "\n"


def serialize_package_run(payload: Dict[str, object]) -> str:
    def _json_default(value):
        if isinstance(value, (set, frozenset)):
            return sorted(value)
        raise TypeError(f"Object of type {value.__class__.__name__} is not JSON serializable")

    return json.dumps(payload, indent=2, default=_json_default)


def summarize_variant_results(adapter_variant: str, results: List[EpisodeResult]) -> Dict[str, Optional[float]]:
    summary = _metrics_from_results(results)
    summary["adapter_variant"] = adapter_variant
    return summary


def task_aggregates_to_dicts(task_aggregates: List[TaskAggregate]) -> List[Dict[str, object]]:
    return [asdict(aggregate) for aggregate in task_aggregates]
