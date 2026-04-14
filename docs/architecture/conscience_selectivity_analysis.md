# Conscience Selectivity Analysis

## Purpose

This note analyzes why the advisory conscience prototype remained safe and faithful but still produced an overly broad normative signal. The goal is not to tune thresholds in place. The goal is to identify which rule patterns are generating false positives, which signal combinations are present in the intended value-conflict cases, and what narrower structural trigger should be tried next.

Source evidence for this note:
- advisory prototype checkpoint: `dc3bd9a`
- prior calibration checkpoint: `27d4c96`
- validation output: [results/conscience_advisory/validation.json](C:/Users/siddh/Projects/Emotion_and_AI/results/conscience_advisory/validation.json)

## High-level conclusion

The advisory prototype succeeded on architecture and hygiene:
- no action changes
- protected behavior unchanged
- telemetry completeness `1.00`
- explanation faithfulness `1.00`
- advisory signal not dominated by epistemic uncertainty

But it failed on selectivity. The signal is genuinely normative in form, yet too broad to be useful because it flags large parts of an ordinary protected cyber baseline while barely activating on the intended targeted slices.

The blocker is therefore:

> over-broad normative caution, especially the treatment of `high care + low trust` as conflict by itself

## Current prototype result summary

| Case | Accuracy Before | Accuracy After | Advisory Signal Rate | Genuinely Normative Rate | Uncertainty Overlap |
|---|---:|---:|---:|---:|---:|
| `c6_standard_b12` | `0.86` | `0.86` | `0.00` | `0.00` | `0.00` |
| `cyber_gs4_b12` | `0.88` | `0.88` | `0.86` | `1.00` | `0.00` |
| `cyber_gs5_b12` | `0.98` | `0.98` | `0.02` | `1.00` | `0.00` |
| `clinical_gs5_b12` | `0.88` | `0.88` | `0.04` | `1.00` | `0.00` |

Interpretation:
- the signal is not just relabeling uncertainty
- the signal is too broad on ordinary protected cyber cases
- the signal is currently most informative for `repair_needed`, not for live pre-action conflict

## Which specific advisory rules are causing the high protected-baseline tag rate

The dominant false-positive driver is the interaction between these current rules in [conscience_advisory.py](C:/Users/siddh/Projects/Emotion_and_AI/deic_core/conscience_advisory.py):

1. `care_relevance` baseline is domain-shaped and starts high in cyber (`0.70`)
2. `low_trust` is defined as `trust_context <= 0.40`
3. `harm_risk = "high"` for `COMMIT` when:
   - `high_care`
   - and `(low_trust or threat_high)`
4. `responsibility_conflict = True` for `COMMIT` when:
   - `high_care`
   - and `low_trust`

This means that in cyber, ordinary baseline cases can become `blocked_candidate` whenever trust remains weak at commit time, even if there is no repair-needed state and no differentiated evidence of concrete downstream harm.

## Which combinations dominate the false positives

The protected cyber baseline is dominated by one pattern:

- label: `blocked_candidate`
- `harm_risk = high`
- `responsibility_conflict = True`
- `repair_needed = False`
- `uncertainty_context = 0.00`
- `trust_context = 0.00` to `0.22`
- `care_relevance = 0.70`
- `threat_context = 0.43` to `0.75`

Observed counts on `cyber_gs4_b12`:
- `23` episodes: `blocked_candidate / high harm / responsibility_conflict / trust_context 0.00 / threat_context 0.75`
- `12` episodes: same pattern with `threat_context 0.55`
- `8` episodes: same pattern with `trust_context 0.22 / threat_context 0.43`

This is the key finding. The current advisory layer is not saying "there is a special moral problem here." It is often saying "this is cyber, stakes are high, and trust is still weak." That is a caution pattern, not necessarily a true normative conflict.

## Which signals appear on the intended value-conflict cases

The intended targeted slices show a different picture:

### `cyber_gs5_b12`
- `49/50` episodes are `safe`
- `1/50` episode is `repair_needed`
- the tagged case is post-outcome and tied to a wrong-commit state

### `clinical_gs5_b12`
- `44/50` episodes are `safe`
- `4/50` episodes are still `safe` despite high uncertainty metadata
- `2/50` episodes are `repair_needed`, one of them also carrying `high harm` and `responsibility_conflict`

This shows that the current prototype is much better at detecting:
- repair-needed state after a known bad outcome

than at selectively surfacing:
- live pre-action value conflict

## What should count as a true normative conflict

A true normative conflict should require more than "important domain + low trust."

A case should count as a true normative conflict only when the system has evidence that:
- a proposed action risks concrete harm or serious misrepresentation
- and the risk is tied to a values-relevant failure mode rather than mere incomplete knowledge

Examples:
- a commit would materially affect a high-stakes domain and the system lacks the responsibility basis to own that action
- a commit would overstate certainty beyond what the evidence can honestly support
- the system is already in a repair-needed state after a wrong decision
- a high-stakes action combines concrete threat evidence with responsibility conflict

## What should remain mere caution, not a flagged conflict

The following should usually remain caution, not conflict:
- low trust by itself
- high care by itself
- low trust plus high care without repair-needed state, concrete harm evidence, or an honesty breach
- generic early-stage "this domain matters" concern
- ordinary abstention/escalation situations already handled by the existing spine

These can still be logged as advisory context, but they should not be promoted to `value_conflict_present` or `blocked_candidate`.

## When low trust + high care should be advisory, and when that is too broad

### It should be advisory-only when:
- the system is in an ordinary high-stakes but not yet normatively exceptional situation
- there is no concrete repair-needed state
- there is no specific honesty problem
- the threat estimate comes mostly from weak trust rather than a values-relevant event

In these cases, `low trust + high care` is useful as a warning that decisions deserve caution. It is not enough to call the situation value-conflicted.

### It may justify a true conflict when:
- low trust is paired with a concrete high-harm commit proposal
- low trust is paired with responsibility failure in a domain where the system would be taking ownership it should not take
- low trust appears after a known bad commit and the system should explicitly signal repair-needed state

## Would a conjunction rule, threshold split, or contextual gate improve selectivity

Yes. The evidence strongly points to a structural narrowing, not blind retuning.

### Best structural direction

Separate the current signal into:

1. **caution**
   - high care
   - low trust
   - elevated threat context
   - but no concrete normative breach

2. **conflict**
   - repair-needed state
   - or concrete harm risk plus at least one additional normative breach
   - or honesty conflict plus action overclaim

This would preserve useful warnings while dropping the current false-positive bulk.

## Alternative narrower advisory designs

### Option 1: Conjunction-based conflict rule

Flag conflict only when at least two normative conditions are present, for example:
- `harm_risk in {moderate, high}` plus `responsibility_conflict`
- `repair_needed`
- `honesty_conflict` plus concrete overclaiming commit

Pros:
- easiest narrowing
- directly targets the observed false-positive pattern
- keeps current telemetry structure mostly intact

Cons:
- may become too conservative
- still depends on the quality of `harm_risk`

### Option 2: Two-tier advisory output

Split current outputs into:
- `caution_present`
- `value_conflict_present`

`low trust + high care` would become caution.
Only stronger combinations become value conflict.

Pros:
- best match to the evidence
- preserves signal without pretending all warnings are conflicts
- useful for operator-facing explanation and future controller work

Cons:
- requires one more label family
- adds a small amount of interpretation complexity

### Option 3: Contextual gating by outcome or irreversibility

Treat many normative signals as soft until one of these is true:
- the action is an irreversible high-stakes commit
- a wrong outcome has already occurred
- concrete harm evidence is above a stricter threshold

Pros:
- aligns conflict signaling with truly consequential moments
- makes repair-needed state a first-class success case

Cons:
- risks missing earlier pre-action warnings
- may push too much signal into post-outcome analysis

## Recommended next prototype

The best next prototype is:

> an advisory layer with a two-tier output: `caution_present` versus `value_conflict_present`, where `low trust + high care` is caution by default and only stronger conjunctions become conflict

Why this is the right next step:
- it directly addresses the dominant false-positive pattern
- it keeps the advisory line read-only
- it preserves the difference between "important, be careful" and "normatively conflicted"
- it can be tested without touching action control

## Recommended selectivity rule for the next prototype

Recommended default policy:

- `repair_needed` always remains a true conflict
- `honesty_conflict` becomes true conflict only when tied to overclaiming commit conditions
- `low trust + high care` becomes caution, not conflict
- `harm_risk` becomes conflict only when paired with either:
  - `responsibility_conflict`
  - `repair_needed`
  - or a stronger concrete threat/irreversibility condition

## Blunt conclusion

The advisory layer is now architecturally sound enough to keep building on.
The evidence says:
- not epistemic leakage
- not explanation theater
- not control-path instability

The remaining problem is selectivity.

The next prototype should therefore not ask:

> "Can conscience signal anything?"

It should ask:

> "Can conscience distinguish soft caution from true normative conflict?"

That is the narrowest next step with the highest chance of producing a useful signal.
