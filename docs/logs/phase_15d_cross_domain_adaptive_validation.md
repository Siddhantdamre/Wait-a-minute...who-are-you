# Phase 15d - Cross-Domain Adaptive Validation

## Goal

Validate whether the guarded `ADAPT_REFINE` recovery policy generalizes beyond the original cyber anomaly harness, and decide whether it is safe to make it the default adaptive execution policy for bounded generator-backed domains.

## Scope

- No new architecture layer
- No broader family-search expansion
- No changes to core posterior math
- No LLM coupling or benchmark redesign
- Focus only on the execution policy after successful bounded family adoption

## Core Intervention

The winning intervention was narrow:

1. Keep bounded adjacent-family search unchanged.
2. After successful adoption, clear the resolved structural-contradiction suspicion spike for the trusted source.
3. Enter `ADAPT_REFINE`.
4. Spend one focused post-adaptation validation query.
5. Allow commit under the adapted family without waiting for the original pre-adaptation coverage target.

This changed post-adaptation behavior without changing the frozen inference math.

## Validation Matrix

Before/after comparisons were run on:

- Cyber fixed-family anomalies: `gs=3`, `gs=5`
- Clinical closest structural mismatch harness using a fixed-family `gs=4` generator against true `gs=3` and `gs=5` episodes
- Cyber `gs=4` standard baseline
- Planner-integrated C6 standard path

Budgets studied: `8`, `12`, `16`, `20`

## Key Results

| Case | Budget 12 Before -> After | Budget 16 Before -> After |
|---|---|---|
| Cyber `gs=3` anomaly | `0.00 -> 0.46` | `0.37 -> 0.91` |
| Cyber `gs=5` anomaly | `0.00 -> 0.69` | `0.58 -> 0.99` |
| Clinical fixed-family `gs=3` mismatch | `0.00 -> 0.44` | `0.35 -> 0.90` |
| Clinical fixed-family `gs=5` mismatch | `0.00 -> 0.68` | `0.60 -> 0.96` |
| Cyber `gs=4` baseline | `0.90 -> 0.90` | `1.00 -> 1.00` |
| C6 standard planner path | `0.91 -> 0.91` | `1.00 -> 1.00` |

The earlier bottleneck was post-adaptation escalation, not family ranking. Once the planner stopped treating the resolved Rule 0 contradiction as an unresolved suspicion spike, bounded adaptation became useful at realistic budgets.

## Guard Checks

The following guard suites still passed after propagation:

```bash
python tests/test_golden_c6.py
python tests/test_transfer_regression.py
python -m pytest tests/test_planner.py tests/test_workspace.py tests/test_inspector.py tests/test_controller.py -q
```

## Merge Decision

`ADAPT_REFINE` should be the default adaptive execution policy for generator-backed fixed-family domains.

Reason:

- It materially improves adaptive recovery in the bounded family setting.
- It preserves frozen baseline behavior where adaptation never triggers.
- It does not require broader family search, threshold retuning, or posterior changes.

## Remaining Bottleneck

The next constrained problem is budget-8 contradiction discovery.

At tight budgets, the system still often fails before it detects the structural mismatch. The next phase should therefore target earlier contradiction discovery rather than more family-search complexity or a new architecture layer.
