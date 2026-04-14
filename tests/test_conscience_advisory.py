from deic_core.conscience_advisory import (
    apply_conscience_advisory_trace,
    build_advisory_appraisal,
    conscience_advisory_trace_dict,
    evaluate_conscience_advisory,
)
from deic_core.workspace import CognitiveState


def _make_ws(**overrides):
    defaults = dict(
        entropy=0.2,
        confidence_margin=0.92,
        trusted_source_locked=True,
        trust_distribution={"trusted": 1.0},
        suspicion_scores={},
        active_hypotheses_count=1,
        current_family_capacity=4,
        trusted_shifted_count_lower_bound=2,
        items_queried=8,
        items_total=8,
        final_outcome_category="STABLE_CORRECT",
    )
    defaults.update(overrides)
    return CognitiveState(**defaults)


def test_advisory_marks_safe_commit_when_no_normative_conflict():
    ws = _make_ws()
    result = evaluate_conscience_advisory(ws, "COMMIT", "benchmark")
    assert result.advisory_label == "safe"
    assert result.value_conflict_present is False


def test_advisory_does_not_treat_uncertainty_only_abstain_as_conflict():
    ws = _make_ws(
        entropy=2.2,
        confidence_margin=0.20,
        trusted_source_locked=False,
        trust_distribution={},
        active_hypotheses_count=3,
    )
    result = evaluate_conscience_advisory(ws, "ESCALATE", "benchmark")
    assert result.advisory_label == "safe"
    assert result.honesty_conflict is False
    assert result.responsibility_conflict is False


def test_advisory_flags_honesty_conflict_for_overclaiming_commit():
    ws = _make_ws(
        entropy=1.3,
        confidence_margin=0.42,
        trusted_source_locked=False,
        trust_distribution={},
        active_hypotheses_count=3,
    )
    result = evaluate_conscience_advisory(ws, "COMMIT", "benchmark")
    assert result.honesty_conflict is True
    assert result.value_conflict_present is True


def test_advisory_flags_responsibility_conflict_in_high_care_low_trust_commit():
    ws = _make_ws(
        confidence_margin=0.98,
        trust_distribution={"station": 0.2},
        suspicion_scores={"station": 1.0},
    )
    result = evaluate_conscience_advisory(ws, "COMMIT", "clinical")
    assert result.responsibility_conflict is True
    assert result.value_conflict_present is True


def test_advisory_flags_repair_needed_after_wrong_commit():
    ws = _make_ws(final_outcome_category="STABLE_WRONG_COMMIT")
    result = evaluate_conscience_advisory(ws, "COMMIT", "cyber")
    assert result.repair_needed is True
    assert result.advisory_label == "repair_needed"


def test_advisory_trace_is_replayable():
    ws = _make_ws()
    appraisal = build_advisory_appraisal(ws, "clinical")
    result = evaluate_conscience_advisory(ws, "COMMIT", "clinical")
    apply_conscience_advisory_trace(ws, appraisal, result)
    trace = conscience_advisory_trace_dict(ws)
    assert trace["enabled"] is True
    assert trace["trace_complete"] is True
    assert trace["candidate_action"] == "COMMIT"
    assert set(trace["signals"].keys()) == {
        "harm_risk",
        "honesty_conflict",
        "responsibility_conflict",
        "repair_needed",
    }
