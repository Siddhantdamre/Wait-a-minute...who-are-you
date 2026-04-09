# DEIC Platform v1 Freeze

This document defines the canonical frozen subsystem baseline that future benchmark work should evaluate rather than reshape.

---

## Purpose

Stop architecture churn.

Define a stable bounded cognitive subsystem that can serve as:

- the benchmark baseline
- the source of controlled ablations
- the protected reference point for future adaptive-learning work

---

## What Is Frozen

### Frozen platform components

- DEIC core inference engine
- hypothesis generator framework
- belief inspector
- commit controller
- cross-episode memory implementation
- tool and action interface
- global workspace
- self-model
- minimal planner
- safe explanation and safe LLM rendering layer

### Frozen safety conclusions

- silent blind commits are eliminated
- escalation is operational, not decorative
- abstention is analytically distinct from wrong commit
- the platform behaves honestly under ambiguity

### Frozen adaptive conclusions

- cyber transfer is established
- clinical transfer is established
- bounded family adaptation is established
- ADAPT_REFINE is the default bounded adaptive execution policy for validated fixed-family domains
- the one-shot contradiction probe is the final merged bounded trigger-tuning improvement

---

## Protected Evaluation Guards

These checks remain mandatory:

- C6 golden regression
- cyber transfer regression
- clinical transfer regression
- planner, workspace, inspector, and controller tests
- silent failure must remain `0`
- false adaptation on standard cases must remain near `0`

---

## Canonical Baseline Config

Benchmark packaging should use one explicit baseline config rather than drifting between phase-specific defaults.

### DEIC_PLATFORM_V1

- `adaptive_trust=True`
- `use_planner=True`
- `enable_adapt_refine=True`
- `enable_final_contradiction_probe=True`
- `enable_upward_capacity_trigger=False`
- benchmark planner confidence threshold fixed to the current validated setting
- transfer coverage threshold fixed to the current validated setting
- cross-episode memory disabled for benchmark v1 per-episode baselines so runs stay independent and reproducible

This choice keeps the frozen bounded-adaptive path intact while avoiding cross-episode leakage in the first public benchmark release.

---

## Explicit Non-Goals

DEIC Platform v1 is not:

- a claim of AGI
- a general early-contradiction solution
- open-ended structure invention
- relational or causal reasoning
- long-horizon interactive world modeling

Those belong to later milestones.

---

## Done Criteria

Milestone 0 is complete when:

- the bounded adaptive path is frozen
- negative-result trigger branches remain archived rather than merged
- frozen regression checks remain green
- the canonical benchmark baseline config is documented
- future work targets benchmark packaging or new capability layers rather than local trigger tuning
