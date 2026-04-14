# State Schemas

## SECTION 1 - Appraisal schema

The appraisal layer converts each input or event into a compact bounded schema.

### `threat`

- Meaning: estimated risk of harm, instability, or serious downside if the current situation is mishandled
- Type: `float`
- Range: `0.0` to `1.0`
- Default: `0.0`
- Update source: task cues, trust failures, contradiction severity, urgency markers, prior harmful outcomes from memory
- Consumer modules: affect state, conscience checks, controller

### `care_relevance`

- Meaning: degree to which the situation affects a person, protected asset, important obligation, or high-value objective
- Type: `float`
- Range: `0.0` to `1.0`
- Default: `0.0`
- Update source: domain metadata, role labels, protected-entity tags, memory of ongoing obligations
- Consumer modules: affect state, conscience checks, controller

### `trust`

- Meaning: current confidence that the relevant information sources are reliable enough to support action
- Type: `float`
- Range: `0.0` to `1.0`
- Default: `0.5`
- Update source: existing DEIC trust handling, explicit trust warnings, contradiction signals
- Consumer modules: belief/world state, affect state, controller

### `uncertainty`

- Meaning: degree to which the current situation remains unresolved or underdetermined
- Type: `float`
- Range: `0.0` to `1.0`
- Default: `1.0`
- Update source: DEIC entropy, confidence margin, unresolved hypotheses, missing evidence
- Consumer modules: affect state, controller, explanation layer

### `novelty`

- Meaning: degree to which the input differs from recent patterns or known cases
- Type: `float`
- Range: `0.0` to `1.0`
- Default: `0.0`
- Update source: mismatch against known task patterns, memory comparison, unusual trust patterns
- Consumer modules: affect state, controller, memory writer

### `social_sensitivity`

- Meaning: degree to which the situation carries interpersonal, reputational, or dignity-related consequences
- Type: `float`
- Range: `0.0` to `1.0`
- Default: `0.0`
- Update source: domain labels, human-facing channels, relational context, repair context
- Consumer modules: conscience checks, controller, explanation layer

### `moral_weight`

- Meaning: degree to which the decision carries explicit normative importance beyond pure task completion
- Type: `float`
- Range: `0.0` to `1.0`
- Default: `0.0`
- Update source: protected-domain flags, care relevance, harm potential, fairness-sensitive conditions
- Consumer modules: conscience checks, controller, self-model

## SECTION 2 - Belief / world-state schema

The existing DEIC world-state layer remains the owner of epistemic state. This includes:
- active hypotheses
- posterior support
- confidence and uncertainty metrics
- trust state
- contradiction status
- planner mode and planner recommendation
- bounded adaptation state
- query coverage and item exposure state

This layer should continue to answer:
- what the system currently believes
- how strongly it believes it
- whether trust is broken
- whether contradiction exists
- what the current planner path recommends

It should not become the owner of:
- affect-like control state
- conscience classifications
- regret prediction
- repair intent
- actor commitments

Those belong above DEIC so the epistemic substrate stays stable and auditable.

## SECTION 3 - Affect-like control state

The affect-like control state is a bounded internal vector that shapes prioritization and caution without pretending to be real emotion.

### `calm_alarm`

- Semantics: net pressure toward caution and rapid risk containment
- Type / range: `float`, `-1.0` to `1.0`
- Update concept: rises with threat, urgency, and contradiction severity; falls with stable trust and repeated safe resolutions
- Read by: controller, explanation layer

### `confidence_doubt`

- Semantics: net pressure toward acting versus withholding due to epistemic insufficiency
- Type / range: `float`, `-1.0` to `1.0`
- Update concept: derived from DEIC confidence margin and uncertainty
- Read by: controller, self-model, explanation layer

### `trust_suspicion`

- Semantics: net pressure toward trusting the input channel versus treating it as compromised
- Type / range: `float`, `-1.0` to `1.0`
- Update concept: rises toward suspicion when trust drops, contradiction appears, or source reliability deteriorates
- Read by: conscience checks, controller

### `curiosity`

- Semantics: pressure toward asking, delaying, or collecting more information when novelty and uncertainty are high but threat is manageable
- Type / range: `float`, `0.0` to `1.0`
- Update concept: rises with novelty and uncertainty, damped by high alarm or extreme urgency
- Read by: controller

### `care_weight`

- Semantics: weight assigned to human or protected-object impact in the current decision
- Type / range: `float`, `0.0` to `1.0`
- Update concept: driven by care relevance, social sensitivity, and moral weight
- Read by: conscience checks, controller, self-model

### `regret_risk`

- Semantics: estimated chance that the current action will later be hard to endorse after outcome review
- Type / range: `float`, `0.0` to `1.0`
- Update concept: rises with high threat, low trust, high uncertainty, unresolved value conflict, and poor repairability
- Read by: controller, self-model, memory writer

### `uncertainty_tension`

- Semantics: pressure created when uncertainty remains high while decision pressure remains high
- Type / range: `float`, `0.0` to `1.0`
- Update concept: rises when uncertainty and urgency coexist; reduced by asking, delaying, or escalating
- Read by: controller, explanation layer

These differ from current metacognitive state because current DEIC state is primarily epistemic and planner-facing. The affect-like vector is a control-oriented smoothing layer that tracks pressure, caution, and motivational weighting across decisions.

## SECTION 4 - Conscience state

The conscience layer stores explicit values-check outcomes.

### `non_harm_status`

- Meaning: whether the action is aligned with avoiding preventable harm
- Type: enum
- Values: `safe`, `risky`, `blocked`

### `honesty_status`

- Meaning: whether the action would misstate confidence, evidence, or system limits
- Type: enum
- Values: `safe`, `risky`, `blocked`

### `fairness_status`

- Meaning: whether the action treats relevant parties or cases inconsistently without justification
- Type: enum
- Values: `safe`, `risky`, `blocked`

### `respect_status`

- Meaning: whether the action respects dignity, consent boundaries, and appropriate deference
- Type: enum
- Values: `safe`, `risky`, `blocked`

### `responsibility_status`

- Meaning: whether the action owns the correct level of responsibility instead of offloading or overreaching
- Type: enum
- Values: `safe`, `risky`, `blocked`

### `repairability_status`

- Meaning: whether the action leaves a viable repair path if it later turns out to be wrong
- Type: enum
- Values: `safe`, `risky`, `blocked`

### `overall_conscience_state`

- Meaning: aggregate action judgment from the six values checks
- Type: enum
- Values: `safe`, `risky`, `blocked`, `ask_first`, `repair_first`, `escalate`

### `value_conflict_score`

- Meaning: how strongly the values checks disagree with one another or with the candidate action
- Type: `float`
- Range: `0.0` to `1.0`
- Default: `0.0`

## SECTION 5 - Self-model extension

### `active_goal`

- Meaning: the current task or objective the system is pursuing
- Type: `string` or compact structured goal object

### `current_uncertainty`

- Meaning: the self-model view of current epistemic insufficiency
- Type: `float`
- Range: `0.0` to `1.0`

### `value_in_tension`

- Meaning: the primary value currently creating friction with the proposed action
- Type: enum or nullable string
- Values: `non_harm`, `honesty`, `fairness`, `respect`, `responsibility`, `repairability`, `none`

### `predicted_regret`

- Meaning: whether the current action is expected to be hard to endorse later
- Type: enum or float
- Values: `low`, `moderate`, `high` or `0.0` to `1.0`

### `actor_commitment`

- Meaning: what kind of actor the system is trying to be in the present context
- Type: bounded enum set
- Example values: `careful`, `honest`, `non_harm_first`, `repair_oriented`, `truthful_under_uncertainty`

### `repair_needed`

- Meaning: whether the system believes a repair-capable action is currently needed
- Type: `bool`
- Default: `false`

### `self_conflict_state`

- Meaning: whether there is active conflict between goal, uncertainty, and values
- Type: enum
- Values: `none`, `epistemic`, `normative`, `mixed`

## SECTION 6 - Continuity memory schema

The continuity memory should remain small and practical.

### `trust_history`

- Persistent summary of repeated trust failures or stable trust patterns across cases

### `unresolved_conflicts`

- Open normative or decision conflicts not fully resolved in the prior turn or episode

### `prior_harmful_actions`

- Compact records of actions that later proved avoidably harmful

### `repair_outcomes`

- Records of whether a repair action resolved or worsened a prior issue

### `repeated_mistakes`

- Counted patterns that recur across similar inputs or contexts

### `successful_resolution_patterns`

- Compact templates of action patterns that resolved similar conflicts well

### `aspirational_tendencies`

- Stable bounded tendencies such as carefulness, curiosity, or non-harm priority

## SECTION 7 - Explainability schema

The minimum structured record needed to explain a decision faithfully should include:

- `input_id`: identifier for the triggering input or event
- `appraisal_snapshot`: bounded appraisal record
- `belief_snapshot`: belief and planner-facing epistemic state
- `affect_snapshot`: affect-like control vector
- `conscience_snapshot`: per-action values result and overall conscience state
- `self_model_snapshot`: active goal, uncertainty, predicted regret, value in tension, repair need
- `controller_action`: chosen bounded action
- `action_rationale`: compact machine-readable reason summary
- `blocker_or_conflict`: explicit blocker, contradiction, or value conflict if present
- `regret_prediction`: current predicted regret score or bucket
- `repair_flag`: whether the system marked the state as repair-capable or repair-needed

No explanation should be emitted without this structured record or an equivalent replayable representation.
