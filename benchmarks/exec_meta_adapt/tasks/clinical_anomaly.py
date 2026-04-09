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
from benchmarks.exec_meta_adapt.tasks.common import build_adapter
from deic_core import FixedPartitionGenerator
from deic_core.self_model import SelfModel
from experiments.clinical_transfer.environment import ClinicalEnvironment
from experiments.cross_domain_adaptive_validation import generate_clinical_anomaly_episodes


def run_task(spec, include_traces=False):
    true_group_size = spec.group_size or 5
    episodes = generate_clinical_anomaly_episodes(spec.n_episodes, group_size=true_group_size, seed_offset=spec.seed_offset)
    fixed_generator = FixedPartitionGenerator(group_size=4, multipliers=[1.3, 1.8, 2.5])
    results = []
    for index, cfg in enumerate(episodes):
        cfg.max_queries = spec.budget
        env = ClinicalEnvironment(cfg)
        adapter = build_adapter(spec.domain, spec.adapter_variant, hypothesis_generator=fixed_generator)
        outcome = adapter.diagnose(env)
        ws = outcome.get("final_workspace")
        committed = not bool(outcome.get("escalated"))
        abstained = bool(outcome.get("abstained")) or bool(outcome.get("escalated"))
        accuracy = 1.0 if outcome.get("correct", False) else 0.0
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
                planner_trace_available=False,
                self_model_snapshot_available=self_model_snapshot is not None,
                explanation_trace_available=False,
                planner_trace=None,
                self_model_snapshot=self_model_snapshot if include_traces else None,
                explanation_trace=None,
                metadata={
                    "queries_used": outcome.get("queries_used", env.turn),
                    "true_group_size": true_group_size,
                    "family_search_outcome": ws.get("family_search_outcome") if ws else "",
                },
            )
        )
    return results
