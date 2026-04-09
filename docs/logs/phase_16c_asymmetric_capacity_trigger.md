# Phase 16c - Asymmetric Capacity Trigger

## 1. Failure explanation

Phase 16b tested a symmetric partial-fit trigger: before total collapse, compare the current family against adjacent families using only the currently replayable trusted evidence, then adapt if an adjacent family appears to fit better.

That shape recovered some anomaly cases earlier, but it also introduced a structural bias. Under partial coverage, smaller families can concentrate support faster because they explain a narrower support pattern with fewer open degrees of freedom. This means that when trusted evidence is still incomplete, a smaller adjacent family can look artificially cleaner than the true current family even on ordinary `gs=4` episodes.

That is why the Phase 16b trigger produced false adaptations on standard `gs=4` baseline cases and on the C6 planner path. The problem was not random noise and not post-adaptation execution. The problem was the trigger shape itself: "best adjacent family under partial evidence" is not safety-aligned because partial evidence does not symmetrically penalize under-capacity and over-capacity families.

Conclusion: Phase 16b is a valid negative result and should remain unmerged. Symmetric partial-fit comparison under partial coverage is unsafe as a default early-adaptation trigger.

## 2. Asymmetric trigger design

Phase 16c should replace generic adjacent-family comparison with a smaller and safer question:

"Has trusted replayable evidence already crossed a structural-capacity boundary that the current family cannot explain?"

This trigger should be:

- Trusted-evidence only: use only evidence from sources that have already cleared the trust gate.
- Directional: reason separately about upward and downward structural pressure rather than comparing all adjacent families symmetrically.
- Bounded: if triggered, only test the immediately adjacent family in the indicated direction.
- Conservative: do not adapt because another family looks cleaner under partial evidence; adapt only because the current family is already structurally impossible or tightly contradicted.

Design sketch for v1:

1. Build a trusted-evidence summary from replayable observations only.
2. Derive directional structural-capacity constraints implied by that evidence under the current family.
3. Trigger only if the current family violates one directional constraint with high certainty.
4. Search only the adjacent family in that direction.
5. Preserve existing replay validation and post-adaptation validation exactly as in the current adaptive path.

This is safer than symmetric partial-fit comparison because it asks whether the current family has become impossible, not whether another family looks temporarily sharper under sparse evidence.

## 3. Candidate trigger forms

Only narrow candidate forms should be considered here.

Observed shifted-count exceeding current family capacity:
Use trusted observations to infer a lower bound on the number of shifted items. If that lower bound exceeds the current family capacity, trigger upward adaptation. This is the cleanest upward trigger because it only fires when the current family cannot contain what trusted evidence already forces.

Trusted lower-bound / upper-bound support mismatch:
Maintain trusted lower and upper bounds on feasible shifted support size. Trigger upward when the lower bound exceeds current capacity. Trigger downward only when the upper bound falls strictly below current capacity and remains stable after replay. This is useful, but downward triggering is more fragile because partial evidence often leaves many unobserved explanations alive.

Asymmetrical family-capacity contradiction test:
Replay trusted evidence against the current family while measuring whether any hypothesis in the current family can still satisfy the directional capacity bounds. Trigger only when the family is contradicted by capacity, not merely outscored. This is the most faithful formulation if it can be implemented without adding a new architecture layer.

Upward-only or downward-only trigger rules:
An upward-only v1 is the safest serious option if the anomaly cases of interest are dominated by under-capacity failures such as true `gs=5` under a fixed `gs=4` family. Downward triggers can be added later only if they can be made equally conservative.

Safest v1 choice:
Use an asymmetrical family-capacity contradiction test with an upward-only trigger as the initial merge candidate.

Reason:

- It directly targets the failure mode Phase 16b exposed.
- It avoids the small-family bias created by symmetric partial-fit concentration.
- It fits the main anomaly types already observed.
- It minimizes false adaptation pressure on normal `gs=4` baseline cases.
- It keeps the implementation bounded to adjacent-family search and existing replay validation.

Downward triggering should stay out of v1 unless a comparably strict contradiction rule appears necessary after the upward-only pass is measured.

## 4. Safety constraints

The trigger must satisfy all of the following:

- Preserve silent failure = 0. If the trigger fires, the system must still go through replay validation and then the existing adaptive execution path. No silent structural swap.
- Keep false adaptation near 0 on standard `gs=4` baseline and C6 planner-integrated paths.
- Never bypass replay validation.
- Never trigger from unresolved trust.
- Never trigger from mixed trusted and untrusted evidence.
- Never broaden family search beyond the single adjacent family in the indicated direction.
- Never degrade standard baseline behavior just to gain anomaly recall.
- Fail closed: if the capacity signal is ambiguous, do not adapt early.

## 5. Evaluation plan

Run paired before/after evaluation on the existing adaptive harnesses, comparing the current default adaptive path against the new asymmetric pre-collapse trigger.

Required cases:

- Cyber `gs=3` anomaly
- Cyber `gs=5` anomaly
- Clinical fixed-family mismatch cases
- `gs=4` standard baseline
- C6 standard planner path

Execution plan:

1. Measure the current pre-collapse behavior on all required cases.
2. Add the asymmetric capacity trigger with adjacent-family search only in the indicated direction.
3. Re-run the same budgets and seeds used in the existing anomaly validation harnesses.
4. Keep replay validation, `ADAPT_REFINE`, and final commit logic unchanged so the intervention is isolated to trigger timing.
5. Compare anomaly recovery against baseline preservation, with baseline preservation treated as the primary gate.

## 6. Metrics

Track the following metrics for each case and budget:

- Pre-collapse trigger rate
- Adaptation trigger rate
- Final accuracy
- Escalation rate
- Wrong-commit rate
- False adaptation rate
- Baseline regression preservation

Interpretation guidance:

- Pre-collapse trigger rate shows whether the new signal activates earlier than total collapse.
- Adaptation trigger rate shows how often a pre-collapse signal survives replay validation.
- Final accuracy measures whether earlier triggering creates real recovery rather than noise.
- Escalation rate shows whether the system still fails closed when evidence is insufficient.
- Wrong-commit rate detects unsafe early commits after adaptation.
- False adaptation rate is the primary safety metric on standard `gs=4` and C6 paths.
- Baseline regression preservation is the merge gate: anomaly gains do not matter if the frozen standard paths drift.

## 7. Merge rule

Merge the new trigger into the default adaptive path only if all of the following hold:

- False adaptation remains effectively zero on standard `gs=4` baseline and C6 standard planner paths.
- No meaningful regression appears in standard baseline final accuracy or wrong-commit rate.
- Replay validation remains intact and no silent structural swap is introduced.
- The trigger improves recovery on at least one fixed-family mismatch class in a repeatable way.
- The improvement comes from earlier safe triggering rather than weakened safety thresholds.
- The implementation adds no new architecture layer, no broader family search, no LLM coupling, and no benchmark redesign.

If those conditions are not met, keep Phase 16c as another bounded negative result rather than relaxing safety.
