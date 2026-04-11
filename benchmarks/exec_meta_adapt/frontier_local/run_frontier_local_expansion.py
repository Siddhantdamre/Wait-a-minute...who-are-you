import argparse
import json
import os
import statistics
import sys
from pathlib import Path

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
FRONTIER_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontier"))
sys.path.insert(0, PROJECT_ROOT)
sys.path.insert(0, FRONTIER_ROOT)
sys.path.insert(0, os.path.dirname(__file__))

from local_model_configs import LOCAL_MODEL_CONFIGS, get_model_config
from local_model_runner import LocalModelRunner
from prompt_builder import load_tasks
from run_frontier_local import DEFAULT_TASKS, run_model_on_tasks, select_tasks
from scoring_frontier import score_records


DEFAULT_MODELS = ["qwen", "smollm", "tinyllama", "granite"]
DEFAULT_OUTPUT = os.path.join(PROJECT_ROOT, "results", "frontier_local", "open_model_expansion")
DEFAULT_SEEDS = [17, 23, 31]
SUMMARY_KEYS = [
    "final_accuracy",
    "commit_accuracy",
    "abstain_rate",
    "bluff_rate",
    "escalation_rate",
    "silent_failure_rate",
    "average_confidence",
    "average_confidence_on_wrong_commit",
    "parse_error_rate",
]
TASK_TYPES = [
    "hidden_state_uncertainty",
    "adversarial_trust",
    "overflow_mismatch",
    "clear_commit",
]


def mean_summary(summaries):
    return {
        key: round(statistics.mean(summary[key] for summary in summaries), 4)
        for key in SUMMARY_KEYS
    }


def aggregate_model_runs(model_name, model_config, runs):
    overall_summaries = [run["summary"]["summary"] for run in runs]
    by_task_type = {}
    for task_type in TASK_TYPES:
        typed_summaries = [run["summary"]["by_task_type"][task_type] for run in runs]
        by_task_type[task_type] = mean_summary(typed_summaries)
    return {
        "model": model_name,
        "model_config": model_config,
        "seeds": [run["seed"] for run in runs],
        "summary": mean_summary(overall_summaries),
        "by_task_type": by_task_type,
        "seed_invariant": len({json.dumps(run["summary"], sort_keys=True) for run in runs}) == 1,
    }


def render_overall_table(aggregates):
    lines = [
        "# Open-Weight Expansion: Overall Comparison",
        "",
        "| Model | Seeds | Final Acc | Commit Acc | Abstain | Bluff | Escalate | Silent Failure | Avg Conf | Wrong Commit Conf |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for payload in aggregates:
        summary = payload["summary"]
        lines.append(
            f"| {payload['model']} | {len(payload['seeds'])} | {summary['final_accuracy']:.2f} | "
            f"{summary['commit_accuracy']:.2f} | {summary['abstain_rate']:.2f} | {summary['bluff_rate']:.2f} | "
            f"{summary['escalation_rate']:.2f} | {summary['silent_failure_rate']:.2f} | "
            f"{summary['average_confidence']:.2f} | {summary['average_confidence_on_wrong_commit']:.2f} |"
        )
    return "\n".join(lines)


def render_per_task_type_table(aggregates):
    lines = ["# Open-Weight Expansion: Per-Task-Type Comparison", ""]
    for task_type in TASK_TYPES:
        lines.append(f"## {task_type}")
        lines.append("")
        lines.append("| Model | Final Acc | Commit Acc | Abstain | Bluff | Escalate | Silent Failure |")
        lines.append("|---|---:|---:|---:|---:|---:|---:|")
        for payload in aggregates:
            summary = payload["by_task_type"][task_type]
            lines.append(
                f"| {payload['model']} | {summary['final_accuracy']:.2f} | {summary['commit_accuracy']:.2f} | "
                f"{summary['abstain_rate']:.2f} | {summary['bluff_rate']:.2f} | "
                f"{summary['escalation_rate']:.2f} | {summary['silent_failure_rate']:.2f} |"
            )
        lines.append("")
    return "\n".join(lines)


def render_findings_note(aggregates):
    model_map = {payload["model"]: payload for payload in aggregates}
    qwen_abstain = model_map.get("qwen", {}).get("by_task_type", {}).get("hidden_state_uncertainty", {}).get("abstain_rate", 0.0)
    smollm_abstain = model_map.get("smollm", {}).get("by_task_type", {}).get("hidden_state_uncertainty", {}).get("abstain_rate", 0.0)
    lines = [
        "# Open-Weight Expansion Findings",
        "",
        "## Main Question",
        "",
        "Is the `safe but over-escalatory` pattern stable across open-weight models, or is it specific to the original two-model slice?",
        "",
        "## Short Answer",
        "",
        "This first expansion pass is designed to answer that question on the same frozen task set, with the same prompts and scoring. "
        "The key interpretation remains tied to hidden-state uncertainty: the central failure is not bluffing, but collapsing abstention into escalation.",
        "",
        "## Current Readout",
        "",
        f"- `qwen` hidden-state abstain rate: `{qwen_abstain:.2f}`",
        f"- `smollm` hidden-state abstain rate: `{smollm_abstain:.2f}`",
        "- If the added models also drive `hidden_state_uncertainty` mostly to `ESCALATE`, the pattern is likely stable across this open-weight slice.",
        "- If one of the added models separates `ABSTAIN` from `ESCALATE` materially better, that becomes the most important new contrast result.",
        "",
        "## Evaluation Note",
        "",
        "This expansion runner keeps a multi-seed interface for consistency, but on the full 40-task frozen benchmark under greedy decoding the outputs are expected to be seed-invariant.",
    ]
    return "\n".join(lines)


def render_behavior_svg(aggregates, output_path):
    width = 220 + 250 * len(aggregates)
    height = 560
    chart_top = 120
    chart_bottom = 400
    chart_height = chart_bottom - chart_top
    model_width = 210
    action_colors = {
        "commit": "#2C7FB8",
        "abstain": "#F28E2B",
        "escalate": "#C44E52",
    }
    task_labels = {
        "hidden_state_uncertainty": ["Hidden", "uncertainty"],
        "adversarial_trust": ["Adversarial", "trust"],
        "overflow_mismatch": ["Overflow", "mismatch"],
        "clear_commit": ["Clear", "commit"],
    }
    svg = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#ffffff"/>',
        '<text x="{0}" y="34" text-anchor="middle" font-family="Arial, sans-serif" font-size="24" font-weight="bold" fill="#111111">Open-Weight Metacognition Expansion</text>'.format(width / 2),
        '<text x="{0}" y="58" text-anchor="middle" font-family="Arial, sans-serif" font-size="14" fill="#444444">Commit / Abstain / Escalate behavior by task type</text>'.format(width / 2),
    ]
    for tick in range(6):
        value = tick / 5
        y = chart_bottom - value * chart_height
        svg.append(f'<line x1="60" y1="{y}" x2="{width - 40}" y2="{y}" stroke="#e6e6e6" stroke-width="1"/>')
        svg.append(f'<text x="50" y="{y + 4}" text-anchor="end" font-family="Arial, sans-serif" font-size="11" fill="#666666">{value:.1f}</text>')
    for model_index, payload in enumerate(aggregates):
        origin_x = 90 + model_index * 250
        svg.append(
            f'<text x="{origin_x + model_width / 2}" y="92" text-anchor="middle" font-family="Arial, sans-serif" font-size="15" font-weight="bold" fill="#111111">{payload["model"]}</text>'
        )
        svg.append(f'<line x1="{origin_x}" y1="{chart_bottom}" x2="{origin_x + model_width}" y2="{chart_bottom}" stroke="#333333" stroke-width="1.2"/>')
        for group_index, task_type in enumerate(TASK_TYPES):
            task_summary = payload["by_task_type"][task_type]
            rates = [
                ("commit", 1.0 - task_summary["abstain_rate"] - task_summary["escalation_rate"]),
                ("abstain", task_summary["abstain_rate"]),
                ("escalate", task_summary["escalation_rate"]),
            ]
            base_x = origin_x + 8 + group_index * 50
            for rate_index, (rate_name, rate_value) in enumerate(rates):
                bar_height = max(0.0, min(1.0, rate_value)) * chart_height
                x = base_x + rate_index * 14
                y = chart_bottom - bar_height
                svg.append(
                    f'<rect x="{x}" y="{y}" width="12" height="{bar_height}" fill="{action_colors[rate_name]}" rx="1"/>'
                )
            center = base_x + 20
            for line_index, line in enumerate(task_labels[task_type]):
                svg.append(
                    f'<text x="{center}" y="{chart_bottom + 20 + line_index * 13}" text-anchor="middle" font-family="Arial, sans-serif" font-size="10" fill="#333333">{line}</text>'
                )
    legend_x = max(120, width / 2 - 140)
    legend_y = 470
    for idx, (label, color) in enumerate([("COMMIT", action_colors["commit"]), ("ABSTAIN", action_colors["abstain"]), ("ESCALATE", action_colors["escalate"])]):
        x = legend_x + idx * 120
        svg.append(f'<rect x="{x}" y="{legend_y}" width="18" height="18" fill="{color}" rx="2"/>')
        svg.append(f'<text x="{x + 26}" y="{legend_y + 14}" font-family="Arial, sans-serif" font-size="12" fill="#333333">{label}</text>')
    svg.append("</svg>")
    output_path.write_text("\n".join(svg), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Run expanded local/open-weight frontier evaluation across several models.")
    parser.add_argument("--models", nargs="+", default=DEFAULT_MODELS)
    parser.add_argument("--tasks", default=DEFAULT_TASKS)
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--seeds", nargs="+", type=int, default=DEFAULT_SEEDS)
    args = parser.parse_args()

    tasks = load_tasks(args.tasks)
    runner = LocalModelRunner()
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    aggregates = []
    for model_name in args.models:
        model_runs = []
        cache_summary = None
        cache_records = None
        for seed in args.seeds:
            selected_tasks = select_tasks(tasks, limit=args.limit, sample_seed=seed)
            if args.limit is None and cache_summary is not None:
                scored = cache_summary
                records = cache_records
            else:
                records = run_model_on_tasks(runner, model_name, selected_tasks)
                scored = score_records(records)
                if args.limit is None:
                    cache_records = records
                    cache_summary = scored
            payload = {
                "model": model_name,
                "model_config": get_model_config(model_name),
                "seed": seed,
                "n_tasks": len(selected_tasks),
                "summary": scored,
                "records": records,
            }
            model_runs.append(payload)
            (output_dir / f"{model_name}_seed_{seed}.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
        aggregates.append(aggregate_model_runs(model_name, get_model_config(model_name), model_runs))

    aggregate_payload = {
        "models": aggregates,
        "task_file": str(Path(args.tasks)),
        "seeds": args.seeds,
        "available_models": sorted(LOCAL_MODEL_CONFIGS),
    }
    (output_dir / "aggregate_summary.json").write_text(json.dumps(aggregate_payload, indent=2), encoding="utf-8")
    (output_dir / "overall_comparison.md").write_text(render_overall_table(aggregates), encoding="utf-8")
    (output_dir / "per_task_type_table.md").write_text(render_per_task_type_table(aggregates), encoding="utf-8")
    (output_dir / "findings_note.md").write_text(render_findings_note(aggregates), encoding="utf-8")
    render_behavior_svg(aggregates, output_dir / "behavior_figure.svg")
    print(render_overall_table(aggregates))


if __name__ == "__main__":
    main()
