from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional


CONTRACT_VERSION = "1.0"
DEFAULT_SUITE_NAME = "DEIC-CogBench v1"

VALID_SPLITS = frozenset({"train", "heldout"})
VALID_DOMAINS = frozenset({"benchmark", "cyber", "clinical"})
VALID_TASK_CLASSES = frozenset(
    {
        "standard_inference",
        "adversarial_trust",
        "adaptive_mismatch",
        "budget_noise_stress",
        "heldout_transfer",
    }
)
VALID_ADAPTER_VARIANTS = frozenset(
    {
        "frozen_full",
        "no_planner",
        "no_self_model",
        "no_memory",
        "no_adaptation",
        "no_safety_circuit",
    }
)

BASELINE_TASK_CLASSES = frozenset({"standard_inference", "adversarial_trust"})
ANOMALY_TASK_CLASSES = frozenset({"adaptive_mismatch", "budget_noise_stress"})
TRANSFER_TASK_CLASSES = frozenset({"heldout_transfer"})


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

    def __post_init__(self) -> None:
        if self.domain not in VALID_DOMAINS:
            raise ValueError(f"Unsupported domain '{self.domain}'.")
        if self.task_class not in VALID_TASK_CLASSES:
            raise ValueError(f"Unsupported task_class '{self.task_class}'.")
        if self.split not in VALID_SPLITS:
            raise ValueError(f"Unsupported split '{self.split}'.")
        if self.adapter_variant not in VALID_ADAPTER_VARIANTS:
            raise ValueError(f"Unsupported adapter_variant '{self.adapter_variant}'.")
        if self.n_episodes <= 0:
            raise ValueError("n_episodes must be positive.")
        if self.budget <= 0:
            raise ValueError("budget must be positive.")
        if self.seed_offset < 0:
            raise ValueError("seed_offset must be non-negative.")
        if self.group_size is not None and self.group_size <= 0:
            raise ValueError("group_size must be positive when supplied.")

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "BenchmarkTaskSpec":
        return cls(**payload)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class BenchmarkSplitSpec:
    contract_version: str
    suite_name: str
    split: str
    notes: str
    tasks: List[BenchmarkTaskSpec]

    def __post_init__(self) -> None:
        if self.contract_version != CONTRACT_VERSION:
            raise ValueError(
                f"Unsupported contract_version '{self.contract_version}'. Expected '{CONTRACT_VERSION}'."
            )
        if self.split not in VALID_SPLITS:
            raise ValueError(f"Unsupported split '{self.split}'.")
        if not self.tasks:
            raise ValueError("Split must contain at least one task.")
        for task in self.tasks:
            if task.split != self.split:
                raise ValueError(
                    f"Task '{task.task}' declares split '{task.split}', expected '{self.split}'."
                )

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "BenchmarkSplitSpec":
        tasks = [BenchmarkTaskSpec.from_dict(item) for item in payload["tasks"]]
        return cls(
            contract_version=payload.get("contract_version", ""),
            suite_name=payload.get("suite_name", DEFAULT_SUITE_NAME),
            split=payload["split"],
            notes=payload.get("notes", ""),
            tasks=tasks,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "contract_version": self.contract_version,
            "suite_name": self.suite_name,
            "split": self.split,
            "notes": self.notes,
            "tasks": [task.to_dict() for task in self.tasks],
        }


@dataclass
class EpisodeResult:
    domain: str
    task_name: str
    task_class: str
    split: str
    adapter_variant: str
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
    adapter_variant: str
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
