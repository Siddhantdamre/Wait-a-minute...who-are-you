# DEIC-CogBench v1

DEIC-CogBench v1 packages the frozen DEIC Platform v1 as a runnable benchmark for:

- executive function
- metacognition
- adaptive learning under partial observability
- safety-aware abstention

This is a bounded cognitive benchmark package, not a claim of AGI.

## Code Structure Summary

- `spec.md`: benchmark contract, baseline config, task families, reporting rules
- `splits/train_split.yaml`: canonical train split for baseline, trust, anomaly, and budget/noise coverage
- `splits/heldout_split.yaml`: explicit held-out transfer split
- `tasks/`: thin wrappers over the frozen benchmark, cyber, and clinical environments
- `schemas.py`: frozen task, split, episode, and aggregate schemas
- `scoring.py`: deterministic aggregation, reporting, trace selection, and serialization
- `run_suite.py`: full package runner that emits the combined report and JSON artifact
- `run_ablations.py`: ablation-only runner over the frozen contract

## CLI Contract

`run_suite.py` is the main package command. By default it:

- runs both the train and held-out splits
- includes traces
- includes ablations
- writes outputs to `results/deic_cogbench/`

Key arguments:

- `--train-split`
- `--heldout-split`
- `--output-dir`
- `--max-tasks`
- `--max-episodes`
- `--trace-limit`
- `--no-traces`
- `--skip-ablations`

`run_ablations.py` runs the ablation surface directly and writes `ablations_train.json` into the same output directory.

## Run

```bash
python benchmarks/exec_meta_adapt/run_suite.py
```

Small smoke run:

```bash
python benchmarks/exec_meta_adapt/run_suite.py --max-tasks 2 --max-episodes 2
```

Ablations only:

```bash
python benchmarks/exec_meta_adapt/run_ablations.py --max-tasks 2 --max-episodes 2
```
