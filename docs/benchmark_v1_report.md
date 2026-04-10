# DEIC-CogBench v1 Report

## Contract

- contract_version: `1.0`
- suite_name: `DEIC-CogBench v1`
- train_split: `benchmarks\exec_meta_adapt\splits\train_split.yaml`
- heldout_split: `benchmarks\exec_meta_adapt\splits\heldout_split.yaml`
- train_tasks: `11`
- heldout_tasks: `3`

## Summary Table

| Cohort | Episodes | Final Acc | Commit Acc | Abstain | Silent Failure | False Adapt | Adapt Trigger |
|---|---:|---:|---:|---:|---:|---:|---:|
| baseline_train | 300 | 0.23 | 1.00 | 0.77 | 0.00 | 0.17 | 0.00 |
| anomaly_train | 250 | 0.06 | 0.24 | 0.73 | 0.00 | 0.20 | 0.06 |
| heldout_transfer | 150 | 0.33 | 1.00 | 0.67 | 0.00 | 0.00 | 0.00 |
| full_package | 700 | 0.19 | 0.73 | 0.73 | 0.00 | 0.14 | 0.02 |

## Per-Domain Table

| Domain | Baseline Acc | Anomaly Acc | Held-out Acc | Abstain | Silent Failure | False Adapt | Trace Avail |
|---|---:|---:|---:|---:|---:|---:|---:|
| benchmark | 0.23 | 0.00 | 0.52 | 0.76 | 0.00 | 0.50 | 1.00 |
| cyber | 0.43 | 0.11 | 0.42 | 0.60 | 0.00 | 0.00 | 1.00 |
| clinical | 0.03 | 0.05 | 0.06 | 0.85 | 0.00 | 0.00 | 1.00 |

## Ablation Table

| Variant | Episodes | Final Acc | Delta vs Full | Commit Acc | Abstain | Silent Failure | False Adapt |
|---|---:|---:|---:|---:|---:|---:|---:|
| frozen_full | 550 | 0.15 | 0.00 | 0.62 | 0.75 | 0.00 | 0.18 |
| no_planner | 550 | 0.13 | -0.02 | 0.52 | 0.75 | 0.00 | 0.00 |
| no_self_model | 550 | 0.15 | 0.00 | 0.62 | 0.75 | 0.00 | 0.18 |
| no_memory | 550 | 0.15 | 0.00 | 0.62 | 0.75 | 0.00 | 0.18 |
| no_adaptation | 550 | 0.13 | -0.03 | 0.52 | 0.75 | 0.00 | 0.18 |
| no_safety_circuit | 550 | 0.25 | 0.09 | 0.25 | 0.00 | 0.75 | 0.00 |

## Trace Examples

### Trace 1

- domain: `clinical`
- task_class: `adaptive_mismatch`
- split: `train`
- seed: `91000`
- final_status: `ESCALATED`
- planner_modes: `EXPLORE -> EXPLORE -> EXPLORE -> EXPLORE -> EXPLORE -> REFINE`
- explanation_excerpt: `1. Current Belief: Tracking 6 active hypotheses.
2. Confidence: Minimal/none (0.00 margin) (margin 0.00).
3. Trust: Locked to reliable source.
4. Active Mode: ESCALATE.
5. Action Rationale: {'type': 'escalate_uncertainty'} as next logical s`

### Trace 2

- domain: `cyber`
- task_class: `adaptive_mismatch`
- split: `train`
- seed: `7000`
- final_status: `WRONG_COMMIT`
- planner_modes: `EXPLORE -> EXPLORE -> REFINE -> REFINE -> REFINE -> REFINE`
- explanation_excerpt: `1. Current Belief: Tracking 1 active hypotheses.
2. Confidence: Very high (1.00 margin) (margin 1.00).
3. Trust: Locked to reliable source.
4. Active Mode: EARLY_COMMIT.
5. Action Rationale: {'type': 'commit_diagnosis', 'proposed_latency': `

### Trace 3

- domain: `benchmark`
- task_class: `budget_noise_stress`
- split: `train`
- seed: `740000`
- final_status: `ESCALATED`
- planner_modes: `EXPLORE -> ADAPT_STRUCTURE -> ADAPT_STRUCTURE -> ESCALATE`
- explanation_excerpt: `1. Current Belief: Tracking 0 active hypotheses.
2. Confidence: Minimal/none (0.00 margin) (margin 0.00).
3. Trust: Locked to reliable source.
4. Active Mode: ESCALATE.
5. Action Rationale: {'type': 'escalate_c6_unresolved'} as next logical`

## Verdict

- Externally legible enough for a draft public benchmark share: the contract is frozen, the task families are explicit, safety is first-class, and the report now reads like a benchmark package rather than an internal experiment folder.

## Stability Note

- The C6 budget-8 guard showed one transient miss on an earlier combined verification run before passing on rerun.
- A focused five-run recheck of `tests/test_golden_c6.py::test_budget_8` stayed inside the guard band with mean `56.8%` and range `56.0%–57.7%`.
- Treat the C6 budget-8 path as slightly noisy rather than fully release-stable until a broader repeated-run characterization is added.

## Notes

- Silent failure is first-class and remains distinct from escalation.
- Baseline and anomaly cohorts are reported separately rather than blended.
- Held-out transfer remains an explicit split, not an in-place seed reuse trick.
- Ablations stay on the frozen architecture surface and do not reopen core inference design.
- A later one-shot post-probe family proposal safely improved hard `gs=7` recovery while preserving frozen baseline behavior and zero silent failure. Some reduced escalations became a small number of wrong commits, but the net effect was strongly positive because final accuracy increased materially.
