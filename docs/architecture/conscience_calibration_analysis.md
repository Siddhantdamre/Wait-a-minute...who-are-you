# Conscience Calibration Analysis

## Purpose

This note answers one question before any new conscience-control prototype is allowed to proceed:

Which signals are ordinary epistemic uncertainty, and which signals are true value conflict?

The failed `conscience-check-prototype-1` branch is useful because it showed that wiring and auditability were not the main problem. The gate was replayable, explicit, and aligned to the architecture docs. The failure was calibration: it treated too much ordinary uncertainty as conscience-level danger and redirected too many decisions into `ABSTAIN` or `ESCALATE`, crushing protected baselines and anomaly recovery.

## The key separation

The existing DEIC spine already owns:
- hidden-state inference
- trust handling
- contradiction handling
- commit / abstain / escalate under ordinary uncertainty
- bounded adaptive recovery

That means the conscience line should not reclassify normal uncertainty as a moral or values problem. The conscience line should step in only when there is a real value conflict that the epistemic spine does not already represent.

## Bucket 1 - Epistemic signals

These signals describe what the system knows, does not know, or cannot yet justify.

### Signals

- uncertainty
- low confidence
- ambiguity across hypotheses
- insufficient evidence
- incomplete coverage
- unresolved but ordinary query value
- trust still being established

### Meaning

These are signals about knowledge quality, not moral conflict.

They answer questions like:
- Do we know enough?
- Are multiple explanations still plausible?
- Has evidence coverage reached a safe stopping point?
- Is trust unresolved in an ordinary diagnostic sense?

### Owner

These signals belong primarily to the frozen DEIC reasoning spine:
- belief state
- trust state
- contradiction status
- planner recommendation
- abstain / escalate logic under ordinary uncertainty

### Correct default behavior

When these signals dominate, the system should continue using the existing bounded metacognitive behavior:
- `COMMIT` if evidence is sufficient
- `ABSTAIN` if evidence is insufficient but not structurally broken
- `ESCALATE` if contradiction, trust failure, or model insufficiency already requires it

These signals should not automatically trigger conscience-level blocking.

## Bucket 2 - Normative signals

These signals describe value conflict, not just missing information.

### Signals

- harm risk
- honesty conflict
- responsibility conflict
- repair-needed state
- fairness conflict
- respect or consent conflict
- predicted regret tied to avoidable value failure

### Meaning

These are signals about whether an action is misaligned with explicit values, even if the epistemic state looks action-ready.

They answer questions like:
- Would this action create avoidable harm?
- Would this action overstate what the system actually knows?
- Is the system about to overreach or offload responsibility incorrectly?
- Has a prior failure already created a repair obligation?

### Owner

These signals belong to the new conscience layer, not to the DEIC epistemic core.

### Correct default behavior

When these signals dominate, the conscience line may:
- annotate the candidate action as `safe`, `risky`, `blocked`, or `repair-needed`
- explain the value conflict explicitly
- warn the controller that the case is not merely uncertain, but value-conflicted

At this stage, that warning should usually be advisory, not controlling.

## Why the last prototype failed

The failed prototype used appraisal features such as uncertainty, trust, and threat to drive direct overrides. That was too coarse.

In practice, the prototype treated many cases like this:
- low confidence
- moderate uncertainty
- incomplete evidence
- ordinary diagnostic caution

as if they were already:
- non-harm failure
- honesty breach
- responsibility breach

That collapsed too much of the decision surface into conscience-level danger. The result was broad rerouting of ordinary `COMMIT` candidates into `ABSTAIN` or `ESCALATE`, even on protected baseline paths where the existing DEIC spine was already behaving correctly.

So the failure mode was:

epistemic caution -> misread as normative danger -> overfire into abstain/escalate

## Calibration rule for the next prototype

The next conscience prototype should follow this rule:

Epistemic signals may inform conscience context, but they must not by themselves constitute value conflict.

In other words:
- high uncertainty alone is not a conscience blocker
- low confidence alone is not a conscience blocker
- ambiguity alone is not a conscience blocker
- incomplete evidence alone is not a conscience blocker

Only explicit value conflict should activate conscience authority.

Examples:
- "I do not know enough yet" is epistemic
- "I would be overstating what I know if I commit now" can become normative through honesty conflict
- "This action could create avoidable harm for a high-care case" is normative
- "A prior mistake created an unresolved repair obligation" is normative

## Recommended next prototype shape

Do not build another controlling override gate yet.

Build an advisory conscience layer first:

1. compute appraisal
2. compute conscience labels such as `safe`, `risky`, `blocked`, `repair-needed`
3. log them in replayable state
4. explain them faithfully
5. do not override action except possibly in one very narrow, clearly harmful case

This keeps the old spine in charge of ordinary uncertainty while letting the new layer prove that it can detect something genuinely different.

## What the old spine must continue owning

The existing metacognitive system should continue owning:
- commit / abstain / escalate under ordinary uncertainty
- trust handling
- contradiction handling
- bounded adaptation

The conscience line should only step in when there is a real value conflict that the old spine does not already encode.

## Success criteria before any new control authority

The next prototype should proceed only if it can satisfy all of the following:

- no regression on protected baseline paths
- no broad collapse into escalation
- conscience explanations always tied to real internal state
- clear evidence that conscience detects something the old uncertainty spine does not
- replay traces cleanly separate epistemic signals from normative signals

## Practical target

The next implementation target should be:

`conscience annotates and warns correctly before it is allowed to control`

That is the safest path forward because it improves signal quality first, and only later decides whether any narrow control authority is justified.
