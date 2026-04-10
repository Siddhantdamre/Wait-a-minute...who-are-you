import argparse
import json
import os
import sys
from datetime import datetime

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, PROJECT_ROOT)

from benchmarks.exec_meta_adapt.run_suite import load_split, resolve_task_runner
from benchmarks.exec_meta_adapt.schemas import BenchmarkTaskSpec, CONTRACT_VERSION, DEFAULT_SUITE_NAME
from benchmarks.exec_meta_adapt.scoring import (
    _metrics_from_results,
    filter_episode_results,
    flatten_episode_results,
    serialize_package_run,
)


DEFAULT_TRAIN_SPLIT = os.path.join(PROJECT_ROOT, "benchmarks", "exec_meta_adapt", "splits", "train_split.yaml")
DEFAULT_HELDOUT_SPLIT = os.path.join(PROJECT_ROOT, "benchmarks", "exec_meta_adapt", "splits", "heldout_split.yaml")
DEFAULT_OUTPUT_DIR = os.path.join(PROJECT_ROOT, "results", "deic_cogbench", "system_comparison")
DEFAULT_SEED_SHIFTS = (0, 1_000_000, 2_000_000)

SYSTEMS = (
    {
        "label": "v1.4-deic-cogbench",
        "adapter_variant": "frozen_full",
        "notes": "Frozen benchmark checkpoint reproduced through the frozen_full configuration on the current codebase.",
    },
    {
        "label": "no-adaptation",
        "adapter_variant": "no_adaptation",
        "notes": "Planner and safety stay on, but bounded adaptation is disabled.",
    },
    {
        "label": "v1.6-dsl-v1",
        "adapter_variant": "dsl_v1",
        "notes": "DSL v1 enables guarded post-adaptation probing plus replay-validated post-probe family proposal.",
    },
)

TRAIN_BUCKETS = (
    ("standard_tasks", ("standard_inference",)),
    ("adaptive_mismatch_tasks", ("adaptive_mismatch",)),
    ("adversarial_trust_tasks", ("adversarial_trust",)),
    ("budget_noise_stress", ("budget_noise_stress",)),
)


def clone_task_spec(spec, *, adapter_variant, seed_shift, max_episodes=None):
    payload = spec.to_dict()
    payload["adapter_variant"] = adapter_variant
    payload["seed_offset"] += seed_shift
    if max_episodes is not None:
        payload["n_episodes"] = min(payload["n_episodes"], max_episodes)
    return BenchmarkTaskSpec.from_dict(payload)


def run_system_split(split_path, system, seed_shifts, max_tasks=None, max_episodes=None, include_traces=False):
    split_spec = load_split(split_path)
    task_specs = list(split_spec.tasks)
    if max_tasks is not None:
        task_specs = task_specs[:max_tasks]

    all_results = []
    seed_runs = []
    for run_index, seed_shift in enumerate(seed_shifts):
        suite_results = {}
        for spec in task_specs:
            shifted_spec = clone_task_spec(
                spec,
                adapter_variant=system["adapter_variant"],
                seed_shift=seed_shift,
                max_episodes=max_episodes,
            )
            runner = resolve_task_runner(shifted_spec.task)
            episode_results = runner(shifted_spec, include_traces=include_traces)
            for episode in episode_results:
                episode.metadata["seed_run_index"] = run_index
                episode.metadata["seed_shift"] = seed_shift
                episode.metadata["system_label"] = system["label"]
            key = f"{shifted_spec.task}:{shifted_spec.task_class}:{shifted_spec.domain}:{shifted_spec.adapter_variant}:{seed_shift}"
            suite_results[key] = episode_results

        flattened = flatten_episode_results(suite_results)
        seed_runs.append(
            {
                "seed_shift": seed_shift,
                "metrics": _metrics_from_results(flattened),
            }
        )
        all_results.extend(flattened)

    return {
        "split": split_spec.split,
        "system_label": system["label"],
        "adapter_variant": system["adapter_variant"],
        "seed_shifts": list(seed_shifts),
        "episodes": all_results,
        "seed_runs": seed_runs,
    }


def build_train_rows(results_by_system):
    rows = []
    for system_label, results in results_by_system.items():
        train_results = results["train"]["episodes"]
        for bucket_name, task_classes in TRAIN_BUCKETS:
            metrics = _metrics_from_results(
                filter_episode_results(train_results, task_classes=task_classes)
            )
            rows.append(
                {
                    "system": system_label,
                    "bucket": bucket_name,
                    **metrics,
                }
            )
    return rows


def build_heldout_rows(results_by_system):
    rows = []
    for system_label, results in results_by_system.items():
        heldout_results = results["heldout"]["episodes"]
        for domain in ("benchmark", "cyber", "clinical"):
            metrics = _metrics_from_results(
                filter_episode_results(
                    heldout_results,
                    task_classes=("heldout_transfer",),
                    domain=domain,
                )
            )
            rows.append(
                {
                    "system": system_label,
                    "domain": domain,
                    **metrics,
                }
            )
    return rows


def build_system_rows(results_by_system):
    baseline = results_by_system["v1.4-deic-cogbench"]
    baseline_metrics = _metrics_from_results(baseline["train"]["episodes"] + baseline["heldout"]["episodes"])
    rows = []
    for system_label, results in results_by_system.items():
        metrics = _metrics_from_results(results["train"]["episodes"] + results["heldout"]["episodes"])
        rows.append(
            {
                "system": system_label,
                "episodes": metrics["n_episodes"],
                "final_accuracy": metrics["final_accuracy"],
                "accuracy_on_commit": metrics["accuracy_on_commit"],
                "abstention_rate": metrics["abstention_rate"],
                "silent_failure_rate": metrics["silent_failure_rate"],
                "false_adaptation_rate": metrics["false_adaptation_rate"],
                "adaptation_trigger_rate": metrics["adaptation_trigger_rate"],
                "post_adaptation_recovery_rate": metrics["post_adaptation_recovery_rate"],
                "delta_vs_v14": round(metrics["final_accuracy"] - baseline_metrics["final_accuracy"], 4),
            }
        )
    return rows


def build_verdict(train_rows, heldout_rows):
    def _row(rows, system, bucket_or_domain_key, value):
        for row in rows:
            if row["system"] == system and row.get(bucket_or_domain_key) == value:
                return row
        raise KeyError((system, bucket_or_domain_key, value))

    dsl_adaptive = _row(train_rows, "v1.6-dsl-v1", "bucket", "adaptive_mismatch_tasks")
    baseline_adaptive = _row(train_rows, "v1.4-deic-cogbench", "bucket", "adaptive_mismatch_tasks")
    dsl_standard = _row(train_rows, "v1.6-dsl-v1", "bucket", "standard_tasks")
    baseline_standard = _row(train_rows, "v1.4-deic-cogbench", "bucket", "standard_tasks")
    dsl_trust = _row(train_rows, "v1.6-dsl-v1", "bucket", "adversarial_trust_tasks")
    baseline_trust = _row(train_rows, "v1.4-deic-cogbench", "bucket", "adversarial_trust_tasks")

    heldout_delta = []
    for domain in ("benchmark", "cyber", "clinical"):
        dsl_domain = _row(heldout_rows, "v1.6-dsl-v1", "domain", domain)
        baseline_domain = _row(heldout_rows, "v1.4-deic-cogbench", "domain", domain)
        heldout_delta.append(dsl_domain["final_accuracy"] - baseline_domain["final_accuracy"])

    adaptive_gain = dsl_adaptive["final_accuracy"] - baseline_adaptive["final_accuracy"]
    standard_drift = abs(dsl_standard["final_accuracy"] - baseline_standard["final_accuracy"])
    trust_drift = abs(dsl_trust["final_accuracy"] - baseline_trust["final_accuracy"])
    mean_heldout_delta = sum(heldout_delta) / len(heldout_delta)

    if adaptive_gain >= 0.05 and standard_drift <= 0.01 and trust_drift <= 0.01 and mean_heldout_delta < 0.03:
        return (
            "v1.6-dsl-v1 currently reads as a narrow local win: it improves adaptive mismatch behavior without harming "
            "the protected standard or trust paths, but the held-out transfer surface is essentially flat."
        )
    if adaptive_gain >= 0.05 and mean_heldout_delta >= 0.03:
        return (
            "v1.6-dsl-v1 looks like a benchmark-visible capability shift: adaptive mismatch gains are real and held-out "
            "transfer moved meaningfully in the same direction."
        )
    return (
        "v1.6-dsl-v1 is still below the benchmark-visible threshold: the comparison bundle does not show enough adaptive "
        "or held-out movement to justify a broader significance claim."
    )


def _format(value):
    if value is None:
        return "-"
    if isinstance(value, int):
        return str(value)
    return f"{value:.2f}"


def render_report(payload):
    lines = [
        "# DEIC-CogBench System Comparison",
        "",
        "## Scope",
        "",
        f"- suite_name: `{DEFAULT_SUITE_NAME}`",
        f"- contract_version: `{CONTRACT_VERSION}`",
        f"- train_split: `{payload['train_split']}`",
        f"- heldout_split: `{payload['heldout_split']}`",
        f"- seed_shifts: `{payload['seed_shifts']}`",
        "",
        "## Benchmark Comparison Table",
        "",
        "| System | Bucket | Final Acc | Commit Acc | Abstain | Silent Failure | False Adapt | Adapt Trigger | Post-Adapt Recovery |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in payload["benchmark_rows"]:
        lines.append(
            f"| {row['system']} | {row['bucket']} | {_format(row['final_accuracy'])} | {_format(row['accuracy_on_commit'])} | "
            f"{_format(row['abstention_rate'])} | {_format(row['silent_failure_rate'])} | {_format(row['false_adaptation_rate'])} | "
            f"{_format(row['adaptation_trigger_rate'])} | {_format(row['post_adaptation_recovery_rate'])} |"
        )

    lines.extend(
        [
            "",
            "## Heldout Generalization Table",
            "",
            "| System | Domain | Final Acc | Commit Acc | Abstain | Silent Failure | False Adapt | Adapt Trigger | Post-Adapt Recovery |",
            "|---|---|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for row in payload["heldout_rows"]:
        lines.append(
            f"| {row['system']} | {row['domain']} | {_format(row['final_accuracy'])} | {_format(row['accuracy_on_commit'])} | "
            f"{_format(row['abstention_rate'])} | {_format(row['silent_failure_rate'])} | {_format(row['false_adaptation_rate'])} | "
            f"{_format(row['adaptation_trigger_rate'])} | {_format(row['post_adaptation_recovery_rate'])} |"
        )

    lines.extend(
        [
            "",
            "## System Comparison Table",
            "",
            "| System | Episodes | Final Acc | Delta vs v1.4 | Commit Acc | Abstain | Silent Failure | False Adapt | Adapt Trigger | Post-Adapt Recovery |",
            "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for row in payload["system_rows"]:
        lines.append(
            f"| {row['system']} | {row['episodes']} | {_format(row['final_accuracy'])} | {_format(row['delta_vs_v14'])} | "
            f"{_format(row['accuracy_on_commit'])} | {_format(row['abstention_rate'])} | {_format(row['silent_failure_rate'])} | "
            f"{_format(row['false_adaptation_rate'])} | {_format(row['adaptation_trigger_rate'])} | {_format(row['post_adaptation_recovery_rate'])} |"
        )

    lines.extend(
        [
            "",
            "## Verdict",
            "",
            f"- {payload['verdict']}",
            "",
            "## Notes",
            "",
            "- This comparison is evaluation-only: no mechanism changes were introduced beyond exposing the frozen v1.6 configuration as an explicit benchmark variant.",
            "- `v1.4-deic-cogbench` is reproduced through the frozen planner configuration on the current codebase, rather than by checking out a separate worktree.",
            "- Multi-seed runs are implemented by deterministic seed shifts applied to the frozen split specs.",
        ]
    )
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description="Run benchmark-scale system comparison for DEIC-CogBench.")
    parser.add_argument("--train-split", default=DEFAULT_TRAIN_SPLIT)
    parser.add_argument("--heldout-split", default=DEFAULT_HELDOUT_SPLIT)
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--seed-shifts", nargs="*", type=int, default=list(DEFAULT_SEED_SHIFTS))
    parser.add_argument("--max-tasks", type=int, default=None)
    parser.add_argument("--max-episodes", type=int, default=None)
    parser.add_argument("--include-traces", action="store_true")
    args = parser.parse_args()

    results_by_system = {}
    for system in SYSTEMS:
        results_by_system[system["label"]] = {
            "train": run_system_split(
                args.train_split,
                system,
                seed_shifts=args.seed_shifts,
                max_tasks=args.max_tasks,
                max_episodes=args.max_episodes,
                include_traces=args.include_traces,
            ),
            "heldout": run_system_split(
                args.heldout_split,
                system,
                seed_shifts=args.seed_shifts,
                max_tasks=args.max_tasks,
                max_episodes=args.max_episodes,
                include_traces=args.include_traces,
            ),
            "notes": system["notes"],
        }

    benchmark_rows = build_train_rows(results_by_system)
    heldout_rows = build_heldout_rows(results_by_system)
    system_rows = build_system_rows(results_by_system)
    verdict = build_verdict(benchmark_rows, heldout_rows)
    serialized_systems = {}
    for system_label, results in results_by_system.items():
        serialized_systems[system_label] = {
            "notes": results["notes"],
            "train": {
                "split": results["train"]["split"],
                "system_label": results["train"]["system_label"],
                "adapter_variant": results["train"]["adapter_variant"],
                "seed_shifts": results["train"]["seed_shifts"],
                "seed_runs": results["train"]["seed_runs"],
                "episodes": [episode.to_dict() for episode in results["train"]["episodes"]],
            },
            "heldout": {
                "split": results["heldout"]["split"],
                "system_label": results["heldout"]["system_label"],
                "adapter_variant": results["heldout"]["adapter_variant"],
                "seed_shifts": results["heldout"]["seed_shifts"],
                "seed_runs": results["heldout"]["seed_runs"],
                "episodes": [episode.to_dict() for episode in results["heldout"]["episodes"]],
            },
        }

    payload = {
        "generated_at_utc": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "suite_name": DEFAULT_SUITE_NAME,
        "contract_version": CONTRACT_VERSION,
        "train_split": os.path.relpath(args.train_split, PROJECT_ROOT),
        "heldout_split": os.path.relpath(args.heldout_split, PROJECT_ROOT),
        "seed_shifts": args.seed_shifts,
        "systems": serialized_systems,
        "benchmark_rows": benchmark_rows,
        "heldout_rows": heldout_rows,
        "system_rows": system_rows,
        "verdict": verdict,
    }
    report = render_report(payload)

    os.makedirs(args.output_dir, exist_ok=True)
    json_path = os.path.join(args.output_dir, "system_comparison.json")
    report_path = os.path.join(args.output_dir, "system_comparison_report.md")
    with open(json_path, "w", encoding="utf-8") as handle:
        handle.write(serialize_package_run(payload))
    with open(report_path, "w", encoding="utf-8") as handle:
        handle.write(report)

    print(report)
    print(f"System comparison JSON saved to {json_path}")
    print(f"System comparison report saved to {report_path}")


if __name__ == "__main__":
    main()
