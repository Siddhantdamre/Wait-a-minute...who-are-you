import os
import sys
from dataclasses import asdict

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, PROJECT_ROOT)
sys.path.insert(0, os.path.join(PROJECT_ROOT, "benchmark"))

from benchmark.environment import ProceduralEnvironment, generate_episodes
from benchmarks.exec_meta_adapt.schemas import EpisodeResult
from benchmarks.exec_meta_adapt.scoring import (
    compute_false_adaptation,
    compute_silent_failure,
    final_status_from_flags,
    truthy_turn,
)
from benchmarks.exec_meta_adapt.tasks.common import build_adapter
from deic_core.self_model import SelfModel


def run_task(spec, include_traces=False):
    episodes = generate_episodes(spec.n_episodes, condition=spec.condition or "c6_hidden_structure", seed_offset=spec.seed_offset)
    results = []
    for index, cfg in enumerate(episodes):
        cfg.max_turns = spec.budget
        env = ProceduralEnvironment(cfg)
        adapter = build_adapter(spec.domain, spec.adapter_variant)
        trajectory, outcome = adapter.solve(env)
        ws = outcome.get("final_workspace")
        committed = not bool(outcome.get("escalated"))
        abstained = bool(outcome.get("abstained")) or bool(outcome.get("escalated"))
        accuracy = 1.0 if outcome.get("consensus_reached", False) else 0.0
        self_model_snapshot = (
            asdict(SelfModel.from_workspace(ws))
            if ws and hasattr(ws, "top_hypotheses")
            else None
        )
        results.append(
            EpisodeResult(
                domain=spec.domain,
                task_name=spec.task,
                task_class=spec.task_class,
                split=spec.split,
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
                planner_trace_available=bool(trajectory),
                self_model_snapshot_available=self_model_snapshot is not None,
                explanation_trace_available=False,
                planner_trace=trajectory if include_traces else None,
                self_model_snapshot=self_model_snapshot if include_traces else None,
                explanation_trace=None,
                metadata={"condition": spec.condition or "c6_hidden_structure", "queries_used": len(trajectory)},
            )
        )
    return results
