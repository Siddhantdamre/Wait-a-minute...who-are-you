from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class BenchmarkTaskSpec:
    task: str
    domain: str
    task_class: str
    split: str
    n_episodes: int
    budget: int
    seed_offset: int
    adapter_variant: str = "frozen_full"
    condition: Optional[str] = None
    group_size: Optional[int] = None
    notes: str = ""

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "BenchmarkTaskSpec":
        return cls(**payload)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class EpisodeResult:
    domain: str
    task_name: str
    task_class: str
    split: str
    seed: int
    budget: int
    final_status: str
    accuracy: float
    committed: bool
    abstained: bool
    silent_failure: bool
    false_adaptation: bool
    trust_lock_turn: Optional[int]
    contradiction_trigger_turn: Optional[int]
    adaptation_trigger_turn: Optional[int]
    planner_trace_available: bool
    self_model_snapshot_available: bool
    explanation_trace_available: bool
    planner_trace: Optional[List[Dict[str, Any]]] = None
    self_model_snapshot: Optional[Dict[str, Any]] = None
    explanation_trace: Optional[List[str]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class TaskAggregate:
    task_name: str
    domain: str
    task_class: str
    split: str
    n_episodes: int
    final_accuracy: float
    accuracy_on_commit: float
    abstention_rate: float
    silent_failure_rate: float
    false_adaptation_rate: float
    avg_trust_lock_turn: Optional[float]
    contradiction_trigger_rate: float
    adaptation_trigger_rate: float
    post_adaptation_recovery_rate: float
    planner_trace_availability: float
    self_model_snapshot_availability: float
    explanation_trace_availability: float

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
