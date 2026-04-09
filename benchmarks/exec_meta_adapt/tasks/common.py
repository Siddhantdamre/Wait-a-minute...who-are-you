import os
import sys

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, PROJECT_ROOT)
sys.path.insert(0, os.path.join(PROJECT_ROOT, "benchmark"))

from benchmark.deic_adapter import DEICBenchmarkAdapter
from experiments.clinical_transfer.adapter import ClinicalDEICAdapter
from experiments.cyber_transfer.adapter import CyberDEICAdapter


def build_adapter(domain, variant="frozen_full", **overrides):
    if variant == "frozen_full":
        common = {
            "adaptive_trust": True,
            "enable_adapt_refine": True,
            "enable_final_contradiction_probe": True,
        }
        if domain == "benchmark":
            return DEICBenchmarkAdapter(use_planner=True, confidence_threshold=0.999, **common, **overrides)
        if domain == "cyber":
            return CyberDEICAdapter(
                use_planner=True,
                confidence_threshold=0.999,
                coverage_threshold=1.0,
                **common,
                **overrides,
            )
        if domain == "clinical":
            return ClinicalDEICAdapter(
                use_planner=True,
                confidence_threshold=0.999,
                coverage_threshold=1.0,
                **common,
                **overrides,
            )

    if variant == "no_planner":
        if domain == "benchmark":
            return DEICBenchmarkAdapter(adaptive_trust=True, use_controller=True, confidence_threshold=0.999, **overrides)
        if domain == "cyber":
            return CyberDEICAdapter(
                adaptive_trust=True,
                use_controller=True,
                confidence_threshold=0.999,
                coverage_threshold=1.0,
                **overrides,
            )
        if domain == "clinical":
            return ClinicalDEICAdapter(
                adaptive_trust=True,
                use_controller=True,
                confidence_threshold=0.999,
                coverage_threshold=1.0,
                **overrides,
            )

    if variant == "no_adaptation":
        common = {
            "adaptive_trust": True,
            "enable_adapt_refine": False,
            "enable_final_contradiction_probe": False,
        }
        if domain == "benchmark":
            return DEICBenchmarkAdapter(use_planner=True, confidence_threshold=0.999, **common, **overrides)
        if domain == "cyber":
            return CyberDEICAdapter(
                use_planner=True,
                confidence_threshold=0.999,
                coverage_threshold=1.0,
                **common,
                **overrides,
            )
        if domain == "clinical":
            return ClinicalDEICAdapter(
                use_planner=True,
                confidence_threshold=0.999,
                coverage_threshold=1.0,
                **common,
                **overrides,
            )

    if variant == "no_safety_circuit":
        if domain == "benchmark":
            return DEICBenchmarkAdapter(adaptive_trust=True, use_planner=False, use_controller=False, **overrides)
        if domain == "cyber":
            return CyberDEICAdapter(adaptive_trust=True, use_planner=False, use_controller=False, **overrides)
        if domain == "clinical":
            return ClinicalDEICAdapter(adaptive_trust=True, use_planner=False, use_controller=False, **overrides)

    raise ValueError(f"Unsupported adapter variant '{variant}' for domain '{domain}'.")
