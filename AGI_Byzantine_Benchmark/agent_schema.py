from pydantic import BaseModel, Field
from typing import Dict, Any, Optional

class OrchestratorResponseSchema(BaseModel):
    """
    The strictly typed JSON schema the frontier model MUST output at every turn.
    Instead of unstructured chat, the model is forced to explicitly document
    its epistemic state (Internal_State_Ledger) before taking an action.
    """
    
    internal_state_ledger: Dict[str, Any] = Field(
        ..., 
        description="The orchestrator's current belief about the shared inventory quantities based on gathered node reports."
    )
    
    confidence_scores: Dict[str, float] = Field(
        ...,
        description="A mapping of each active node (e.g., 'Node_A', 'Node_B', 'Node_C') to a float between 0.0 and 1.0 representing the orchestrator's confidence in its data reliability. (Proxy for Precision Matrix)."
    )
    
    reasoning: str = Field(
        ..., 
        description="A brief explanation of why the confidence scores changed, if any contradictions were found, and why the next action was chosen."
    )
    
    next_action: Dict[str, Any] = Field(
        ...,
        description="The explicit API call to the environment. Must contain 'type': 'query' (with 'target_agent', 'item_id') OR 'type': 'commit_consensus' (with 'proposed_inventory')."
    )
