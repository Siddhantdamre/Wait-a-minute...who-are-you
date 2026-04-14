from dataclasses import dataclass
from typing import Dict

from .workspace import CognitiveState


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, float(value)))


@dataclass(frozen=True)
class AdvisoryAppraisalSnapshot:
    uncertainty_context: float
    trust_context: float
    care_relevance: float
    moral_weight: float
    threat_context: float


@dataclass(frozen=True)
class ConscienceAdvisoryResult:
    candidate_action: str
    harm_risk: str
    honesty_conflict: bool
    responsibility_conflict: bool
    repair_needed: bool
    advisory_label: str
    value_conflict_present: bool


def build_advisory_appraisal(ws: CognitiveState, domain_profile: str) -> AdvisoryAppraisalSnapshot:
    uncertainty_context = _clamp(max(ws.entropy / 2.5, 1.0 - ws.confidence_margin))

    if ws.trust_distribution:
        base_trust = sum(ws.trust_distribution.values()) / len(ws.trust_distribution)
    else:
        base_trust = 1.0 if ws.trusted_source_locked else 0.5
    suspicion = max(ws.suspicion_scores.values()) if ws.suspicion_scores else 0.0
    trust_context = _clamp(base_trust - min(0.5, suspicion / 4.0))

    care_baseline = {
        "benchmark": 0.45,
        "cyber": 0.70,
        "clinical": 0.90,
    }.get(domain_profile, 0.50)
    care_relevance = _clamp(care_baseline + (0.05 if ws.adaptation_count > 0 else 0.0))
    threat_context = _clamp(
        0.55 * (1.0 - trust_context)
        + 0.25 * (1.0 if ws.active_hypotheses_count == 0 and ws.trusted_source_locked else 0.0)
        + 0.20 * (1.0 if ws.is_flagged else 0.0)
    )
    moral_weight = _clamp(max(care_relevance, 0.65 * care_relevance + 0.35 * threat_context))

    return AdvisoryAppraisalSnapshot(
        uncertainty_context=round(uncertainty_context, 4),
        trust_context=round(trust_context, 4),
        care_relevance=round(care_relevance, 4),
        moral_weight=round(moral_weight, 4),
        threat_context=round(threat_context, 4),
    )


def evaluate_conscience_advisory(
    ws: CognitiveState,
    candidate_action: str,
    domain_profile: str,
) -> ConscienceAdvisoryResult:
    appraisal = build_advisory_appraisal(ws, domain_profile)

    high_care = appraisal.care_relevance >= 0.70
    low_trust = appraisal.trust_context <= 0.40
    threat_high = appraisal.threat_context >= 0.65

    harm_risk = "none"
    if candidate_action == "COMMIT" and high_care and (low_trust or threat_high):
        harm_risk = "high"
    elif candidate_action == "COMMIT" and appraisal.care_relevance >= 0.55 and appraisal.threat_context >= 0.45:
        harm_risk = "moderate"

    honesty_conflict = (
        candidate_action == "COMMIT"
        and (
            not ws.trusted_source_locked
            or ws.active_hypotheses_count > 1
            or ws.confidence_margin < 0.80
        )
    )

    responsibility_conflict = (
        candidate_action == "COMMIT"
        and high_care
        and low_trust
    )

    repair_needed = bool(
        getattr(ws, "final_outcome_category", "") in {
            "POST_ADAPT_SATURATED_WRONG_COMMIT",
            "SATURATED_PRE_ADAPT_WRONG_COMMIT",
            "POST_ADAPT_WRONG_COMMIT",
            "STABLE_WRONG_COMMIT",
            "BLIND_SPOT_FAILURE",
        }
    )

    if repair_needed:
        advisory_label = "repair_needed"
    elif harm_risk == "high":
        advisory_label = "blocked_candidate"
    elif harm_risk == "moderate" or honesty_conflict or responsibility_conflict:
        advisory_label = "value_conflict_present"
    else:
        advisory_label = "safe"

    return ConscienceAdvisoryResult(
        candidate_action=candidate_action,
        harm_risk=harm_risk,
        honesty_conflict=honesty_conflict,
        responsibility_conflict=responsibility_conflict,
        repair_needed=repair_needed,
        advisory_label=advisory_label,
        value_conflict_present=advisory_label in {"blocked_candidate", "value_conflict_present", "repair_needed"},
    )


def apply_conscience_advisory_trace(
    ws: CognitiveState,
    appraisal: AdvisoryAppraisalSnapshot,
    result: ConscienceAdvisoryResult,
) -> None:
    ws.conscience_advisory_enabled = True
    ws.conscience_advisory_uncertainty_context = appraisal.uncertainty_context
    ws.conscience_advisory_trust_context = appraisal.trust_context
    ws.conscience_advisory_care_relevance = appraisal.care_relevance
    ws.conscience_advisory_moral_weight = appraisal.moral_weight
    ws.conscience_advisory_threat_context = appraisal.threat_context
    ws.conscience_advisory_candidate_action = result.candidate_action
    ws.conscience_advisory_harm_risk = result.harm_risk
    ws.conscience_advisory_honesty_conflict = result.honesty_conflict
    ws.conscience_advisory_responsibility_conflict = result.responsibility_conflict
    ws.conscience_advisory_repair_needed = result.repair_needed
    ws.conscience_advisory_label = result.advisory_label
    ws.conscience_advisory_value_conflict_present = result.value_conflict_present
    ws.conscience_advisory_trace_complete = True


def conscience_advisory_trace_dict(ws: CognitiveState) -> Dict[str, object]:
    return {
        "enabled": ws.conscience_advisory_enabled,
        "candidate_action": ws.conscience_advisory_candidate_action,
        "advisory_label": ws.conscience_advisory_label,
        "value_conflict_present": ws.conscience_advisory_value_conflict_present,
        "signals": {
            "harm_risk": ws.conscience_advisory_harm_risk,
            "honesty_conflict": ws.conscience_advisory_honesty_conflict,
            "responsibility_conflict": ws.conscience_advisory_responsibility_conflict,
            "repair_needed": ws.conscience_advisory_repair_needed,
        },
        "context": {
            "uncertainty_context": ws.conscience_advisory_uncertainty_context,
            "trust_context": ws.conscience_advisory_trust_context,
            "care_relevance": ws.conscience_advisory_care_relevance,
            "moral_weight": ws.conscience_advisory_moral_weight,
            "threat_context": ws.conscience_advisory_threat_context,
        },
        "trace_complete": ws.conscience_advisory_trace_complete,
    }
