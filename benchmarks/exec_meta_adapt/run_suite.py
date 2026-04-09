import argparse
import importlib
import json
import os
import sys
from datetime import datetime

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, PROJECT_ROOT)

from benchmarks.exec_meta_adapt.schemas import BenchmarkSplitSpec, CONTRACT_VERSION, DEFAULT_SUITE_NAME
from benchmarks.exec_meta_adapt.scoring import (
    aggregate_episode_results,
    build_ablation_rows,
    build_domain_rows,
    build_summary_rows,
    flatten_episode_results,
    render_markdown_report,
    select_trace_examples,
    serialize_package_run,
    summarize_variant_results,
    task_aggregates_to_dicts,
)
from benchmarks.exec_meta_adapt.tasks import TASK_REGISTRY


DEFAULT_TRAIN_SPLIT = os.path.join(PROJECT_ROOT, "benchmarks", "exec_meta_adapt", "splits", "train_split.yaml")
DEFAULT_HELDOUT_SPLIT = os.path.join(PROJECT_ROOT, "benchmarks", "exec_meta_adapt", "splits", "heldout_split.yaml")
DEFAULT_OUTPUT_DIR = os.path.join(PROJECT_ROOT, "results", "deic_cogbench")


def load_split(path):
    with open(path, "r", encoding="utf-8") as handle:
        payload = json.load(handle)
    split_spec = BenchmarkSplitSpec.from_dict(payload)
    return split_spec


def resolve_task_runner(task_name):
    module = importlib.import_module(TASK_REGISTRY[task_name])
    return module.run_task


def run_split(split_path, include_traces=True, max_tasks=None, max_episodes=None, adapter_variant=None):
    split_spec = load_split(split_path)
    task_specs = list(split_spec.tasks)
    if max_tasks is not None:
        task_specs = task_specs[:max_tasks]

    suite_results = {}
    task_aggregates = []
    for spec in task_specs:
        if max_episodes is not None:
            spec.n_episodes = min(spec.n_episodes, max_episodes)
        if adapter_variant is not None:
            spec.adapter_variant = adapter_variant
        runner = resolve_task_runner(spec.task)
        episode_results = runner(spec, include_traces=include_traces)
        suite_results[f"{spec.task}:{spec.task_class}:{spec.domain}:{spec.adapter_variant}"] = episode_results
        task_aggregates.append(aggregate_episode_results(episode_results))

    metadata = {
        "suite_name": split_spec.suite_name,
        "contract_version": split_spec.contract_version,
        "generated_at_utc": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "split_file": os.path.relpath(split_path, PROJECT_ROOT),
        "split_name": split_spec.split,
        "split_notes": split_spec.notes,
        "task_count": len(task_aggregates),
    }
    return split_spec.split, metadata, task_aggregates, suite_results


def benchmark_verdict(summary_rows, domain_rows, ablation_rows, trace_examples):
    full_row = next((row for row in summary_rows if row["cohort"] == "full_package"), None)
    baseline_row = next((row for row in summary_rows if row["cohort"] == "baseline_train"), None)
    anomaly_row = next((row for row in summary_rows if row["cohort"] == "anomaly_train"), None)
    if (
        full_row
        and baseline_row
        and anomaly_row
        and full_row["silent_failure_rate"] == 0.0
        and len(domain_rows) == 3
        and len(ablation_rows) >= 6
        and len(trace_examples) >= 3
    ):
        return (
            "Externally legible enough for a draft public benchmark share: the contract is frozen, the task families are explicit, "
            "safety is first-class, and the report now reads like a benchmark package rather than an internal experiment folder."
        )
    return (
        "Useful internally, but not yet public-ready: the package still needs fuller coverage, cleaner traces, or stronger ablation visibility "
        "before it will read cleanly to an external benchmark audience."
    )


def build_package_payload(
    train_split_path,
    heldout_split_path,
    include_traces=True,
    max_tasks=None,
    max_episodes=None,
    include_ablations=True,
    trace_limit=3,
):
    train_name, train_metadata, train_task_aggregates, train_suite_results = run_split(
        train_split_path,
        include_traces=include_traces,
        max_tasks=max_tasks,
        max_episodes=max_episodes,
    )
    heldout_name, heldout_metadata, heldout_task_aggregates, heldout_suite_results = run_split(
        heldout_split_path,
        include_traces=include_traces,
        max_tasks=max_tasks,
        max_episodes=max_episodes,
    )

    train_results = flatten_episode_results(train_suite_results)
    heldout_results = flatten_episode_results(heldout_suite_results)
    summary_rows = build_summary_rows(train_results, heldout_results)
    domain_rows = build_domain_rows(train_results, heldout_results)
    trace_examples = select_trace_examples(train_results, heldout_results, limit=trace_limit)

    ablation_payload = None
    ablation_rows = []
    if include_ablations:
        from benchmarks.exec_meta_adapt.run_ablations import run_ablation_suite

        ablation_payload = run_ablation_suite(
            train_split_path,
            max_tasks=max_tasks,
            max_episodes=max_episodes,
            include_traces=include_traces,
        )
        ablation_rows = build_ablation_rows(ablation_payload["summary_rows"])

    verdict = benchmark_verdict(summary_rows, domain_rows, ablation_rows, trace_examples)
    report = render_markdown_report(
        train_metadata,
        heldout_metadata,
        summary_rows,
        domain_rows,
        ablation_rows,
        trace_examples,
        verdict,
    )

    payload = {
        "contract_version": CONTRACT_VERSION,
        "suite_name": DEFAULT_SUITE_NAME,
        "cli_contract": {
            "train_split": os.path.relpath(train_split_path, PROJECT_ROOT),
            "heldout_split": os.path.relpath(heldout_split_path, PROJECT_ROOT),
            "output_dir": os.path.relpath(DEFAULT_OUTPUT_DIR, PROJECT_ROOT),
            "include_traces": include_traces,
            "include_ablations": include_ablations,
            "trace_limit": trace_limit,
            "max_tasks": max_tasks,
            "max_episodes": max_episodes,
        },
        "train": {
            "split": train_name,
            "metadata": train_metadata,
            "task_aggregates": task_aggregates_to_dicts(train_task_aggregates),
            "episodes": {
                task_name: [episode.to_dict() for episode in task_results]
                for task_name, task_results in train_suite_results.items()
            },
        },
        "heldout": {
            "split": heldout_name,
            "metadata": heldout_metadata,
            "task_aggregates": task_aggregates_to_dicts(heldout_task_aggregates),
            "episodes": {
                task_name: [episode.to_dict() for episode in task_results]
                for task_name, task_results in heldout_suite_results.items()
            },
        },
        "summary_rows": summary_rows,
        "domain_rows": domain_rows,
        "trace_examples": trace_examples,
        "ablation_summary": ablation_rows,
        "verdict": verdict,
    }
    if ablation_payload is not None:
        payload["ablations"] = ablation_payload

    return payload, report


def main():
    parser = argparse.ArgumentParser(description="Run the full DEIC-CogBench v1 package.")
    parser.add_argument("--train-split", default=DEFAULT_TRAIN_SPLIT)
    parser.add_argument("--heldout-split", default=DEFAULT_HELDOUT_SPLIT)
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--max-tasks", type=int, default=None)
    parser.add_argument("--max-episodes", type=int, default=None)
    parser.add_argument("--trace-limit", type=int, default=3)
    parser.add_argument("--no-traces", action="store_true")
    parser.add_argument("--skip-ablations", action="store_true")
    args = parser.parse_args()

    payload, report = build_package_payload(
        args.train_split,
        args.heldout_split,
        include_traces=not args.no_traces,
        max_tasks=args.max_tasks,
        max_episodes=args.max_episodes,
        include_ablations=not args.skip_ablations,
        trace_limit=args.trace_limit,
    )

    os.makedirs(args.output_dir, exist_ok=True)
    json_path = os.path.join(args.output_dir, "package_run.json")
    report_path = os.path.join(args.output_dir, "package_report.md")
    with open(json_path, "w", encoding="utf-8") as handle:
        handle.write(serialize_package_run(payload))
    with open(report_path, "w", encoding="utf-8") as handle:
        handle.write(report)

    print(report)
    print(f"Package JSON saved to {json_path}")
    print(f"Package report saved to {report_path}")


if __name__ == "__main__":
    main()
