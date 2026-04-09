# Phase 16c - Upward Capacity Trigger Validation

## Goal

Validate the narrowest safe Phase 16c trigger:

- trusted-evidence only
- upward-only
- replay-validated
- bounded to the next adjacent family

The implementation rule was:

Trigger pre-collapse adaptation only when the trusted shifted-count lower bound strictly exceeds the current fixed-family capacity.

## Implementation scope

- Added workspace telemetry for:
  - trusted shifted-count lower bound
  - current family capacity
  - precollapse capacity-trigger turn
  - trigger direction
- Added a planner rule for upward-only capacity triggering
- Restricted pre-collapse adaptation to the next larger adjacent family only
- Left Rule 0 total-collapse adaptation and replay validation intact
- Did not add any downward trigger

## Evaluation cases

Compared `enable_upward_capacity_trigger=False` vs `True` on:

- Cyber fixed-family mismatch `gs=5`
- Clinical fixed-family mismatch `gs=5`
- Cyber `gs=4` standard baseline
- C6 standard planner path

Budgets tested: `8`, `12`, `16`, `20`

## Results

### Core finding

The new trigger was safe but inert.

- False adaptation remained `0.0` on the tested `gs=4` baseline and C6 standard planner paths.
- Silent failure remained `0.0`.
- Final accuracy and escalation rates on the standard paths were unchanged.
- `gs=5` anomaly recovery was also unchanged because the pre-collapse trigger rate stayed `0.0` at every tested budget.

### Before vs after summary

| Case | Budget | Precollapse Trigger Before -> After | Final Accuracy Before -> After |
|---|---:|---:|---:|
| Cyber `gs=5` | 8 | `0.00 -> 0.00` | `0.00 -> 0.00` |
| Cyber `gs=5` | 12 | `0.00 -> 0.00` | `0.69 -> 0.69` |
| Cyber `gs=5` | 16 | `0.00 -> 0.00` | `0.99 -> 0.99` |
| Cyber `gs=5` | 20 | `0.00 -> 0.00` | `1.00 -> 1.00` |
| Clinical `gs=5` | 8 | `0.00 -> 0.00` | `0.00 -> 0.00` |
| Clinical `gs=5` | 12 | `0.00 -> 0.00` | `0.68 -> 0.68` |
| Clinical `gs=5` | 16 | `0.00 -> 0.00` | `0.96 -> 0.96` |
| Clinical `gs=5` | 20 | `0.00 -> 0.00` | `1.00 -> 1.00` |
| Cyber `gs=4` baseline | 12 | `0.00 -> 0.00` | `0.90 -> 0.90` |
| C6 standard planner path | 12 | `0.00 -> 0.00` | `0.91 -> 0.91` |

## Interpretation

This trigger shape is safer than Phase 16b because it never rewards smaller families under partial coverage.

However, under the current query-update loop it appears to become true only on the same observation that collapses the fixed family. Once the trusted source reveals a fifth shifted item under a `gs=4` family, the posterior has already hit Rule 0 total contradiction. That leaves no measurable pre-collapse window for the planner to exploit.

So Phase 16c v1 produced:

- useful telemetry
- a clean upward-only safety rule
- no baseline harm
- no earlier adaptation benefit

## Merge decision

Do not merge this trigger into the default adaptive path in its current form.

Reason:

- It satisfies the safety side of the merge rule.
- It does not satisfy the benefit side because `gs=5` anomaly recovery did not improve materially.

The branch is still useful because it narrows the problem further: a strict trusted lower-bound capacity trigger is safe, but within the current action timing it is operationally inert.
