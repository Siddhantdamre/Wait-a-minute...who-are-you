import os
import sys
from dataclasses import asdict

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, PROJECT_ROOT)

from benchmarks.exec_meta_adapt.schemas import EpisodeResult
from benchmarks.exec_meta_adapt.scoring import (
    compute_false_adaptation,
    compute_silent_failure,
    final_status_from_flags,
    truthy_turn,
)
from benchmarks.exec_meta_adapt.tasks.common import (
    build_adapter,
    build_explanation_trace,
    build_memory,
    build_self_model_snapshot,
    extract_planner_trace,
    update_cross_episode_memory,
)
from experiments.clinical_transfer.environment import ClinicalEnvironment, generate_clinical_episodes


def run_task(spec, include_traces=False):
    episodes = generate_clinical_episodes(spec.n_episodes, seed_offset=spec.seed_offset)
    results = []
    memory = build_memory(spec.adapter_variant)
    for index, cfg in enumerate(episodes):
        cfg.max_queries = spec.budget
        env = ClinicalEnvironment(cfg)
        adapter = build_adapter(spec.domain, spec.adapter_variant, memory=memory)
        outcome = adapter.diagnose(env)
        ws = outcome.get("final_workspace")
        planner_trace = extract_planner_trace(outcome)
        committed = not bool(outcome.get("escalated"))
        abstained = bool(outcome.get("abstained")) or bool(outcome.get("escalated"))
        accuracy = 1.0 if outcome.get("correct", False) else 0.0
        self_model = build_self_model_snapshot(ws, spec.adapter_variant)
        self_model_snapshot = asdict(self_model) if self_model is not None else None
        explanation_trace = build_explanation_trace(ws, planner_trace, spec.adapter_variant)
        results.append(
            EpisodeResult(
                domain=spec.domain,
                task_name=spec.task,
                task_class=spec.task_class,
                split=spec.split,
                adapter_variant=spec.adapter_variant,
                seed=spec.seed_offset + index,
                budget=spec.budget,
                final_status=final_status_from_flags(committed, abstained, accuracy),
                accuracy=accuracy,
                committed=committed,
                abstained=abstained,
                silent_failure=compute_silent_failure(committed, abstained, ws.get("confidence_margin") if ws else None),
                false_adaptation=compute_false_adaptation(spec.task_class, ws.get("adaptation_count", 0) if ws else 0),
                trust_lock_turn=truthy_turn(ws.get("trust_lock_turn") if ws else None),
                contradiction_trigger_turn=truthy_turn(ws.get("contradiction_probe_trigger_turn") if ws else None),
                adaptation_trigger_turn=truthy_turn(ws.get("adaptation_turn") if ws else None),
                planner_trace_available=bool(planner_trace),
                self_model_snapshot_available=self_model_snapshot is not None,
                explanation_trace_available=bool(explanation_trace),
                planner_trace=planner_trace if include_traces else None,
                self_model_snapshot=self_model_snapshot if include_traces else None,
                explanation_trace=explanation_trace if include_traces else None,
                metadata={
                    "queries_used": outcome.get("queries_used", env.turn),
                    "group_size": len(cfg.deteriorating),
                    "memory_enabled": memory is not None,
                },
            )
        )
        update_cross_episode_memory(memory, ws, success=accuracy >= 1.0)
    return results
