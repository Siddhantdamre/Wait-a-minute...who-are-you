# DEIC-CogBench v1

DEIC-CogBench v1 is the first benchmark packaging layer for the current DEIC platform.

It evaluates a bounded cognitive subsystem across:

- executive function
- metacognition
- adaptive learning under partial observability
- safety-aware abstention

The suite is built around the frozen DEIC Platform v1 baseline defined in [docs/milestones/deic_platform_v1.md](../../docs/milestones/deic_platform_v1.md).

## Layout

- `spec.md`: benchmark goals, task classes, hard rules, and baseline config
- `tasks/`: runnable task wrappers for C6, cyber, and clinical domains
- `splits/`: explicit train and held-out split definitions
- `schemas.py`: unified per-episode and aggregate result schemas
- `scoring.py`: normalization, aggregation, and report rendering
- `run_suite.py`: one-command benchmark runner
- `run_ablations.py`: benchmark ablation runner
- `results/`: JSON outputs from suite runs

## Run

```bash
python benchmarks/exec_meta_adapt/run_suite.py
```

For a small smoke run:

```bash
python benchmarks/exec_meta_adapt/run_suite.py --max-tasks 2 --max-episodes 5
```
