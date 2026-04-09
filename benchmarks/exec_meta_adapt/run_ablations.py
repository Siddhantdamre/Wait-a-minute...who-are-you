import argparse
import json
import os
import sys

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, PROJECT_ROOT)

from benchmarks.exec_meta_adapt.run_suite import run_split


SUPPORTED_ABLATIONS = [
    "frozen_full",
    "no_planner",
    "no_adaptation",
    "no_safety_circuit",
]

PLANNED_ABLATIONS = {
    "no_self_model": "Current adapters do not expose a clean self-model bypass without conflating planner removal.",
    "no_memory": "Benchmark v1 baseline runs do not use cross-episode memory yet, so this ablation is deferred until multi-episode curricula are added.",
}


def main():
    parser = argparse.ArgumentParser(description="Run DEIC-CogBench v1 ablations.")
    parser.add_argument("--split", default=os.path.join(PROJECT_ROOT, "benchmarks", "exec_meta_adapt", "splits", "train_split.yaml"))
    parser.add_argument("--max-tasks", type=int, default=None)
    parser.add_argument("--max-episodes", type=int, default=None)
    parser.add_argument(
        "--output-json",
        default=os.path.join(PROJECT_ROOT, "benchmarks", "exec_meta_adapt", "results", "ablations.json"),
    )
    args = parser.parse_args()

    payload = {"supported": {}, "planned": PLANNED_ABLATIONS}
    for variant in SUPPORTED_ABLATIONS:
        split_name, metadata, task_aggregates, _suite_results = run_split(
            args.split,
            include_traces=False,
            max_tasks=args.max_tasks,
            max_episodes=args.max_episodes,
            adapter_variant=variant,
        )
        metadata["adapter_variant"] = variant
        payload["supported"][variant] = {
            "split": split_name,
            "metadata": metadata,
            "task_aggregates": [aggregate.to_dict() for aggregate in task_aggregates],
        }

    os.makedirs(os.path.dirname(args.output_json), exist_ok=True)
    with open(args.output_json, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)

    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
