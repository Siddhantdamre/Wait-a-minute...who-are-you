import argparse
import importlib
import json
import os
import sys
from datetime import datetime

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, PROJECT_ROOT)

from benchmarks.exec_meta_adapt.schemas import BenchmarkTaskSpec
from benchmarks.exec_meta_adapt.scoring import aggregate_episode_results, render_markdown_report, serialize_run
from benchmarks.exec_meta_adapt.tasks import TASK_REGISTRY


DEFAULT_SPLIT = os.path.join(PROJECT_ROOT, "benchmarks", "exec_meta_adapt", "splits", "train_split.yaml")
DEFAULT_JSON = os.path.join(PROJECT_ROOT, "benchmarks", "exec_meta_adapt", "results", "latest_run.json")
DEFAULT_REPORT = os.path.join(PROJECT_ROOT, "docs", "benchmark_v1_report.md")


def load_split(path):
    with open(path, "r", encoding="utf-8") as handle:
        payload = json.load(handle)
    tasks = [BenchmarkTaskSpec.from_dict(item) for item in payload["tasks"]]
    return payload, tasks


def resolve_task_runner(task_name):
    module = importlib.import_module(TASK_REGISTRY[task_name])
    return module.run_task


def run_split(split_path, include_traces=False, max_tasks=None, max_episodes=None, adapter_variant=None):
    split_payload, task_specs = load_split(split_path)
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
        suite_results[f"{spec.task}:{spec.task_class}:{spec.domain}"] = episode_results
        task_aggregates.append(aggregate_episode_results(episode_results))

    metadata = {
        "suite_name": split_payload.get("suite_name", "DEIC-CogBench v1"),
        "generated_at_utc": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "split_file": os.path.relpath(split_path, PROJECT_ROOT),
        "task_count": str(len(task_aggregates)),
    }
    return split_payload["split"], metadata, task_aggregates, suite_results


def main():
    parser = argparse.ArgumentParser(description="Run DEIC-CogBench v1.")
    parser.add_argument("--split", default=DEFAULT_SPLIT)
    parser.add_argument("--output-json", default=DEFAULT_JSON)
    parser.add_argument("--output-report", default=DEFAULT_REPORT)
    parser.add_argument("--include-traces", action="store_true")
    parser.add_argument("--max-tasks", type=int, default=None)
    parser.add_argument("--max-episodes", type=int, default=None)
    args = parser.parse_args()

    split_name, metadata, task_aggregates, suite_results = run_split(
        args.split,
        include_traces=args.include_traces,
        max_tasks=args.max_tasks,
        max_episodes=args.max_episodes,
    )

    os.makedirs(os.path.dirname(args.output_json), exist_ok=True)
    with open(args.output_json, "w", encoding="utf-8") as handle:
        handle.write(serialize_run(split_name, metadata, task_aggregates, suite_results))

    report = render_markdown_report(split_name, task_aggregates, metadata)
    os.makedirs(os.path.dirname(args.output_report), exist_ok=True)
    with open(args.output_report, "w", encoding="utf-8") as handle:
        handle.write(report)

    print(report)
    print(f"JSON saved to {args.output_json}")
    print(f"Report saved to {args.output_report}")


if __name__ == "__main__":
    main()
