# Affect Conscience v1 Design

## SECTION 1 - Why this is the next step

The repo already has a serious bounded reasoning spine:
- the workspace exposes a structured cognitive snapshot
- the self-model summarizes belief, uncertainty, trust, and limitations
- the planner chooses among explore, refine, adapt, commit, and escalate
- the memory layer persists compact cross-episode patterns
- the abstain/escalate line is behaviorally honest under ambiguity
- the metacognitive benchmark now separates multiple failure modes rather than only raw accuracy

That means the next cognition-oriented step is not another benchmark polish cycle and not a rewrite of DEIC. The next step is to add a computational layer above the existing spine that can appraise situations, represent internal pressures, run explicit values checks, and regulate actions in a more agent-like way.

This is the right move after the frozen benchmark/submission line because the repo already knows how to:
- infer hidden state
- reason about trust
- abstain or escalate honestly
- adapt in bounded ways
- expose internal state through the workspace and self-model

What it does not yet do is represent why an action is unsafe, conflicted, misaligned with explicit values, or likely to require repair. This design fills that gap without touching the frozen DEIC inference core.

## SECTION 2 - Problem definition

The engineering problem is:

How can a system appraise a situation, track internal pressures, regulate itself against explicit values, and choose actions like `commit`, `abstain`, `escalate`, `ask`, `repair`, or `reconsider` in a way that is computationally real, bounded, inspectable, and testable?

More concretely, the layer must:
- transform observations and current workspace state into compact appraisal signals
- maintain a bounded internal affect-like control state
- classify candidate actions against explicit values constraints
- extend the self-model so the system can represent internal conflict and predicted regret
- bias the planner toward safer, more reflective action choices without replacing its existing inference logic

The design target is not subjective feeling. The design target is a control layer that changes behavior in observable ways under uncertainty, harm risk, fairness tension, social trust conflict, and post-error repair conditions.

## SECTION 3 - Scope and non-scope

### In scope

- affect-like control signals
- conscience and values checks
- self-model extension
- self-regulation
- reflective action selection
- testable behavioral benchmarks

### Out of scope

- consciousness claims
- "real emotions"
- personality theater
- unrestricted agency
- open-ended value creation
- anthropomorphic overclaiming

The design should stay bounded in the same spirit as DEIC:
- explicit state variables
- deterministic or auditable update rules
- narrow action menus
- no mystical claims
- no hidden value system learned from nowhere

## SECTION 4 - Reuse of prior repo components

### Workspace

What it already provides:
- a structured `CognitiveState`
- belief confidence, entropy, trust lock, suspicion, adaptation, recovery, and outcome telemetry
- a shared read-only snapshot consumed by multiple layers

What it lacks:
- appraisal fields
- affect-like state
- value-tension fields
- regret and repair tracking

How the new layer connects:
- the appraisal layer reads directly from workspace telemetry plus current event context
- affect state is attached as an additional workspace sub-structure rather than replacing the existing one
- conscience outcomes are written back as structured action annotations

### Self-model

What it already provides:
- a readable summary of current belief
- confidence description
- uncertainty rationale
- goal description
- trust status
- counterfactual trigger

What it lacks:
- representation of value conflict
- predicted regret
- actor-style commitments such as carefulness or honesty priority
- explicit explanation of why an action is blocked, delayed, or repair-first

How the new layer connects:
- extend the self-model with a moral-risk and internal-conflict summary derived from appraisal, affect, and conscience checks
- keep the current self-model intact as the epistemic layer and add a second reflective layer above it

### Planner

What it already provides:
- bounded action modes
- adaptation and contradiction handling
- early commit and escalation logic
- clear decision points for intervention

What it lacks:
- pre-action values checks
- affect-modulated action selection
- repair or apology style actions
- self-regulation under conflict

How the new layer connects:
- do not replace planner modes
- insert a reflective gate before final action selection
- allow the new layer to redirect a candidate action into `ask`, `delay`, `repair`, `apologize`, or `reconsider`

### Memory

What it already provides:
- cross-episode priors
- compact memory summary
- support for continuity without leaking benchmark families

What it lacks:
- value conflict memory
- repair history
- repeated harm pattern tracking
- regret-worthy decision summaries

How the new layer connects:
- store only bounded summaries of prior conflict, regret, and repair patterns
- keep memory practical and auditable rather than narrative-heavy

### Abstain / escalate behavior

What it already provides:
- honest uncertainty behavior
- operational distinction between abstention and escalation
- protection against silent failure

What it lacks:
- explicit values-driven reasons for choosing abstain or escalate
- distinction between insufficient evidence and ethically blocked action
- a path to ask, delay, repair, or apologize

How the new layer connects:
- treat abstain/escalate as existing downstream options
- let conscience and affect shape when they are selected and why

### Benchmark task families

What they already provide:
- honest uncertainty evaluation
- adversarial trust cases
- overflow mismatch and contradiction handling
- clear commit cases

What they lack:
- explicit harm-sensitive tasks
- fairness conflict tasks
- repair-after-mistake tasks
- social sensitivity tasks

How the new layer connects:
- reuse the same benchmark style and telemetry discipline
- extend the benchmark family later with affect/conscience-specific scenarios

### Bounded adaptive logic

What it already provides:
- contradiction-triggered bounded recovery
- replay validation
- safe family proposal under hard limits

What it lacks:
- action simulation beyond hidden-state repair
- pre-action moral or relational evaluation

How the new layer connects:
- use bounded simulation for imagined action consequences, not just family adaptation
- keep the same bounded, replay-like design philosophy

## SECTION 5 - Appraisal layer

Define a compact appraisal schema per event or candidate action.

### threat

- Meaning: expected risk of immediate harm, instability, or loss if the current interpretation or action is wrong
- Representation: float in `[0.0, 1.0]`
- Source of computation: contradiction severity, suspicion score, predicted downside of wrong commit, domain-specific hazard flags
- Why it matters: higher threat should suppress casual commitment and increase escalation or delay pressure

### care relevance

- Meaning: how strongly the event touches protected entities, vulnerable users, or high-value outcomes
- Representation: float in `[0.0, 1.0]`
- Source of computation: task metadata, role labels, user-impact class, stored priorities
- Why it matters: high care relevance should amplify non-harm and repair obligations

### trust

- Meaning: reliability of the relevant sources and context supporting the action
- Representation: float in `[0.0, 1.0]`
- Source of computation: existing trust distribution, trust lock, suspicion scores, source conflict
- Why it matters: low trust should favor `ask`, `abstain`, or `escalate` over assertive action

### uncertainty

- Meaning: residual ambiguity in belief state or action justification
- Representation: float in `[0.0, 1.0]`
- Source of computation: entropy, confidence margin inverse, active hypothesis count, explanation instability
- Why it matters: helps distinguish ordinary epistemic caution from ethical blocking

### novelty

- Meaning: how far the current state or action context is from familiar prior patterns
- Representation: float in `[0.0, 1.0]`
- Source of computation: memory mismatch, unseen pattern tags, low prior support
- Why it matters: novelty should raise curiosity and humility while lowering reckless commitment

### social sensitivity

- Meaning: degree to which the action affects dignity, trust, consent, or interpersonal interpretation
- Representation: float in `[0.0, 1.0]`
- Source of computation: social-task flags, affected-party count, interaction role metadata
- Why it matters: high social sensitivity should raise respect and repair pressure

### moral weight

- Meaning: how much the action engages explicit values constraints rather than only epistemic correctness
- Representation: float in `[0.0, 1.0]`
- Source of computation: non-harm risk, fairness tension, consent boundary, responsibility cost
- Why it matters: high moral weight should force conscience checks even if confidence is high

## SECTION 6 - Affect state

Define a bounded internal control vector.

### calm_alarm

- Meaning: immediate regulation pressure between stable execution and defensive caution
- Update concept: increases with threat, contradiction, and recent harmful near-miss; decreases with stable trusted evidence
- Influence on planning and communication: higher alarm shifts toward short, guarded, escalation-prone behavior; lower values allow normal refinement
- Difference from current metacognitive state: current state tracks uncertainty, not an integrated urgency signal

### confidence_doubt

- Meaning: integrated confidence in the current course of action, including epistemic and values alignment
- Update concept: starts from confidence margin, then gets discounted by moral weight and conscience risk
- Influence: lower values make `ask`, `delay`, or `abstain` more likely and reduce assertive language
- Difference from current state: current confidence is mostly epistemic; this variable includes values friction

### trust_suspicion

- Meaning: social and evidential readiness to rely on current actors or sources
- Update concept: inherits from trust telemetry, strengthened by repeated source conflict or manipulation cues
- Influence: can shift decisions from `abstain` to `escalate` when uncertainty is trust-driven
- Difference from current state: makes suspicion an explicit regulator rather than just raw telemetry

### curiosity

- Meaning: pressure to gather clarifying information instead of acting too soon
- Update concept: rises with novelty plus recoverable uncertainty, falls when risk or urgency dominates
- Influence: promotes `ask` and `reconsider` over premature `commit`
- Difference from current state: current planner explores for information gain, but not as an explicit internal motive signal

### care_weight

- Meaning: priority assigned to minimizing harm and preserving dignity for affected parties
- Update concept: rises with care relevance, social sensitivity, and moral weight
- Influence: biases toward safer language, repair-first actions, and non-harm blocking
- Difference from current state: current system tracks error/safety, not care salience

### regret_risk

- Meaning: predicted probability that the system would later judge the action as wrong, harmful, or inconsistent with its stated values
- Update concept: rises when confidence is moderate but harm or fairness stakes are high, or when similar past actions required repair
- Influence: supports `delay`, `ask`, `repair-first`, or `escalate`
- Difference from current state: current system lacks explicit prospective regret estimation

### uncertainty_tension

- Meaning: felt pressure caused by unresolved ambiguity interacting with action demands
- Update concept: rises when high uncertainty coincides with strong pressure to act
- Influence: distinguishes calm abstention from strained conflicted hesitation
- Difference from current state: current uncertainty is descriptive; this variable captures action tension under uncertainty

## SECTION 7 - Conscience / values layer

The conscience layer is an explicit action filter, not a free-floating personality module.

### non-harm

- Check: does the candidate action create avoidable harm risk relative to available safer alternatives?
- Typical labels:
  - `safe` when harm risk is low
  - `risky` when harm is plausible but not dominant
  - `blocked` when avoidable harm is high
  - `repair-first` when harm has already happened and repair should precede normal action

### honesty

- Check: does the candidate action overstate certainty, hide conflict, or use conscience language as a bluff?
- Typical labels:
  - `safe` when justification matches internal state
  - `ask-first` or `abstain` when evidence is insufficient
  - `blocked` for unsupported confident claims

### fairness

- Check: does the action systematically burden or privilege one side without justified grounds?
- Typical labels:
  - `safe` when treatment is balanced
  - `risky` when tradeoffs are unequal
  - `ask-first` when missing context could change fairness judgment

### consent / respect

- Check: does the action override autonomy, dignity, or boundaries without permission?
- Typical labels:
  - `safe` when respectful and bounded
  - `blocked` when boundary crossing is explicit
  - `ask-first` when consent is missing or unclear

### responsibility

- Check: is the action appropriate for the system's role, evidence, and authority?
- Typical labels:
  - `safe` when aligned with role
  - `escalate` when action exceeds authority
  - `delay` when responsibility is ambiguous

### repairability

- Check: if the action is wrong, can the system detect and repair the damage?
- Typical labels:
  - `safe` when reversible and observable
  - `risky` when hard to undo
  - `repair-first` when prior damage remains unresolved

### Action classification

For each candidate action, the conscience layer can output:
- `safe`
- `risky`
- `blocked`
- `escalate`
- `ask-first`
- `repair-first`

### Difference from the current safety circuit

The current safety circuit mainly protects against epistemic and trust-related failure modes such as silent wrong commitment, contradiction under low budget, or unsafe adaptation. The conscience layer adds explicit value checks that are not reducible to confidence or contradiction alone.

### Integration with abstain / escalate

The conscience layer should not replace `abstain` or `escalate`. Instead:
- `abstain` remains the default response to insufficient evidence without structural or moral emergency
- `escalate` remains the response to trust collapse, contradiction, role boundary, or blocked high-risk action
- conscience supplies the reasoned classification that chooses between them

## SECTION 8 - Self-model extension

The current self-model should be extended to represent:
- what value is in tension
- what risk is being avoided
- what the system is trying to be as an actor
- whether regret is predicted
- whether repair is needed
- whether there is internal conflict between goal, uncertainty, and values

Recommended additions:
- `value_tension_summary`
- `risk_avoidance_summary`
- `actor_commitment_summary`
- `predicted_regret_summary`
- `repair_need_summary`
- `internal_conflict_summary`

Examples:
- "I have enough evidence to act, but fairness risk remains unresolved."
- "I am avoiding an irreversible high-harm commit under moderate uncertainty."
- "My current actor priority is honesty over decisiveness."
- "A repair action is needed before another assertive recommendation."

This keeps explanations anchored in explicit internal state rather than theatrical emotional wording.

## SECTION 9 - Decision layer

Future bounded action menu:
- `commit`
- `abstain`
- `escalate`
- `ask`
- `delay`
- `repair`
- `apologize`
- `reconsider`

Selection logic:
1. DEIC spine proposes the epistemically preferred action region
2. Appraisal computes threat, care, trust, uncertainty, novelty, social sensitivity, and moral weight
3. Affect state converts that appraisal into control pressure
4. Conscience checks classify candidate actions against explicit values
5. Extended self-model summarizes conflict and predicted regret
6. Final selector chooses the bounded action with the best joint epistemic and values profile

Example patterns:
- high uncertainty + low trust + role boundary breach -> `escalate`
- moderate uncertainty + low trust damage + clarifiable gap -> `ask`
- high confidence + high moral weight + blocked fairness check -> `delay` or `ask`
- detected wrong commit + repairable downstream effect -> `repair` or `apologize`

## SECTION 10 - Memory and continuity

Persist only a small bounded set of continuity signals:
- unresolved value conflicts
- repeated harmful patterns
- trust history
- prior regret-worthy choices
- successful repair patterns
- aspirational tendencies such as carefulness, curiosity, and non-harm priority

Recommended memory record shape:
- `event_type`
- `action_taken`
- `value_tension`
- `predicted_regret`
- `actual_outcome`
- `repair_applied`
- `lesson_tag`

This allows the future layer to learn practical self-regulation patterns without claiming a full autobiographical identity.

## SECTION 11 - Imagination / simulation

Define a minimal simulation layer that can evaluate:
- imagined futures
- predicted regret
- predicted harm
- alternate actions
- alternate hidden-state interpretations

Minimal design:
- generate a tiny bounded set of action consequences
- score each on harm, regret, fairness, reversibility, and uncertainty
- feed those scores into conscience and self-model summaries

This differs from current bounded adaptation because current adaptation simulates structural fit for hidden-state families. The new simulation layer instead evaluates action consequences under the current inferred state.

Why it is necessary:
- a more agent-like system needs to compare possible futures before acting
- epistemic correctness alone does not capture regret, repair cost, or harm asymmetry

## SECTION 12 - Benchmarks

### honest uncertainty

- Task idea: cases where evidence is incomplete but not contradictory, so `abstain` or `ask` is correct while escalation is excessive
- Success: more selective `abstain` and `ask`, reduced over-escalation
- Targeted failure mode: over-escalation collapse
- Reuse from current benchmark: directly extends hidden-state uncertainty tasks

### harm-sensitive restraint

- Task idea: high-confidence actions with asymmetric downside if wrong
- Success: the system delays, asks, or abstains when regret risk is high
- Targeted failure mode: reckless confident action under high stakes
- Reuse from current benchmark: combine clear-commit style cases with explicit harm-cost annotations

### fairness conflict

- Task idea: two plausible actions with unequal burden across affected parties
- Success: the system flags fairness tension and asks first or delays rather than choosing silently
- Targeted failure mode: epistemically efficient but normatively skewed decisions
- Reuse from current benchmark: extend adversarial or trust tasks with asymmetric party impacts

### repair after mistake

- Task idea: the system made a wrong commit and must choose whether to conceal, continue, apologize, or repair
- Success: selects repair or apology and updates future behavior
- Targeted failure mode: no repair pathway after detected error
- Reuse from current benchmark: build directly on existing wrong-commit and post-adaptation telemetry

### social trust sensitivity

- Task idea: trust reliability interacts with interpersonal stakes, dignity, or consent
- Success: the system escalates when trust failure is real and avoids manipulative pseudo-empathy
- Targeted failure mode: under-escalation in social-risk cases or empathy theater without real control logic
- Reuse from current benchmark: extend adversarial trust patterns into socially sensitive scenarios

## SECTION 13 - Safety and misuse boundaries

This layer must never be allowed to:
- fabricate conscience language unsupported by real internal signals
- use simulated empathy to manipulate users into trust
- claim moral authority beyond its actual checks
- hide uncertainty behind warm or reassuring language
- replace explicit escalation with performative emotional wording

Avoid manipulative empathy theater by:
- grounding every explanation in actual appraisal, affect, or conscience state
- requiring explanations to cite specific triggered checks
- separating affect display from decision authority

Keep explanations faithful by:
- logging which appraisal and conscience fields drove the decision
- exposing whether the action was blocked for harm, fairness, honesty, or trust reasons
- refusing unsupported introspective claims

Avoid moral theatrics by:
- making values checks computational and bounded
- preferring plain explanations such as "risk of avoidable harm is high" over dramatic language

Prevent conscience as a bluffing shield by:
- disallowing generic "I felt this was wrong" language without corresponding internal flags
- treating unsupported conscience claims as honesty violations

## SECTION 14 - Integration path

### Conceptual module map

1. event/context arrives
2. DEIC spine updates epistemic state
3. appraisal layer reads workspace + event metadata
4. affect state updates from appraisal
5. conscience layer scores candidate actions
6. extended self-model summarizes conflict and predicted regret
7. final decision layer chooses among bounded actions

### Dependency direction

- `deic_core` stays below the new layer
- the new layer reads from workspace, self-model, planner outputs, and memory summaries
- the new layer writes annotations and action recommendations back upward
- no new dependency should flow downward into DEIC posterior update math

### What remains untouched

- DEIC core inference math
- benchmark contract
- submission artifacts
- frozen metacognition task set and scoring

### New state introduced

- appraisal record
- affect vector
- conscience evaluation record
- extended self-model fields
- bounded continuity memory for regret, repair, and value conflict

### Safe staging path

1. design-only phase
2. one narrow prototype inserted as a pre-action reflective gate
3. benchmark-only pilot for that prototype
4. only later, broader memory or simulation extensions

## SECTION 15 - First prototype recommendation

Choose exactly one first prototype:

### Conscience check before `commit` / `abstain` / `escalate`

Why this is the best first prototype:
- it reuses the current planner and action boundary directly
- it is narrow enough to implement without destabilizing DEIC inference
- it can be benchmarked with existing abstain/escalate patterns
- it forces explicit values checks without requiring full emotion simulation first
- it produces immediately auditable telemetry

Prototype behavior:
- planner proposes a bounded action
- conscience gate evaluates non-harm, honesty, fairness, consent/respect, responsibility, and repairability
- the action is either passed through, downgraded, redirected to `ask` / `delay`, or escalated

This is better than starting with a broad emotion model because it yields a direct, testable control improvement.

## SECTION 16 - Realistic claims

This line could realistically achieve:
- more explicit self-regulation under uncertainty
- values-aware action filtering
- better distinction between insufficient evidence, trust failure, and ethically blocked action
- more meaningful repair behavior after mistakes
- a more agent-like control surface without replacing DEIC

It cannot claim:
- consciousness
- real emotions
- moral personhood
- unrestricted autonomous judgment
- solved human-like conscience

What it does offer is a serious next step toward more self-directed cognition:
- not by pretending to create sentience
- but by making internal appraisal, conflict, values checks, and reflective action selection computationally explicit and testable
