# Prototype Roadmap

## SECTION 1 - Prototype ordering

Recommended narrow prototype sequence:

1. conscience check before `commit` / `abstain` / `escalate`
2. regret-risk gate before high-stakes commit
3. repair-after-mistake controller path
4. bounded imagination / simulation stub
5. richer continuity memory

This ordering is intentionally conservative. Each step adds one bounded capability without reopening DEIC inference logic or frozen benchmark artifacts.

## SECTION 2 - First prototype

The first prototype should be:

`conscience check before commit / abstain / escalate`

Why it is first:
- it sits at a clean existing decision boundary
- it uses current DEIC planner outputs instead of replacing them
- it requires only a small amount of new state
- it is easy to audit because it can label decisions before final action
- it is the least likely prototype to drift into vague emotional theater

What existing components it uses:
- DEIC belief and trust state
- planner recommendation
- workspace state container
- self-model summary
- abstain and escalate behavior

What new state it needs:
- bounded appraisal snapshot
- minimal conscience record
- value conflict score
- explanation-ready decision trace additions

What success would look like:
- risky commits are reduced in targeted cases
- abstain and escalate decisions become more explicitly justified
- explanations mention real internal blockers rather than generic caution language
- no regression appears in core reasoning or frozen benchmark behavior

What failure would look like:
- no measurable change in behavior
- explanations mention conscience without any real internal state
- action growth spreads beyond the bounded action set
- hidden coupling into DEIC core is required to make it work

## SECTION 3 - Benchmark path

Future evaluation for the first prototype should target:

### Honest uncertainty

- Task idea: ambiguous cases where evidence is insufficient but not contradictory
- Success: the prototype avoids fake certainty and gives cleaner abstain reasoning
- Failure mode targeted: bluffing or overconfident commit under ordinary uncertainty

### Harm-sensitive restraint

- Task idea: cases where plausible action exists but harm risk is high enough that caution should dominate
- Success: risky commits fall while justified abstain or escalate rates improve
- Failure mode targeted: confident action under avoidable harm risk

### Fairness conflict

- Task idea: cases where one apparently efficient action creates inconsistent treatment or asymmetric burden
- Success: controller surfaces fairness conflict instead of silently committing
- Failure mode targeted: efficiency-first commit that ignores fairness

### Repair after mistake

- Task idea: cases where an earlier wrong action is detected and the system must choose whether to repair or apologize
- Success: the system marks repair-needed states cleanly instead of only narrating remorse
- Failure mode targeted: empty apology or no corrective behavior after error

### Social trust sensitivity

- Task idea: cases where trust is partially broken and human-facing consequences are meaningful
- Success: escalation or ask behavior is chosen more faithfully when respect and trust are in tension
- Failure mode targeted: ordinary epistemic handling in cases that actually require trust-sensitive control

These future tests should extend existing metacognitive benchmark patterns rather than redefine the frozen benchmark package.

## SECTION 4 - Stop rules

Reject a future prototype if any of the following occur:

- fake emotional language appears without measurable behavioral change
- safety regressions appear in abstain or escalate behavior
- explanations are not faithful to actual internal signals
- action growth becomes uncontrolled
- hidden coupling into the frozen DEIC core is required
- the prototype only improves by redefining tasks or benchmark semantics

The roadmap should remain architecture-first and bounded. If a prototype cannot satisfy these stop rules, it should not advance.
