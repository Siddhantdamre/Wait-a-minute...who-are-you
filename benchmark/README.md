# benchmark

Legacy benchmark harnesses, adapters, and utilities for the earlier executive-function evaluation path.

## What Lives Here
- `environment.py`: C3-C6 style benchmark environment logic.
- `deic_adapter.py`: bridge between DEIC and the benchmark environment.
- `run_evaluation.py`, `run_lean.py`, `run_c6_v3_pilot.py`: evaluation entrypoints.
- `solvers.py`: legacy solver implementations and comparisons.

## Notes
- This folder supports the older benchmark ladder and compatibility runs.
- The newer benchmark packaging work lives under `benchmarks/`.
