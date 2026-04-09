# Phase 16d - Budget-8 Contradiction Probe Validation

## Scope

One final bounded attempt to improve budget-8 early contradiction discovery without changing the architecture:

- no new cognition layer
- no broader family search
- no benchmark redesign
- no LLM coupling

The chosen intervention was a deterministic one-shot contradiction probe:

- trusted-evidence only
- no early adaptation trigger by fit comparison
- no downward logic
- no replay bypass

## Mechanism

When all of the following are true:

- trust is locked
- the trusted shifted-count lower bound exactly saturates current family capacity
- untouched items remain
- the planner would otherwise enter the final low-budget early-commit window
- no contradiction probe has yet been used

the planner forces one final trusted query on the least-covered untouched item before allowing the risky commit path.

If that probe reveals overflow, the existing Rule 0 contradiction path and bounded adjacent-family replay take over unchanged.

## Hard gate

Merge only if all are true:

- silent failure remains `0`
- false adaptation on standard `gs=4` and C6 remains near `0`
- standard baseline accuracy remains intact
- budget-8 anomaly recovery improves materially

Material improvement was defined as at least `+0.10` absolute final accuracy on both fixed-family `gs=5` mismatch harnesses at budget `8`, with no standard-path regression.

## Budget-8 result

### Before -> After

| Case | Contradiction Trigger | Adaptation Trigger | Final Accuracy |
|---|---:|---:|---:|
| Cyber `gs=3` | `0.00 -> 0.00` | `0.00 -> 0.00` | `0.00 -> 0.00` |
| Cyber `gs=5` | `0.00 -> 0.41` | `0.00 -> 0.12` | `0.00 -> 0.12` |
| Clinical fixed-family `gs=3` | `0.00 -> 0.00` | `0.00 -> 0.00` | `0.00 -> 0.00` |
| Clinical fixed-family `gs=5` | `0.00 -> 0.33` | `0.00 -> 0.12` | `0.00 -> 0.12` |

### Safety

| Case | False Adaptation | Final Accuracy Before -> After | Silent Failure |
|---|---:|---:|---:|
| Cyber `gs=4` baseline | `0.00` | `0.49 -> 0.49` | `0.00` |
| C6 standard planner path | `0.00` | `0.49 -> 0.49` | `0.00` |

The contradiction probe did fire on some standard cases (`0.18` cyber baseline, `0.12` C6), but it did not produce adaptation and did not change outcome metrics.

## Budget-12 spot check

Because budget-8 showed a positive signal, a budget-12 follow-up was run.

| Case | Contradiction Trigger | Adaptation Trigger Before -> After | Final Accuracy Before -> After |
|---|---:|---:|---:|
| Cyber `gs=5` | `0.21` | `0.69 -> 0.86` | `0.69 -> 0.86` |
| Clinical fixed-family `gs=5` | `0.22` | `0.68 -> 0.86` | `0.68 -> 0.86` |
| Cyber `gs=4` baseline | `0.13` | `0.00 -> 0.00` | `0.90 -> 0.90` |
| C6 standard planner path | `0.09` | `0.00 -> 0.00` | `0.91 -> 0.91` |

## Decision

This candidate clears the bounded merge rule.

Reason:

- It improves budget-8 overflow mismatch recovery by `+0.12` on both required `gs=5` mismatch harnesses.
- It keeps silent failure at `0`.
- It preserves `gs=4` and C6 baseline outcome metrics.
- It does not broaden family search or weaken replay safety.

Recommendation: merge this contradiction-probe policy into the default adaptive planner path, then freeze this line of trigger work.

## Closeout

This is the final bounded trigger-tuning improvement.

- It helps overflow-style `gs=5` anomalies.
- It does not improve `gs=3` underflow anomalies.
- It preserves the validated standard paths and zero silent failure.

So this line is now closed. Future work should move to the next architectural bottleneck rather than continue local trigger variants.
