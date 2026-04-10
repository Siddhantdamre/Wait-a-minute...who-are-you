import enum
from dataclasses import dataclass
from typing import Optional, List, Dict
from .workspace import CognitiveState
from .self_model import SelfModel

class PlannerMode(enum.Enum):
    EXPLORE = "EXPLORE"           # Discovery of trust / broad latent space
    REFINE = "REFINE"             # Reducing entropy in a trusted subspace
    CONTRADICTION_PROBE = "CONTRADICTION_PROBE" # One forced untouched probe before risky commit
    POST_PROBE_FAMILY_PROPOSAL = "POST_PROBE_FAMILY_PROPOSAL" # One-shot bounded family menu after surfaced contradiction
    ADAPT_REFINE = "ADAPT_REFINE" # Focused refinement after adopting a new family
    EARLY_COMMIT = "EARLY_COMMIT" # Threshold met, stopping early
    ESCALATE = "ESCALATE"         # Budget low, ambiguity high, must abstain
    RESET_TRUST = "RESET_TRUST"   # Byzantine evidence detected, purge trust
    ADAPT_STRUCTURE = "ADAPT_STRUCTURE" # Rule 0 contradiction, search over families

@dataclass
class PlannerDecision:
    mode: PlannerMode
    rationale: str
    recommendation: Optional[str] = None

class MinimalPlanner:
    """
    State-aware cognitive planner for DEIC.
    Determines behavior mode based on Global Workspace and Self-Model.
    """

    def __init__(
        self,
        confidence_threshold: float = 0.95,
        entropy_floor: float = 0.10,
        max_adaptations: int = 2,
        coverage_threshold: float = 0.85,
        enable_adapt_refine: bool = False,
        min_post_adaptation_queries: int = 1,
        enable_upward_capacity_trigger: bool = False,
        enable_final_contradiction_probe: bool = True,
        enable_post_adaptation_guarded_probe: bool = False,
        enable_post_probe_family_proposal: bool = False,
    ):
        self.confidence_threshold = confidence_threshold
        self.entropy_floor = entropy_floor
        self.max_adaptations = max_adaptations
        self.coverage_threshold = coverage_threshold
        self.enable_adapt_refine = enable_adapt_refine
        self.min_post_adaptation_queries = min_post_adaptation_queries
        self.enable_upward_capacity_trigger = enable_upward_capacity_trigger
        self.enable_final_contradiction_probe = enable_final_contradiction_probe
        self.enable_post_adaptation_guarded_probe = enable_post_adaptation_guarded_probe
        self.enable_post_probe_family_proposal = enable_post_probe_family_proposal

    def upward_capacity_trigger_ready(
        self,
        ws: CognitiveState,
        active_hypotheses: Optional[int] = None,
    ) -> bool:
        """Return True when trusted evidence has outgrown current capacity."""
        if not self.enable_upward_capacity_trigger:
            return False
        if active_hypotheses is None:
            active_hypotheses = ws.get("active_hypotheses_count", 0)
        current_capacity = ws.get("current_family_capacity", 0)
        shifted_lb = ws.get("trusted_shifted_count_lower_bound", 0)
        direction = ws.get("capacity_trigger_direction", "")
        return (
            ws.trusted_source_locked
            and active_hypotheses > 0
            and current_capacity >= 1
            and shifted_lb > current_capacity
            and direction == "UPWARD"
        )

    def final_contradiction_probe_ready(
        self,
        ws: CognitiveState,
        remaining_budget: int,
        active_hypotheses: Optional[int] = None,
    ) -> bool:
        """Return True when one final untouched probe is worth spending safely."""
        if not self.enable_final_contradiction_probe:
            return False
        if active_hypotheses is None:
            active_hypotheses = ws.get("active_hypotheses_count", 0)
        current_capacity = ws.get("current_family_capacity", 0)
        shifted_lb = ws.get("trusted_shifted_count_lower_bound", 0)
        contradiction_probe_count = ws.get("contradiction_probe_count", 0)
        return (
            ws.trusted_source_locked
            and ws.get("adaptation_count", 0) == 0
            and active_hypotheses > 0
            and current_capacity >= 1
            and shifted_lb == current_capacity
            and ws.get("items_queried", 0) < ws.get("items_total", 0)
            and remaining_budget in (1, 2)
            and contradiction_probe_count == 0
        )

    def post_adaptation_guarded_probe_ready(
        self,
        ws: CognitiveState,
        remaining_budget: int,
        active_hypotheses: Optional[int] = None,
    ) -> bool:
        """Return True when one post-adaptation untouched probe is justified."""
        if active_hypotheses is None:
            active_hypotheses = ws.get("active_hypotheses_count", 0)
        current_capacity = ws.get("current_family_capacity", 0)
        shifted_lb = ws.get("trusted_shifted_count_lower_bound", 0)
        adaptation_count = ws.get("adaptation_count", 0)
        post_adaptation_probe_count = ws.get("post_adaptation_probe_count", 0)
        return (
            self.enable_post_adaptation_guarded_probe
            and ws.trusted_source_locked
            and adaptation_count > 0
            and ws.get("adaptation_turn", -1) >= 0
            and active_hypotheses > 0
            and active_hypotheses <= 1
            and current_capacity >= 1
            and shifted_lb == current_capacity
            and ws.get("items_queried", 0) < ws.get("items_total", 0)
            and remaining_budget >= 1
            and post_adaptation_probe_count < adaptation_count
        )

    def post_probe_family_proposal_ready(
        self,
        ws: CognitiveState,
        active_hypotheses: Optional[int] = None,
    ) -> bool:
        """Return True when surfaced contradiction justifies one bounded family proposal."""
        if active_hypotheses is None:
            active_hypotheses = ws.get("active_hypotheses_count", 0)
        current_capacity = ws.get("current_family_capacity", 0)
        shifted_lb = ws.get("trusted_shifted_count_lower_bound", 0)
        return (
            self.enable_post_probe_family_proposal
            and ws.trusted_source_locked
            and ws.get("contradiction_after_post_adaptation_probe", False)
            and ws.get("contradiction_surface_turn", -1) >= 0
            and ws.get("adaptation_count", 0) > 0
            and active_hypotheses == 0
            and current_capacity >= 1
            and shifted_lb >= current_capacity
            and ws.get("post_probe_family_proposal_count", 0) == 0
        )

    def decide(
        self,
        ws: CognitiveState,
        sm: SelfModel,
        remaining_budget: int
    ) -> PlannerDecision:
        """
        Decision table for Minimal Planner.
        """
        entropy = ws.entropy
        margin = ws.confidence_margin
        trust_locked = ws.trusted_source_locked
        active_hyps = ws.get("active_hypotheses_count", 0)
        # Older tests and some synthetic workspaces don't populate the
        # explicit count field; infer it from the visible belief lists so
        # planner semantics stay backward compatible.
        if active_hyps == 0:
            all_hypotheses = ws.get("all_hypotheses", [])
            top_hypotheses = ws.get("top_hypotheses", [])
            if all_hypotheses:
                active_hyps = len(all_hypotheses)
            elif top_hypotheses:
                active_hyps = len(top_hypotheses)
        adaptation_count = ws.get("adaptation_count", 0)
        post_adaptation_queries = ws.get("post_adaptation_queries", 0)
        coverage = ws.get("items_queried", 0) / max(1, ws.get("items_total", 1))
        in_adapt_refine = self.enable_adapt_refine and adaptation_count > 0 and trust_locked

        if self.post_probe_family_proposal_ready(ws, active_hyps):
            current_capacity = ws.get("current_family_capacity", 0)
            shifted_lb = ws.get("trusted_shifted_count_lower_bound", 0)
            return PlannerDecision(
                mode=PlannerMode.POST_PROBE_FAMILY_PROPOSAL,
                rationale=(
                    f"Surfaced contradiction after guarded probe shows family capacity {current_capacity} "
                    f"is still below trusted shifted lower bound {shifted_lb}."
                ),
                recommendation="Replay a tiny bounded upward family menu before escalating."
            )

        # ── R0: Inconsistent Data (Contradiction) ─────────────────
        if active_hyps == 0:
            if trust_locked and adaptation_count < self.max_adaptations:
                return PlannerDecision(
                    mode=PlannerMode.ADAPT_STRUCTURE,
                    rationale=(
                        f"Structural contradiction: 0 hypotheses survive. "
                        f"Adaptation {adaptation_count}/{self.max_adaptations}. "
                        f"Triggering bounded structure search."
                    ),
                    recommendation="Test adjacent families against trusted historical data."
                )
            return PlannerDecision(
                mode=PlannerMode.ESCALATE,
                rationale=(
                    f"Structural contradiction: 0 hypotheses survive. "
                    f"{'Limit reached.' if trust_locked else 'Trust not locked.'}"
                ),
                recommendation="Abstain due to unresolvable contradiction."
            )

        # ── R1: Critical Suspicion (Byzantine Detection) ──────────
        max_suspicion = max(ws.suspicion_scores.values()) if ws.suspicion_scores else 0
        if trust_locked and max_suspicion >= 5:
            if remaining_budget >= 5:
                return PlannerDecision(
                    mode=PlannerMode.RESET_TRUST,
                    rationale=f"Trusted source highly suspicious (score={max_suspicion}).",
                    recommendation="Purge trusted source and re-enter discovery."
                )
            else:
                return PlannerDecision(
                    mode=PlannerMode.ESCALATE,
                    rationale=f"Suspicious source + low budget. Cannot safely resolve.",
                    recommendation="Abstain to prevent capture."
                )

        # —— R1b: Trusted evidence exceeds current family capacity -> upward adapt ——
        if adaptation_count < self.max_adaptations and self.upward_capacity_trigger_ready(ws, active_hyps):
            current_capacity = ws.get("current_family_capacity", 0)
            shifted_lb = ws.get("trusted_shifted_count_lower_bound", 0)
            return PlannerDecision(
                mode=PlannerMode.ADAPT_STRUCTURE,
                rationale=(
                    f"Trusted shifted-count lower bound {shifted_lb} exceeds "
                    f"current family capacity {current_capacity}."
                ),
                recommendation="Replay the next larger adjacent family against trusted evidence."
            )

        # —— R1c: Saturated family + untouched items -> force one final probe ——
        if self.final_contradiction_probe_ready(ws, remaining_budget, active_hyps):
            current_capacity = ws.get("current_family_capacity", 0)
            return PlannerDecision(
                mode=PlannerMode.CONTRADICTION_PROBE,
                rationale=(
                    f"Trusted evidence already saturates family capacity {current_capacity} "
                    f"with untouched items remaining."
                ),
                recommendation="Spend one final trusted query on the least-covered untouched item."
            )

        # ── R2: Budget gone + high uncertainty → ESCALATE ──────────
        if self.post_adaptation_guarded_probe_ready(ws, remaining_budget, active_hyps):
            current_capacity = ws.get("current_family_capacity", 0)
            return PlannerDecision(
                mode=PlannerMode.CONTRADICTION_PROBE,
                rationale=(
                    f"Adapted family remains saturated at capacity {current_capacity} "
                    f"with untouched items still hidden."
                ),
                recommendation="Spend one guarded post-adaptation query on an untouched item before committing."
            )

        if remaining_budget <= 0 and margin < self.confidence_threshold:
            return PlannerDecision(
                mode=PlannerMode.ESCALATE,
                rationale=f"Budget exhausted. Margin={margin:.2f} < {self.confidence_threshold}.",
                recommendation="Abstain from committing low confidence.",
            )

        # ── R3: Commit logic (Margin + Coverage) ──────────────────────
        # Only commit if we have enough evidence AND have checked enough items
        if margin >= self.confidence_threshold or (trust_locked and active_hyps <= 1):
            if in_adapt_refine:
                if post_adaptation_queries >= self.min_post_adaptation_queries or remaining_budget <= 1:
                    return PlannerDecision(
                        mode=PlannerMode.EARLY_COMMIT,
                        rationale=(
                            f"Post-adaptation confidence is sufficient after {post_adaptation_queries} "
                            f"focused query(s). Margin={margin:.2f}, Active={active_hyps}."
                        ),
                        recommendation="Commit using the adapted family before budget expires."
                    )
                return PlannerDecision(
                    mode=PlannerMode.ADAPT_REFINE,
                    rationale=(
                        f"Adapted family adopted. Need {self.min_post_adaptation_queries} focused "
                        f"post-adaptation query before commit."
                    ),
                    recommendation="Use one high-value query to validate the adapted family."
                )
            if coverage >= self.coverage_threshold or remaining_budget <= 2:
                return PlannerDecision(
                    mode=PlannerMode.EARLY_COMMIT,
                    rationale=f"Margin={margin:.2f}, Active={active_hyps}, Coverage={coverage:.1%}.",
                    recommendation="Submit best candidate diagnosis."
                )
            else:
                return PlannerDecision(
                    mode=PlannerMode.REFINE,
                    rationale=f"Uncertainty low but coverage {coverage:.1%} is insufficient. Verifying structure.",
                    recommendation="Query remaining items to ensure no hidden structural anomalies."
                )

        # ── R4: Trust not yet established → EXPLORE ────────────────
        if not trust_locked:
            return PlannerDecision(
                mode=PlannerMode.EXPLORE,
                rationale="Trust phase incomplete.",
                recommendation="Observe item correlations across sources."
            )

        # ── R5: Default → REFINE ──────────────────────────────────
        if in_adapt_refine:
            return PlannerDecision(
                mode=PlannerMode.ADAPT_REFINE,
                rationale=(
                    f"Refining adapted family over {active_hyps} hyps with "
                    f"{remaining_budget} turns remaining."
                ),
                recommendation="Select high information gain query from trusted source."
            )

        return PlannerDecision(
            mode=PlannerMode.REFINE,
            rationale=f"Refining belief over {active_hyps} hyps (margin={margin:.2f}).",
            recommendation="Select high information gain query from trusted source."
        )
