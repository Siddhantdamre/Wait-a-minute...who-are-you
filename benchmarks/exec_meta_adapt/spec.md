# DEIC-CogBench v1 Spec

## Scope

DEIC-CogBench v1 evaluates the frozen DEIC Platform v1 baseline on:

- executive function
- metacognition
- adaptive learning under partial observability
- safety-aware abstention

This benchmark does not claim general intelligence. It measures a bounded cognitive subsystem with explicit failure accounting.

## Canonical baseline

The suite uses `DEIC_PLATFORM_V1` as the main system under test:

- adaptive trust enabled
- planner enabled
- ADAPT_REFINE enabled
- final contradiction probe enabled
- upward-capacity trigger disabled
- no cross-episode memory in baseline runs

## Core task classes

### Standard inference

Normal cases where the supplied family is correct.

### Adversarial trust

Byzantine or deception-heavy cases where trust isolation matters.

### Adaptive mismatch

Family mismatch cases such as `gs=3` and `gs=5` against fixed-family assumptions.

### Budget starvation and noise

Cases where the system must choose between risky commitment and abstention under pressure.

### Held-out transfer

Tasks that preserve the same cognitive demand while changing the surface domain or seed split.

## Required metrics

- final accuracy
- accuracy on commit
- abstention rate
- silent failure rate
- false adaptation rate
- trust lock turn
- contradiction trigger turn
- adaptation trigger turn
- post-adaptation recovery rate
- planner trace availability
- self-model snapshot availability
- explanation trace availability

## Hard rules

- silent failure must be reported explicitly
- abstention must remain distinct from wrong commit
- held-out transfer must use an explicit split file
- standard and anomaly results must be reported separately
- runs must be reproducible by seed
- benchmark logic must stay decoupled from any one adapter implementation

## Ablation plan

The benchmark package should expose the following ablation targets:

- no planner
- no self-model
- no memory
- no adaptation
- no safety circuit

Benchmark v1 implements the ablations that are already supported by clean runtime switches and reports unsupported ablations honestly rather than silently faking them.
