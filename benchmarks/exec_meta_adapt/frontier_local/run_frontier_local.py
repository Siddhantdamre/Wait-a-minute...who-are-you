import argparse
import json
import os
import random
import sys
from collections import defaultdict
from pathlib import Path

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
FRONTIER_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontier"))
sys.path.insert(0, PROJECT_ROOT)
sys.path.insert(0, FRONTIER_ROOT)
sys.path.insert(0, os.path.dirname(__file__))

from local_model_configs import get_model_config
from local_model_runner import LocalModelRunner
from prompt_builder import SYSTEM_PROMPT, build_messages, load_tasks
from response_parser import parse_model_response
from scoring_frontier import score_records


DEFAULT_TASKS = os.path.join(FRONTIER_ROOT, "frontier_tasks_metacog.jsonl")
DEFAULT_OUTPUT = os.path.join(PROJECT_ROOT, "results", "frontier_local")
DEFAULT_SAMPLE_SEED = 17


def select_tasks(tasks, limit=None, sample_seed=DEFAULT_SAMPLE_SEED):
    if limit is None or limit >= len(tasks):
        return list(tasks)

    buckets = defaultdict(list)
    for task in tasks:
        buckets[task["task_type"]].append(task)

    rng = random.Random(sample_seed)
    ordered_types = sorted(buckets)
    for task_type in ordered_types:
        rng.shuffle(buckets[task_type])

    selected = []
    bucket_index = 0
    while len(selected) < limit:
        task_type = ordered_types[bucket_index % len(ordered_types)]
        if buckets[task_type]:
            selected.append(buckets[task_type].pop())
        bucket_index += 1
    return selected


def run_model_on_tasks(runner, model_name, tasks):
    config = get_model_config(model_name)
    records = []
    for task in tasks:
        messages = build_messages(task)
        raw_output = runner.generate(model_name, SYSTEM_PROMPT, messages)
        parsed = parse_model_response(raw_output)
        records.append(
            {
                "task_id": task["task_id"],
                "task_type": task["task_type"],
                "gold_action": task["gold_action"],
                "gold_reason": task["gold_reason"],
                "parsed_action": parsed.get("action"),
                "parsed_confidence": parsed.get("confidence"),
                "parsed_reason": parsed.get("reason", ""),
                "parse_error": parsed.get("parse_error", False),
                "correct": parsed.get("action") == task["gold_action"],
                "source_domain": task["source_domain"],
                "source_task_family": task["source_task_family"],
                "source_split": task["source_split"],
                "source_seed": task.get("source_seed"),
                "model_label": config["label"],
                "raw_output": raw_output,
            }
        )
    return records


def render_comparison_table(results_by_model):
    lines = [
        "# Local Frontier Comparison Table",
        "",
        "| Model | Tasks | Final Acc | Commit Acc | Abstain | Bluff | Escalate | Silent Failure | Avg Conf | Wrong Commit Conf | Parse Error |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for model_name, payload in results_by_model.items():
        summary = payload["summary"]["summary"]
        lines.append(
            f"| {model_name} | {summary['n_tasks']} | {summary['final_accuracy']:.2f} | {summary['commit_accuracy']:.2f} | "
            f"{summary['abstain_rate']:.2f} | {summary['bluff_rate']:.2f} | {summary['escalation_rate']:.2f} | "
            f"{summary['silent_failure_rate']:.2f} | {summary['average_confidence']:.2f} | "
            f"{summary['average_confidence_on_wrong_commit']:.2f} | {summary['parse_error_rate']:.2f} |"
        )
    lines.append("")
    lines.append("## By Task Type")
    lines.append("")
    for model_name, payload in results_by_model.items():
        lines.append(f"### {model_name}")
        lines.append("")
        lines.append("| Task Type | Final Acc | Abstain | Bluff | Escalate | Silent Failure |")
        lines.append("|---|---:|---:|---:|---:|---:|")
        for task_type, summary in payload["summary"]["by_task_type"].items():
            lines.append(
                f"| {task_type} | {summary['final_accuracy']:.2f} | {summary['abstain_rate']:.2f} | "
                f"{summary['bluff_rate']:.2f} | {summary['escalation_rate']:.2f} | {summary['silent_failure_rate']:.2f} |"
            )
        lines.append("")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Run local/open-weight frontier evaluation over DEIC metacognition tasks.")
    parser.add_argument("--models", nargs="+", required=True)
    parser.add_argument("--tasks", default=DEFAULT_TASKS)
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--sample-seed", type=int, default=DEFAULT_SAMPLE_SEED)
    args = parser.parse_args()

    tasks = load_tasks(args.tasks)
    tasks = select_tasks(tasks, limit=args.limit, sample_seed=args.sample_seed)

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    runner = LocalModelRunner()
    results_by_model = {}

    for model_name in args.models:
        records = run_model_on_tasks(runner, model_name, tasks)
        scored = score_records(records)
        payload = {
            "model": model_name,
            "model_config": get_model_config(model_name),
            "tasks_file": str(Path(args.tasks)),
            "n_tasks": len(tasks),
            "summary": scored,
            "records": records,
        }
        results_by_model[model_name] = payload
        (output_dir / f"{model_name}_results.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")

    comparison = render_comparison_table(results_by_model)
    (output_dir / "comparison_table.md").write_text(comparison, encoding="utf-8")
    print(comparison)


if __name__ == "__main__":
    main()
