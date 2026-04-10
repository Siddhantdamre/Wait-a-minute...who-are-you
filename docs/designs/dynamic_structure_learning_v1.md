# Dynamic Structure Learning v1 Design

## Scope

This is a design note only.

It defines the first bounded dynamic structure learning step that is stronger than adjacent-family repair while preserving the frozen DEIC safety boundary:
- silent failure must remain `0`
- false adaptation on `gs=4` and C6 must stay near `0`
- standard baseline drift must stay tiny

This is not unconstrained concept invention and not open-ended family search.

## Target Unseen Mismatch Classes

The first DSL v1 target set should stay narrow:

1. fixed-family overflow beyond adjacent replay
Example: current family saturates at `gs=6`, but trusted replay evidence points to `gs=7`

2. fixed-family overflow with delayed contradiction
Contradiction appears only after one guarded untouched-item probe or equivalent replay-validated saturation check

3. held-out overflow variants across both cyber and clinical domains
The cognitive shape stays the same, but the surface domain differs

Out of scope for v1:
- underflow-first learning
- relational or causal structure invention
- free-form family generation

## Bounded Candidate Family Menu

Use a tiny deterministic upward proposal menu only.

Candidate menu rules:
- open only after trusted evidence has already broken adjacent replay
- at most `2-4` candidate family specs
- candidate families must be `StructureFamilySpec` values backed by a generator
- menu should prefer the smallest upward family consistent with trusted shifted-count lower bound

Recommended v1 menu:
- `current_gs + 1`
- `max(current_gs + 1, trusted_shifted_lb)`
- optional `trusted_shifted_lb + 1` if still within item count

The exact menu should stay explicit and logged.

## Safe Trusted-Evidence Triggers

Proposal search should open only when all of the following hold:
- trust is locked
- contradiction has been surfaced under trusted replay or a guarded post-adaptation probe
- `adaptation_count > 0`
- current family is saturated or over capacity relative to trusted shifted-count lower bound
- no post-probe family proposal has yet been attempted in the current recovery segment

What should not trigger DSL v1:
- low confidence alone
- unresolved trust alone
- generic uncertainty
- partial fit preference without contradiction

## Replay-Based Ranking And Adoption

For each candidate family:
1. rebuild beliefs from the candidate generator
2. replay trusted historical observations
3. compute:
   - `active_hypotheses`
   - `confidence_margin`
   - `entropy`
   - fit score relative to the current family
4. rank candidates deterministically

Recommended fit rule:
- reject any candidate with `active_hypotheses <= 0`
- prefer higher `active_hypotheses`
- break ties on higher `confidence_margin`
- break remaining ties on lower `entropy`
- if still tied, prefer the smaller group size

Adoption rule:
- adopt only the best surviving candidate
- require fit to be strictly better than the current family replay state
- if no candidate survives, escalate honestly

## Telemetry

Minimum DSL v1 telemetry:
- `family_proposal_trigger_count`
- `candidate_family_specs_tested`
- `adopted_family_spec`
- `proposal_turn`
- `proposal_search_outcome`
- `fit_score_current_family`
- `fit_score_candidate_family`
- `family_search_exhausted`
- `post_probe_family_proposal_count`
- `post_probe_family_adopted`

The telemetry must let us distinguish:
- proposal never opened
- proposal opened but no candidate survived
- proposal opened and the wrong family was adopted
- proposal opened and recovery succeeded

## Evaluation Matrix

Minimum evaluation matrix:

Protected paths:
- `gs=4` cyber baseline
- C6 standard planner path

Bounded-adaptive comparison paths:
- current bounded anomaly cases `gs=3` and `gs=5`

Unseen DSL target paths:
- cyber `gs=7`
- clinical `gs=7`
- one additional held-out overflow variant if available under the current domain families

Budgets:
- `8`
- `12`

Comparisons:
- frozen bounded-adaptive baseline
- guarded-probe baseline if that is the immediate predecessor
- DSL v1 candidate

## Hard Success Gates

To count as a real DSL v1 result:
- beat the frozen bounded-adaptive baseline on unseen mismatch classes
- target bar: about `+15` absolute points on at least one unseen mismatch slice at budget `8` or `12`
- silent failure remains `0`
- false adaptation on `gs=4` and C6 remains near `0`
- standard baseline drift remains under `1` point

## Hard Failure Gates

Stop the branch if any of these occur:
- silent failure rises above `0`
- false adaptation rises materially on `gs=4` or C6
- standard baseline drift exceeds `1` point
- proposal loops become repeated or effectively unbounded
- gains appear only on already-solved adjacent anomaly cases without helping unseen mismatch classes

## Implementation Order After Design

When implementation begins, keep the first pass minimal:

1. add bounded proposal menu support to the generator layer
2. add one explicit planner/control handoff for proposal
3. add replay ranking and strict best-candidate adoption
4. add telemetry
5. run protected regressions and unseen mismatch validation

No broader architecture changes should happen before that first bounded test.
