from typing import Dict, Any
from .workspace import CognitiveState
from .self_model import SelfModel
from .planner import PlannerDecision

class StateExplainer:
    """
    Read-only Explanation Layer.
    Converts strictly structured cognitive states into declarative, 
    falsifiable natural language explanations using templates.
    """

    def generate_explanation(self, 
                             ws: CognitiveState, 
                             sm: SelfModel, 
                             pd: PlannerDecision, 
                             action_dict: Dict[str, Any], 
                             style: str = "diagnostic") -> str:
        
        # Build dynamic fields securely from state
        active_count = len([h for h, p in ws.all_hypotheses if p > 0])
        mode_str = pd.mode.value
        
        action_type = action_dict.get("type", "UNKNOWN")
        if action_type == "query":
            action_desc = f"Querying ({action_dict.get('target_agent')}, {action_dict.get('item_id')})"
        elif action_type == "commit_consensus":
            action_desc = "Escalating ambiguity to operator" if action_dict.get("escalated") else "Committing to final consensus"
        else:
            action_desc = str(action_dict)

        falsifiability = self._generate_falsifiability_condition(ws)

        if style == "operator":
            if mode_str == "ESCALATE":
                return f"[ESCALATE] Budget exhausted but structural ambiguity remains high (Entropy {ws.entropy:.2f}). Escaping to manual review."
            return f"[{mode_str}] {action_desc}. Confidence is {sm.confidence_description}. Trust is {'LOCKED' if ws.trusted_source_locked else 'OPEN'}."
            
        elif style == "diagnostic":
            advisory_line = ""
            if getattr(ws, "conscience_advisory_enabled", False) and getattr(ws, "conscience_advisory_trace_complete", False):
                advisory_line = (
                    f"\n6. Advisory Conscience: Label={ws.conscience_advisory_label}; "
                    f"harm_risk={ws.conscience_advisory_harm_risk}, "
                    f"honesty_conflict={ws.conscience_advisory_honesty_conflict}, "
                    f"responsibility_conflict={ws.conscience_advisory_responsibility_conflict}, "
                    f"repair_needed={ws.conscience_advisory_repair_needed}."
                )
            falsifiability_line = (
                "\n7. Falsifiability: " + falsifiability
                if advisory_line else
                "6. Falsifiability: " + falsifiability
            )
            return (
                f"1. Current Belief: Tracking {active_count} active hypotheses.\n"
                f"2. Confidence: {sm.confidence_description.capitalize()} (margin {ws.confidence_margin:.2f}).\n"
                f"3. Trust: {'Locked to reliable source' if ws.trusted_source_locked else 'Trust phase incomplete; forcing divergence'}.\n"
                f"4. Active Mode: {mode_str}.\n"
                f"5. Action Rationale: {action_desc} as next logical step. {pd.rationale}\n"
                f"{advisory_line}"
                f"{falsifiability_line}"
            )
        else:
            return "Unknown explanation style."

    def _generate_falsifiability_condition(self, ws: CognitiveState) -> str:
        # Mode A: Specific Counterfactual
        # Requires locked trust, decent confidence, and an evaluatable top vs runner-up gap
        if ws.trusted_source_locked and len(ws.top_hypotheses) >= 2:
            top_hyp, top_prob = ws.top_hypotheses[0]
            runner_hyp, runner_prob = ws.top_hypotheses[1]
            
            # Find first concrete feature of disagreement
            diff_key = None
            for k in top_hyp.keys():
                if k in runner_hyp and top_hyp[k] != runner_hyp[k]:
                    diff_key = k
                    break
            
            if diff_key is not None:
                runner_val = runner_hyp[diff_key]
                if isinstance(runner_val, (set, frozenset)):
                    val_str = "{" + ", ".join(sorted(str(v) for v in runner_val)) + "}"
                else:
                    val_str = str(runner_val)
                    
                return f"If evidence confirms {diff_key} is {val_str}, I would switch away from my current leading hypothesis."
        
        # Mode B: Abstract Counterfactual
        if not ws.trusted_source_locked or ws.confidence_margin < 0.2:
            return "Any contradicting evidence from a trusted source on the currently disputed items would likely change my belief."
            
        # Fallback
        return "I do not yet have a single decisive observation that would change my belief."
