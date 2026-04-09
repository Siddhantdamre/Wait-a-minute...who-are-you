from benchmarks.exec_meta_adapt.run_suite import DEFAULT_HELDOUT_SPLIT, DEFAULT_TRAIN_SPLIT, load_split
from benchmarks.exec_meta_adapt.run_ablations import SUPPORTED_ABLATIONS
from benchmarks.exec_meta_adapt.schemas import (
    ANOMALY_TASK_CLASSES,
    BASELINE_TASK_CLASSES,
    CONTRACT_VERSION,
    TRANSFER_TASK_CLASSES,
)


def _task_classes(split_spec):
    return {task.task_class for task in split_spec.tasks}


def _domains(split_spec):
    return {task.domain for task in split_spec.tasks}


def test_benchmark_split_contract_versions():
    train_split = load_split(DEFAULT_TRAIN_SPLIT)
    heldout_split = load_split(DEFAULT_HELDOUT_SPLIT)

    assert train_split.contract_version == CONTRACT_VERSION
    assert heldout_split.contract_version == CONTRACT_VERSION
    assert train_split.split == "train"
    assert heldout_split.split == "heldout"


def test_benchmark_split_coverage():
    train_split = load_split(DEFAULT_TRAIN_SPLIT)
    heldout_split = load_split(DEFAULT_HELDOUT_SPLIT)

    assert BASELINE_TASK_CLASSES.issubset(_task_classes(train_split))
    assert ANOMALY_TASK_CLASSES.issubset(_task_classes(train_split))
    assert TRANSFER_TASK_CLASSES == _task_classes(heldout_split)

    package_domains = _domains(train_split) | _domains(heldout_split)
    assert package_domains == {"benchmark", "cyber", "clinical"}


def test_supported_ablation_surface_is_frozen():
    assert SUPPORTED_ABLATIONS == [
        "frozen_full",
        "no_planner",
        "no_self_model",
        "no_memory",
        "no_adaptation",
        "no_safety_circuit",
    ]
