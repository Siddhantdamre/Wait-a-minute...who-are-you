import argparse
import json
import os
import sys

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, PROJECT_ROOT)

from benchmarks.exec_meta_adapt.run_suite import run_split
from benchmarks.exec_meta_adapt.schemas import CONTRACT_VERSION
from benchmarks.exec_meta_adapt.scoring import (
    flatten_episode_results,
    serialize_package_run,
    summarize_variant_results,
    task_aggregates_to_dicts,
)


SUPPORTED_ABLATIONS = [
    "frozen_full",
    "no_planner",
    "no_self_model",
    "no_memory",
    "no_adaptation",
    "no_safety_circuit",
]

DEFAULT_SPLIT = os.path.join(PROJECT_ROOT, "benchmarks", "exec_meta_adapt", "splits", "train_split.yaml")
DEFAULT_OUTPUT_DIR = os.path.join(PROJECT_ROOT, "results", "deic_cogbench")


def run_ablation_suite(split_path, max_tasks=None, max_episodes=None, include_traces=True):
    payload = {
        "contract_version": CONTRACT_VERSION,
        "split_file": os.path.relpath(split_path, PROJECT_ROOT),
        "variants": {},
        "summary_rows": [],
    }
    for variant in SUPPORTED_ABLATIONS:
        split_name, metadata, task_aggregates, suite_results = run_split(
            split_path,
            include_traces=include_traces,
            max_tasks=max_tasks,
            max_episodes=max_episodes,
            adapter_variant=variant,
        )
        metadata["adapter_variant"] = variant
        episodes = flatten_episode_results(suite_results)
        summary = summarize_variant_results(variant, episodes)
        summary["split"] = split_name
        payload["summary_rows"].append(summary)
        payload["variants"][variant] = {
            "split": split_name,
            "metadata": metadata,
            "task_aggregates": task_aggregates_to_dicts(task_aggregates),
        }
    return payload


def main():
    parser = argparse.ArgumentParser(description="Run DEIC-CogBench v1 ablations.")
    parser.add_argument("--split", default=DEFAULT_SPLIT)
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--max-tasks", type=int, default=None)
    parser.add_argument("--max-episodes", type=int, default=None)
    parser.add_argument("--no-traces", action="store_true")
    args = parser.parse_args()

    payload = run_ablation_suite(
        args.split,
        max_tasks=args.max_tasks,
        max_episodes=args.max_episodes,
        include_traces=not args.no_traces,
    )

    os.makedirs(args.output_dir, exist_ok=True)
    output_json = os.path.join(args.output_dir, "ablations_train.json")
    with open(output_json, "w", encoding="utf-8") as handle:
        handle.write(serialize_package_run(payload))

    print(json.dumps(payload, indent=2))
    print(f"Ablation JSON saved to {output_json}")


if __name__ == "__main__":
    main()
