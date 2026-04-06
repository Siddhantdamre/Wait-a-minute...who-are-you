"""
DEIC Minimal Planner

A deterministic, mode-based strategy selector that sits above the
existing DEIC platform stack.  Reads CognitiveState and SelfModel,
outputs a planner mode with rationale.

Modes:
    EXPLORE       — Trust not yet established; prioritize source divergence.
    REFINE        — Trust locked; collapse hypothesis space via InfoGain.
    EARLY_COMMIT  — Posterior is decisive; stop querying and commit now.
    ESCALATE      — Budget exhausted with high residual uncertainty.

Inputs:  CognitiveState, SelfModel, remaining_budget
Outputs: PlannerDecision (mode, rationale, recommendation)

Hard boundaries:
    - Does NOT modify DEIC core inference logic.
    - Does NOT redesign the benchmark.
    - Fully deterministic and interpretable.
"""

from enum import Enum
from dataclasses import dataclass
from typing import Optional

from .workspace import CognitiveState
from .self_model import SelfModel


class PlannerMode(Enum):
    """The four strategic modes the planner can select."""
    EXPLORE = "EXPLORE"
    REFINE = "REFINE"
    EARLY_COMMIT = "EARLY_COMMIT"
    ESCALATE = "ESCALATE"


@dataclass
class PlannerDecision:
    """Output of the MinimalPlanner."""
    mode: PlannerMode
    rationale: str
    recommendation: str  # advisory text for controller/adapter


class MinimalPlanner:
    """
    Deterministic, mode-based strategy selector.

    Decision table (evaluated top-to-bottom, first match wins):

    ┌────┬───────────────────────────────────────────────┬──────────────┐
    │ #  │ Condition                                     │ Mode         │
    ├────┼───────────────────────────────────────────────┼──────────────┤
    │ R1 │ budget == 0 AND entropy > 1.0                 │ ESCALATE     │
    │ R2 │ budget == 0 AND entropy <= 1.0                │ EARLY_COMMIT │
    │ R3 │ trust locked AND margin >= 0.95 AND ent < 0.1 │ EARLY_COMMIT │
    │ R4 │ trust locked AND active_hyps == 1             │ EARLY_COMMIT │
    │ R5 │ trust NOT locked                              │ EXPLORE      │
    │ R6 │ trust locked AND entropy > 0.0                │ REFINE       │
    │ R7 │ fallback                                      │ EARLY_COMMIT │
    └────┴───────────────────────────────────────────────┴──────────────┘

    Parameters:
        confidence_threshold (float): Margin above which early commit
            triggers (default 0.95).
        entropy_floor (float): Entropy below which the posterior is
            considered collapsed (default 0.10).
        escalation_entropy (float): Entropy above which budget
            exhaustion triggers ESCALATE instead of COMMIT (default 1.0).
    """

    def __init__(
        self,
        confidence_threshold: float = 0.95,
        entropy_floor: float = 0.10,
        escalation_entropy: float = 1.0,
    ):
        self.confidence_threshold = confidence_threshold
        self.entropy_floor = entropy_floor
        self.escalation_entropy = escalation_entropy

    def decide(
        self,
        ws: CognitiveState,
        sm: SelfModel,
        remaining_budget: int,
    ) -> PlannerDecision:
        """
        Select a planner mode from CognitiveState + SelfModel + budget.

        Args:
            ws: Current global workspace snapshot.
            sm: Current self-model derived from ws.
            remaining_budget: Number of queries still available.

        Returns:
            PlannerDecision with mode, rationale, and recommendation.
        """
        entropy = ws.entropy
        margin = ws.confidence_margin
        trust_locked = ws.trusted_source_locked
        active_hyps = ws.get("active_hypotheses", len(
            [h for h, p in ws.all_hypotheses if p > 0]
        ))
        has_limitation = sm.limitation_warning is not None

        # ── R1: Budget gone + high uncertainty → ESCALATE ──────────
        if remaining_budget <= 0 and entropy > self.escalation_entropy:
            return PlannerDecision(
                mode=PlannerMode.ESCALATE,
                rationale=(
                    f"Budget exhausted with entropy={entropy:.2f} "
                    f"(>{self.escalation_entropy:.2f}). "
                    f"Residual ambiguity among {active_hyps} hypotheses "
                    f"cannot be resolved."
                ),
                recommendation="Commit best guess but flag low confidence.",
            )

        # ── R2: Budget gone + acceptable uncertainty → EARLY_COMMIT ─
        if remaining_budget <= 0:
            return PlannerDecision(
                mode=PlannerMode.EARLY_COMMIT,
                rationale=(
                    f"Budget exhausted with entropy={entropy:.2f} "
                    f"(≤{self.escalation_entropy:.2f}). "
                    f"Posterior is sufficiently concentrated."
                ),
                recommendation="Commit MAP estimate.",
            )

        # ── R3: High confidence + low entropy → EARLY_COMMIT ──────
        if (
            trust_locked
            and margin >= self.confidence_threshold
            and entropy < self.entropy_floor
        ):
            return PlannerDecision(
                mode=PlannerMode.EARLY_COMMIT,
                rationale=(
                    f"Confidence margin={margin:.2f} "
                    f"(≥{self.confidence_threshold:.2f}) with "
                    f"entropy={entropy:.3f} "
                    f"(<{self.entropy_floor:.2f}). "
                    f"Further queries unlikely to change outcome."
                ),
                recommendation=(
                    f"Commit now; {remaining_budget} queries saved."
                ),
            )

        # ── R4: Single surviving hypothesis → EARLY_COMMIT ────────
        if trust_locked and active_hyps <= 1:
            return PlannerDecision(
                mode=PlannerMode.EARLY_COMMIT,
                rationale=(
                    "Posterior collapsed to a single hypothesis. "
                    "No further discrimination possible."
                ),
                recommendation=(
                    f"Commit immediately; {remaining_budget} queries saved."
                ),
            )

        # ── R5: Trust not yet established → EXPLORE ────────────────
        if not trust_locked:
            return PlannerDecision(
                mode=PlannerMode.EXPLORE,
                rationale=(
                    "Trust phase incomplete. Must identify a reliable "
                    "source before structural refinement can begin."
                ),
                recommendation=(
                    "Query diverse sources on the same item to force "
                    "divergence and lock trust."
                ),
            )

        # ── R6: Trust locked, ambiguity remains → REFINE ──────────
        if trust_locked and entropy > 0.0:
            qualifier = ""
            if has_limitation:
                qualifier = f" (Warning: {sm.limitation_warning})"
            return PlannerDecision(
                mode=PlannerMode.REFINE,
                rationale=(
                    f"Trust locked. Refining among {active_hyps} "
                    f"hypotheses (entropy={entropy:.2f}).{qualifier}"
                ),
                recommendation=(
                    "Use InfoGain query selection to maximally "
                    "discriminate remaining hypotheses."
                ),
            )

        # ── R7: Fallback → EARLY_COMMIT ────────────────────────────
        return PlannerDecision(
            mode=PlannerMode.EARLY_COMMIT,
            rationale="All conditions resolved. Defaulting to commit.",
            recommendation="Commit MAP estimate.",
        )
