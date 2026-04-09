import os
import sys

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, PROJECT_ROOT)
sys.path.insert(0, os.path.join(PROJECT_ROOT, "benchmark"))

from deic_core import CrossEpisodeMemory, StateExplainer
from deic_core.planner import PlannerDecision, PlannerMode
from deic_core.self_model import SelfModel
from benchmark.deic_adapter import DEICBenchmarkAdapter
from experiments.clinical_transfer.adapter import ClinicalDEICAdapter
from experiments.cyber_transfer.adapter import CyberDEICAdapter


def variant_uses_self_model(variant):
    return variant != "no_self_model"


def variant_uses_memory(variant):
    return variant != "no_memory"


def build_memory(variant):
    return CrossEpisodeMemory() if variant_uses_memory(variant) else None


def update_cross_episode_memory(memory, workspace, success):
    if memory is None or not success or workspace is None:
        return
    top_hypotheses = getattr(workspace, "top_hypotheses", [])
    if not top_hypotheses:
        return
    chosen_hypothesis = top_hypotheses[0][0]
    if isinstance(chosen_hypothesis, dict):
        memory.observe_episode_outcome({}, True, chosen_hypothesis)


def extract_planner_trace(outcome, fallback_trace=None):
    decision_trace = outcome.get("decision_trace")
    if decision_trace:
        return decision_trace
    return fallback_trace or None


def build_self_model_snapshot(workspace, variant):
    if workspace is None or not variant_uses_self_model(variant):
        return None
    if not hasattr(workspace, "top_hypotheses"):
        return None
    return SelfModel.from_workspace(workspace)


def build_explanation_trace(workspace, planner_trace, variant):
    if workspace is None or not planner_trace or not variant_uses_self_model(variant):
        return None

    last_step = None
    for entry in reversed(planner_trace):
        mode_name = entry.get("planner_mode")
        if mode_name in PlannerMode.__members__:
            last_step = entry
            break
    if last_step is None:
        return None

    planner_mode = PlannerMode[last_step["planner_mode"]]
    planner_decision = PlannerDecision(
        mode=planner_mode,
        rationale=last_step.get("rationale", ""),
        recommendation=last_step.get("recommendation"),
    )
    action = last_step.get("action") or last_step.get("next_action") or {}
    self_model = SelfModel.from_workspace(workspace)
    explainer = StateExplainer()
    return [explainer.generate_explanation(workspace, self_model, planner_decision, action, style="diagnostic")]


def build_adapter(domain, variant="frozen_full", **overrides):
    shared = {
        "memory": overrides.pop("memory", None),
        "enable_self_model": variant_uses_self_model(variant),
    }

    if variant == "frozen_full":
        common = {
            "adaptive_trust": True,
            "enable_adapt_refine": True,
            "enable_final_contradiction_probe": True,
        }
        if domain == "benchmark":
            return DEICBenchmarkAdapter(use_planner=True, confidence_threshold=0.999, **common, **shared, **overrides)
        if domain == "cyber":
            return CyberDEICAdapter(
                use_planner=True,
                confidence_threshold=0.999,
                coverage_threshold=1.0,
                **common,
                **shared,
                **overrides,
            )
        if domain == "clinical":
            return ClinicalDEICAdapter(
                use_planner=True,
                confidence_threshold=0.999,
                coverage_threshold=1.0,
                **common,
                **shared,
                **overrides,
            )

    if variant == "no_planner":
        if domain == "benchmark":
            return DEICBenchmarkAdapter(
                adaptive_trust=True,
                use_controller=True,
                confidence_threshold=0.999,
                **shared,
                **overrides,
            )
        if domain == "cyber":
            return CyberDEICAdapter(
                adaptive_trust=True,
                use_controller=True,
                confidence_threshold=0.999,
                coverage_threshold=1.0,
                **shared,
                **overrides,
            )
        if domain == "clinical":
            return ClinicalDEICAdapter(
                adaptive_trust=True,
                use_controller=True,
                confidence_threshold=0.999,
                coverage_threshold=1.0,
                **shared,
                **overrides,
            )

    if variant == "no_self_model":
        common = {
            "adaptive_trust": True,
            "enable_adapt_refine": True,
            "enable_final_contradiction_probe": True,
        }
        if domain == "benchmark":
            return DEICBenchmarkAdapter(use_planner=True, confidence_threshold=0.999, **common, **shared, **overrides)
        if domain == "cyber":
            return CyberDEICAdapter(
                use_planner=True,
                confidence_threshold=0.999,
                coverage_threshold=1.0,
                **common,
                **shared,
                **overrides,
            )
        if domain == "clinical":
            return ClinicalDEICAdapter(
                use_planner=True,
                confidence_threshold=0.999,
                coverage_threshold=1.0,
                **common,
                **shared,
                **overrides,
            )

    if variant == "no_memory":
        common = {
            "adaptive_trust": True,
            "enable_adapt_refine": True,
            "enable_final_contradiction_probe": True,
        }
        shared["memory"] = None
        if domain == "benchmark":
            return DEICBenchmarkAdapter(use_planner=True, confidence_threshold=0.999, **common, **shared, **overrides)
        if domain == "cyber":
            return CyberDEICAdapter(
                use_planner=True,
                confidence_threshold=0.999,
                coverage_threshold=1.0,
                **common,
                **shared,
                **overrides,
            )
        if domain == "clinical":
            return ClinicalDEICAdapter(
                use_planner=True,
                confidence_threshold=0.999,
                coverage_threshold=1.0,
                **common,
                **shared,
                **overrides,
            )

    if variant == "no_adaptation":
        common = {
            "adaptive_trust": True,
            "enable_adapt_refine": False,
            "enable_final_contradiction_probe": False,
        }
        if domain == "benchmark":
            return DEICBenchmarkAdapter(use_planner=True, confidence_threshold=0.999, **common, **shared, **overrides)
        if domain == "cyber":
            return CyberDEICAdapter(
                use_planner=True,
                confidence_threshold=0.999,
                coverage_threshold=1.0,
                **common,
                **shared,
                **overrides,
            )
        if domain == "clinical":
            return ClinicalDEICAdapter(
                use_planner=True,
                confidence_threshold=0.999,
                coverage_threshold=1.0,
                **common,
                **shared,
                **overrides,
            )

    if variant == "no_safety_circuit":
        if domain == "benchmark":
            return DEICBenchmarkAdapter(
                adaptive_trust=True,
                use_planner=False,
                use_controller=False,
                **shared,
                **overrides,
            )
        if domain == "cyber":
            return CyberDEICAdapter(
                adaptive_trust=True,
                use_planner=False,
                use_controller=False,
                **shared,
                **overrides,
            )
        if domain == "clinical":
            return ClinicalDEICAdapter(
                adaptive_trust=True,
                use_planner=False,
                use_controller=False,
                **shared,
                **overrides,
            )

    raise ValueError(f"Unsupported adapter variant '{variant}' for domain '{domain}'.")
