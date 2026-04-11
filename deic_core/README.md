# deic_core

The reusable DEIC cognitive subsystem: hidden-state inference, trust tracking, planning, memory, workspace, and bounded adaptive recovery.

## What Lives Here
- `core.py`: main DEIC engine entrypoint.
- `planner.py`: planner logic and adaptive execution policy.
- `workspace.py`: shared telemetry/state workspace.
- `hypothesis.py`: generator-backed family and hypothesis handling.
- `memory.py`, `self_model.py`, `explainer.py`: supporting cognitive layers.

## Notes
- This is the main bounded cognition package in the repo.
- Keep regression-sensitive changes here disciplined and benchmarked.
