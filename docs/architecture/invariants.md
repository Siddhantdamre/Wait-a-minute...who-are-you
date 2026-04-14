# Architectural Invariants

This document defines hard invariants for the cognitive architecture line. These are not style preferences. They are constraints that future implementations should satisfy to remain explicit, bounded, auditable, and compatible with the frozen DEIC and benchmark layers.

## Core invariants

- No action without an explicit decision trace.
- No explanation without corresponding internal signals.
- No conscience explanation without a real conscience-state record.
- No escalation without an identified blocker, contradiction, or value conflict.
- No repair action without a prior failure or conflict record.
- No new state variable without a defined type, range, default, and consumer.
- No layer may silently redefine benchmark semantics.
- No module may both evaluate and finalize action without an audit trail.
- Frozen DEIC core and frozen benchmark artifacts are immutable in this phase.

## Replay invariants

- Every action must be reconstructable from a structured snapshot sequence.
- Replay records must include at minimum:
  - input snapshot
  - appraisal snapshot
  - belief snapshot
  - affect snapshot
  - conscience result
  - self-model snapshot
  - controller action
  - explanation record
- Replay must not depend on free-form prose alone.
- Later explanation code may summarize a replay record but may not replace the underlying structured record.
- If an action cannot be replayed, it must be treated as an architecture failure.

## Safety invariants

- No conscience layer may weaken existing abstain or escalate safety behavior by default.
- No high-confidence commit may bypass contradiction, trust failure, or blocked conscience status.
- No urgency signal may erase a low-trust warning without an explicit controller trace.
- No apology or repair action may substitute for actually blocking or escalating a dangerous decision.
- No future affect signal may be used to justify riskier action without an explicit supporting record.

## Module-boundary invariants

- Appraisal may score and normalize inputs, but it may not choose actions.
- Belief/world state may represent epistemic state, but it may not emit moral or affective judgments on its own.
- Affect-like state may bias caution and prioritization, but it may not finalize action.
- Conscience may classify candidate actions, but it may not execute them.
- The controller may choose among allowed actions, but it may not silently mutate lower-layer epistemic state.
- The explanation layer may summarize structured records, but it may not create new justification state.
- Memory may preserve past outcomes, but it may not retroactively rewrite prior decisions.

## Explanation-faithfulness invariants

- No explanation may mention a blocker, conflict, regret, or value unless the corresponding state was recorded at decision time.
- No explanation may use conscience language if the conscience layer did not actually participate in the decision.
- No explanation may present anthropomorphic motives as if they were literal inner experiences.
- No explanation may claim certainty if belief or self-model state recorded high uncertainty.
- No explanation may use apology or empathy language unless a real repair or social-failure record exists.

## Action invariants

- `commit` requires sufficient epistemic support and no blocked conscience state.
- `abstain` requires explicit insufficiency without a stronger escalation trigger.
- `escalate` requires an identified blocker, contradiction, trust failure, limitation, or unresolved value conflict.
- `ask` requires a named missing information target.
- `delay` requires a reason why waiting is safer than acting now.
- `repair` requires a prior failure or harm record.
- `apologize` requires a prior social failure or trust breach record.
- `reconsider` requires a named changed condition or conflict.

## Schema invariants

- Every new state field must define:
  - meaning
  - type
  - range or enum values
  - default
  - update source
  - consumer modules
- No schema may contain hidden free-form fields that later become de facto logic inputs without contract documentation.
- No state field may be introduced solely for explanation style.

## Benchmark and freeze invariants

- Frozen benchmark tasks, prompts, scoring, and submission artifacts remain untouched in this phase.
- No architecture document may quietly reinterpret the existing benchmark contract.
- No future prototype may claim success by changing benchmark semantics instead of changing behavior.
- DSL v1 and bounded adaptive recovery remain historical checkpoints and are not reopened here.

## Anti-theater invariants

- No affect-like state may be marketed or described as real emotion.
- No conscience layer may be described as consciousness.
- No module may use moral language as a bluffing shield for ordinary uncertainty.
- No repair or apology action may be emitted without behavioral substance.
- No actor-identity language may substitute for measurable control behavior.

## Audit invariants

- A reviewer must be able to tell which layer contributed which decision signal.
- A reviewer must be able to distinguish epistemic failure from normative conflict.
- A reviewer must be able to tell whether a final action was blocked, allowed, or redirected by conscience.
- A reviewer must be able to inspect whether an explanation was faithful to the actual trace.

## Rejection invariant

Any future prototype that violates these invariants should be rejected, even if it appears more human-like, because the goal of this architecture phase is lower error and clearer control flow, not theatrical surface behavior.
