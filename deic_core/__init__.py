"""
DEIC — Discrete Executive Inference Core

A reusable cognitive subsystem for hidden-state belief revision
under partial observability with adversarial sources and tight
query budgets.
"""

from .core import DEIC
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
    "HypothesisGenerator",
    "FixedPartitionGenerator",
    "VariablePartitionGenerator",
    "benchmark_generator",
    "cyber_generator",
    "clinical_generator",
]
