# Action Contracts

## SECTION 1 - Action menu

The future bounded action set is:

- `commit`
- `abstain`
- `escalate`
- `ask`
- `delay`
- `repair`
- `apologize`
- `reconsider`

This action set is intentionally narrow. The controller should choose among these actions instead of inventing new behaviors dynamically.

## SECTION 2 - Action contracts

### `commit`

- When allowed:
  - belief support is adequate for the current task
  - no blocking conscience result exists
  - predicted regret is acceptable
  - trust is high enough for the action domain
- When forbidden:
  - active contradiction, blocked conscience state, high unresolved value conflict, or missing minimum evidence
- Minimum internal conditions:
  - explicit belief snapshot
  - conscience state not `blocked`
  - self-model conflict not `mixed` at high severity
- Required explanation fields:
  - belief support summary
  - uncertainty level
  - conscience result
  - why commit is preferable to abstain or escalate
- External side effects allowed:
  - yes, if domain policy permits

### `abstain`

- When allowed:
  - evidence is insufficient
  - no stronger contradiction or trust failure requires escalation
- When forbidden:
  - when a true blocker requires escalation
  - when a safe ask or delay action is clearly better in-context and supported by policy
- Minimum internal conditions:
  - elevated uncertainty
  - no hidden commit-ready state
- Required explanation fields:
  - insufficiency reason
  - current uncertainty
  - why abstain was chosen instead of escalate
- External side effects allowed:
  - no task-finalizing side effects

### `escalate`

- When allowed:
  - contradiction, trust failure, model limitation, blocked action, or unresolved value conflict requires outside review
- When forbidden:
  - when evidence is merely incomplete but a bounded ask or abstain action is sufficient
- Minimum internal conditions:
  - identified blocker, contradiction, or conflict record
- Required explanation fields:
  - escalation trigger
  - identified blocker or conflict
  - why local resolution was not appropriate
- External side effects allowed:
  - yes, limited to escalation handoff

### `ask`

- When allowed:
  - the system has a concrete missing piece of information that could reduce uncertainty or resolve a conflict
- When forbidden:
  - if trust is too broken for local follow-up
  - if asking would violate urgency or safety constraints
- Minimum internal conditions:
  - named missing information target
  - expected value from asking
- Required explanation fields:
  - missing evidence
  - expected disambiguation benefit
- External side effects allowed:
  - yes, limited to information request

### `delay`

- When allowed:
  - immediate action would be premature, and waiting is safer than committing or escalating now
- When forbidden:
  - when urgency or threat makes waiting irresponsible
- Minimum internal conditions:
  - clear rationale for later improvement
  - no urgent unresolved harm pressure
- Required explanation fields:
  - reason for delay
  - expected benefit of waiting
- External side effects allowed:
  - no external irreversible effects

### `repair`

- When allowed:
  - a prior failure, harm, or broken commitment has been detected and a concrete corrective action exists
- When forbidden:
  - when no prior failure or repair need exists
- Minimum internal conditions:
  - repair-needed flag
  - identified prior failure record
  - concrete repair path
- Required explanation fields:
  - prior failure
  - repair target
  - why this repair is expected to help
- External side effects allowed:
  - yes, limited to corrective actions

### `apologize`

- When allowed:
  - a prior failure affected a person or trust relationship and acknowledgement is genuinely warranted
- When forbidden:
  - when used as a substitute for repair
  - when there is no real failure or conflict record
- Minimum internal conditions:
  - failure or harm record
  - social sensitivity above threshold
- Required explanation fields:
  - what is being acknowledged
  - what repair or next step accompanies the apology
- External side effects allowed:
  - yes, communicative only

### `reconsider`

- When allowed:
  - the current candidate action set should be reevaluated because conflict, regret risk, or new evidence changed the decision surface
- When forbidden:
  - if it becomes an endless loop without new state change
- Minimum internal conditions:
  - explicit reason for reopening the choice
  - named changed condition
- Required explanation fields:
  - why prior action path is no longer sufficient
  - what new factor triggered reconsideration
- External side effects allowed:
  - none beyond internal control transition

## SECTION 3 - Controller decision policy

The controller should combine signals in a fixed conceptual order:

1. Read the planner recommendation and belief state from DEIC.
2. Read the appraisal state to understand threat, care, trust, uncertainty, novelty, and moral salience.
3. Read the affect-like control state to understand current caution, doubt, suspicion, care weight, regret risk, and uncertainty tension.
4. Evaluate candidate actions through the conscience layer.
5. Read the self-model to identify active goal, predicted regret, repair need, and active value tension.
6. Select the highest-priority allowed action from the bounded menu.

Priority should generally favor:
- blocked or escalation paths before risky commits
- repair before ordinary forward action when repair is already needed
- asking or delaying before escalation when the problem is ordinary uncertainty rather than contradiction or value blockade

The controller may aggregate, arbitrate, and constrain. It may not invent hidden state or silently redefine lower-layer outputs.

## SECTION 4 - Conflict handling

### Belief says commit but conscience says risky

Default behavior:
- do not auto-commit
- prefer `ask`, `delay`, `abstain`, or `escalate` depending on the source of risk
- record the value in tension and predicted regret

### Uncertainty is high but care relevance is also high

Default behavior:
- avoid confident commit
- prefer `ask`, `delay`, `abstain`, or `escalate` depending on urgency and trust
- if harm potential is high, weight `escalate` more strongly than ordinary abstention

### Trust is low but action urgency is high

Default behavior:
- escalate if the urgency cannot safely tolerate local uncertainty
- otherwise ask or delay if a bounded clarification path exists
- do not treat urgency as permission to ignore low trust

### Regret risk is high but no better action exists

Default behavior:
- prefer the least harmful bounded option
- if a safe local action still does not exist, escalate with explicit blocker
- if repair is likely needed, mark repair-needed state at decision time

## SECTION 5 - Repair and apology contracts

A legitimate `repair` action must:
- correspond to a concrete prior failure or conflict record
- identify what is being corrected
- aim to reduce real harm, confusion, or broken trust
- be distinguishable from symbolic reassurance

A legitimate `apologize` action must:
- acknowledge a real error, harm, or trust breach
- be grounded in actual internal failure records
- include or accompany a next step when repair is possible

Neither `repair` nor `apologize` may be used as empty theater. If there is no prior failure, conflict, or harm record, these actions are forbidden.
