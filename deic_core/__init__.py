"""
DEIC — Discrete Executive Inference Core

A reusable cognitive subsystem for hidden-state belief revision
under partial observability with adversarial sources and tight
query budgets.
"""

from .core import DEIC
from .inspector import BeliefInspector
from .controller import CommitController
from .memory import CrossEpisodeMemory
from .interface import ToolInterface
from .workspace import CognitiveState
from .self_model import SelfModel
from .planner import MinimalPlanner, PlannerMode, PlannerDecision
from .explainer import StateExplainer
from .hypothesis import (
    HypothesisGenerator,
    FixedPartitionGenerator,
    VariablePartitionGenerator,
    benchmark_generator,
    cyber_generator,
    clinical_generator,
)

__all__ = [
    "DEIC",
    "BeliefInspector",
    "CommitController",
    "CrossEpisodeMemory",
    "ToolInterface",
    "CognitiveState",
    "SelfModel",
    "MinimalPlanner",
    "PlannerMode",
    "PlannerDecision",
    "StateExplainer",
    "HypothesisGenerator",
    "FixedPartitionGenerator",
    "VariablePartitionGenerator",
    "benchmark_generator",
    "cyber_generator",
    "clinical_generator",
]
