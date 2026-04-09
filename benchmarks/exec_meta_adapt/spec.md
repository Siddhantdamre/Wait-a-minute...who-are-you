# DEIC-CogBench v1 Spec

## Benchmark Spec Summary

DEIC-CogBench v1 evaluates the frozen DEIC Platform v1 as a bounded cognitive subsystem. The package is designed to be:

- runnable from one command
- schema-stable
- safety-explicit
- cross-domain comparable
- reproducible by seed

It measures a bounded platform, not open-ended intelligence.

## Contract Version

- `contract_version = 1.0`
- frozen domains: `benchmark`, `cyber`, `clinical`
- frozen task classes:
  - `standard_inference`
  - `adversarial_trust`
  - `adaptive_mismatch`
  - `budget_noise_stress`
  - `heldout_transfer`
- frozen ablation surface:
  - `frozen_full`
  - `no_planner`
  - `no_self_model`
  - `no_memory`
  - `no_adaptation`
  - `no_safety_circuit`

## Canonical Baseline

The suite uses `DEIC_PLATFORM_V1` as the main system under test:

- adaptive trust enabled
- planner enabled
- ADAPT_REFINE enabled
- final contradiction probe enabled
- upward-capacity trigger disabled
- benchmark confidence thresholds fixed to the validated settings
- cross-episode memory enabled within each task stream and reset between task specs

This keeps the frozen bounded-adaptive architecture intact while making the memory layer benchmark-visible instead of only archival.

## Split Format

Each split file is JSON-compatible YAML with:

- `contract_version`
- `suite_name`
- `split`
- `notes`
- `tasks`

Each task entry freezes:

- task wrapper name
- domain
- task class
- split
- episode count
- budget
- seed offset
- adapter variant
- optional condition
- optional group size
- notes

## Task Inventory

### Train split

- standard inference
- adversarial trust
- adaptive mismatch
- budget/noise stress

### Held-out split

- held-out transfer with disjoint seeds across all three domains

## Episode Result Schema

Every episode record includes:

- domain
- task name
- task class
- split
- adapter variant
- seed
- budget
- final status
- accuracy
- committed
- abstained
- silent failure
- false adaptation
- trust lock turn
- contradiction trigger turn
- adaptation trigger turn
- planner trace availability
- self-model snapshot availability
- explanation trace availability
- optional planner trace
- optional self-model snapshot
- optional explanation trace
- metadata

## Reporting Outputs

The package report must emit:

- one summary table
- one per-domain table
- one ablation table
- one small set of trace examples
- one blunt verdict on external legibility

## Hard Rules

- silent failure must be reported explicitly
- abstention must remain distinct from wrong commit
- baseline and anomaly cohorts must remain separated in reporting
- held-out transfer must stay in an explicit split file
- outputs must be reproducible by seed
- default run artifacts must stay outside committed source paths
- benchmark work must not modify DEIC core inference logic
