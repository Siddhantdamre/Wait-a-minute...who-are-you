# Cognitive Architecture v1

## SECTION 1 - Purpose

Create a layered cognitive architecture that can appraise situations, maintain bounded internal state, run value-aware action checks, and choose among explicit actions with lower architectural ambiguity.

This architecture is not a replacement for the existing DEIC reasoning spine. It is a control layer above it. DEIC remains responsible for hidden-state inference, trust handling, contradiction handling, abstain and escalate behavior, and bounded adaptive recovery. The new architecture adds explicit appraisal, bounded affect-like control state, conscience checks, reflective control, continuity hooks, and structured explanations so future cognition work has clearer boundaries and lower margin for error.

## SECTION 2 - Design principles

- Explicit state over hidden assumptions: every meaningful control signal should exist as named state with a type, range, and consumer.
- Bounded action sets: the controller should choose from a fixed action menu instead of inventing new actions on the fly.
- Replayability: future decisions must be reconstructable from structured snapshots.
- Auditability: no high-level explanation should exist without corresponding internal records.
- One-way information flow where possible: appraisal should feed downstream modules without silent backflow.
- Separation of scoring from action selection: modules may score, label, or constrain, but the controller owns final action choice.
- Safety before cleverness: blocked, abstain, and escalate paths stay first-class rather than fallback afterthoughts.
- Incremental prototyping: future implementation should begin with one narrow insertion point and measurable behavioral change.

## SECTION 3 - Reuse of prior work

### DEIC reasoning spine

What it already provides:
- discrete hidden-state inference
- trust-sensitive evidence integration
- contradiction detection
- abstain and escalate behavior
- bounded adaptive recovery and DSL v1 control flow

What it does not provide:
- explicit appraisal of threat, care, social sensitivity, or moral weight
- bounded affect-like control variables
- values-based action checks
- reflective action policies above current planner modes

How the new architecture depends on it:
- the belief and trust state exposed by DEIC is the epistemic substrate for the new higher layer
- the new controller must never replace DEIC inference math

### Workspace

What it already provides:
- a structured container for current cognitive state
- telemetry and planner-facing state
- an integration point for tracked reasoning outputs

What it does not provide:
- explicit affect state
- explicit conscience state
- continuity records for regret, repair, or unresolved value conflicts

How the new architecture depends on it:
- the future architecture can extend workspace with additional structured records while keeping existing DEIC state intact

### Self-model

What it already provides:
- current goal framing
- uncertainty and limitation summaries
- action justification framing
- counterfactual triggers

What it does not provide:
- value conflict representation
- predicted regret
- actor commitments
- repair-needed state

How the new architecture depends on it:
- the self-model becomes the natural home for bounded reflective identity and conflict summaries

### Planner

What it already provides:
- explicit decision modes
- bounded branching logic
- commitment, contradiction, adaptation, and escalation decisions

What it does not provide:
- a richer action menu beyond current planning outcomes
- values-aware action filtering
- reflective conflict arbitration across epistemic, affective, and normative signals

How the new architecture depends on it:
- the planner remains the main lower-level decision engine, while the new controller sits above it and constrains or redirects certain decision edges

### Memory

What it already provides:
- continuity summaries
- compact carry-forward context

What it does not provide:
- persistent value conflicts
- regret-worthy decision traces
- repair outcomes and repeated harmful patterns

How the new architecture depends on it:
- memory becomes the continuity substrate for self-regulation and repair

### Abstain / escalate logic

What it already provides:
- safe behavior under insufficient evidence, contradiction, or trust failure
- a benchmarked safety circuit already tied to DEIC

What it does not provide:
- explicit distinction between epistemic insufficiency and normative conflict
- reflective justification for why an action is blocked, delayed, or repair-first

How the new architecture depends on it:
- the new layer must integrate with abstain and escalate, not replace them

### Benchmark package

What it already provides:
- a frozen evaluation contract
- metacognitive task patterns
- known failure-mode surfaces

What it does not provide:
- benchmarks for repair, conscience checks, or regret-sensitive control

How the new architecture depends on it:
- future cognition benchmarks should extend existing patterns rather than redefine the frozen benchmark package

## SECTION 4 - Layered architecture

### Layer 1: Appraisal

Inputs:
- current observation or task input
- trust cues
- urgency cues
- retrieved memory context

Outputs:
- structured appraisal vector

Allowed state:
- transient scored event-level state only

Responsibilities:
- convert raw events into bounded control-relevant descriptors
- normalize threat, care, uncertainty, novelty, trust, social sensitivity, and moral weight

Non-responsibilities:
- no action choice
- no belief revision
- no long-term memory writes

Consumed by:
- belief/world state layer
- affect-like control layer
- conscience layer

### Layer 2: Belief / world state

Inputs:
- DEIC inference outputs
- appraisal summary where relevant

Outputs:
- epistemic state for controller consumption

Allowed state:
- hypotheses, trust state, contradiction state, confidence, uncertainty, planner recommendation

Responsibilities:
- preserve the current DEIC world model and planner-facing epistemic state

Non-responsibilities:
- no value judgment
- no emotion-like control state

Consumed by:
- affect layer
- conscience layer
- reflective controller
- explanation layer

### Layer 3: Affect-like control state

Inputs:
- appraisal outputs
- belief confidence and contradiction state
- continuity memory reads

Outputs:
- bounded internal control vector

Allowed state:
- named scalar or categorical control variables only

Responsibilities:
- accumulate and smooth control pressures such as alarm, doubt, suspicion, care weight, and regret risk

Non-responsibilities:
- no direct final action
- no free-form explanation generation

Consumed by:
- conscience layer
- reflective controller
- explanation layer

### Layer 4: Conscience / values checks

Inputs:
- candidate actions
- appraisal
- belief/world state
- affect-like control state
- self-model commitments

Outputs:
- per-action value labels and conflict signals

Allowed state:
- bounded check outcomes and conflict scores

Responsibilities:
- evaluate candidate actions against explicit values such as non-harm, honesty, fairness, respect, responsibility, and repairability

Non-responsibilities:
- no action execution
- no hidden value invention

Consumed by:
- reflective controller
- explanation layer
- continuity memory writes when conflict persists

### Layer 5: Reflective controller

Inputs:
- planner recommendation
- appraisal vector
- belief/world state
- affect state
- conscience results
- self-model state

Outputs:
- bounded final action
- controller rationale record

Allowed state:
- current decision trace and temporary conflict bookkeeping

Responsibilities:
- resolve action choice among the allowed action set
- mediate between epistemic recommendation and normative constraints

Non-responsibilities:
- no silent mutation of lower-layer inference state
- no benchmark-contract redefinition

Consumed by:
- action execution boundary
- explanation layer
- memory writer

### Layer 6: Memory / continuity

Inputs:
- decision trace
- outcomes
- repair records
- unresolved conflicts

Outputs:
- compact continuity context for later episodes or later turns

Allowed state:
- bounded persistent records only

Responsibilities:
- retain trust history, unresolved value conflicts, regret-worthy actions, and successful repair patterns

Non-responsibilities:
- no direct action choice
- no retroactive explanation fabrication

Consumed by:
- appraisal
- affect layer
- self-model
- reflective controller

### Layer 7: Explanation layer

Inputs:
- structured records from all prior layers

Outputs:
- faithful explanation record

Allowed state:
- explanation-ready structured trace only

Responsibilities:
- summarize why the chosen action was taken
- expose blockers, conflicts, and supporting internal signals

Non-responsibilities:
- no fictional motives
- no post hoc moral theater

Consumed by:
- external reporting
- audit tools

## SECTION 5 - Information flow

Default flow:

`input -> appraisal -> belief/world state -> affect/conscience -> controller -> action -> explanation`

Memory reads occur in three places:
- before appraisal, to provide recent trust and continuity context
- before affect update, to smooth repeated patterns
- before controller choice, to surface prior regret or repair history when relevant

Memory writes occur after:
- final action selection
- outcome observation
- detected conflict, repair need, or repeated failure

Allowed feedback loops:
- belief state may update affect state
- affect state may shape conscience sensitivity
- controller outcomes may produce memory writes
- later memory reads may influence future appraisal

Forbidden feedback loops:
- explanation layer may not rewrite earlier states
- conscience layer may not mutate DEIC belief state directly
- affect layer may not directly finalize action
- controller may not silently change benchmark semantics or planner mode meanings

## SECTION 6 - Failure semantics

- Safe commit: commit chosen with adequate epistemic support, no blocking conscience result, and an explanation trace that matches internal state.
- Abstain: action withheld because evidence is insufficient, but no stronger blocker requires escalation.
- Escalate: action handed off because contradiction, trust failure, model limitation, or unresolved value conflict requires outside review.
- Blocked action: a candidate action rejected because one or more value checks or invariants forbid it.
- Repair-needed state: a state indicating a prior error, harm, or broken commitment that should trigger a repair-capable action path.
- Internal conflict: a structured disagreement between epistemic confidence, affective pressure, value checks, or self-model commitments.
- Regret-worthy action: an action predicted to be hard to endorse after outcome review because it carries high avoidable harm, dishonesty, or responsibility failure.
- Explanation-ready state: a decision state with enough structured evidence to produce a faithful explanation.

## SECTION 7 - Replayability and audit

A future implementation should make each decision replayable from a compact structured record containing:
- input snapshot
- appraisal snapshot
- belief snapshot
- affect snapshot
- conscience result
- self-model snapshot
- controller action
- explanation record

Replay must allow an auditor to answer:
- what the system believed
- what it appraised as threatening, uncertain, or morally weighty
- which value checks constrained the action
- why the final action was allowed
- whether a later explanation is faithful to the original state

The architecture should prefer append-only decision traces so post hoc editing cannot silently rewrite why a decision was made.

## SECTION 8 - Why this reduces error

This architecture lowers error in concrete ways.

First, it reduces hidden coupling. Appraisal, belief, affect, conscience, and action choice are separated instead of mixed into one opaque control step.

Second, it clarifies module boundaries. Each layer has explicit responsibilities and explicit non-responsibilities, which lowers the chance that later prototypes silently duplicate or override DEIC logic.

Third, it makes decisions auditable. A replayable decision trace lets later evaluation distinguish between epistemic failure, value conflict, controller conflict, and explanation failure.

Fourth, it keeps action selection bounded. A fixed action menu reduces improvisational behavior and makes prototype evaluation sharper.

Fifth, it supports faithful explanations. Because explanation consumes structured records rather than inventing free-form motives, the system has less room to bluff about why it acted.
