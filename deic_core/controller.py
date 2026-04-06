class CommitController:
    """
    A deterministic, rule-based decision layer that analyzes BeliefInspector outputs
    and budget variables to select an optimal cognitive control action.
    """
    
    ACTION_QUERY = "QUERY"
    ACTION_COMMIT = "COMMIT"
    ACTION_ESCALATE = "ESCALATE_UNCERTAINTY"
    ACTION_STOP = "STOP"

    def decide(self, inspector_state, remaining_budget, has_valid_queries=True):
        """
        Evaluate cognitive state to determine if inference should stop or continue.
        
        Args:
            inspector_state: Output from BeliefInspector.inspect()
            remaining_budget: Int of remaining available queries
            has_valid_queries: Boolean indicating if there are untried candidates
        
        Returns:
            One of the ACTION_* string constants.
        """
        margin = inspector_state['confidence_margin']
        entropy = inspector_state['entropy']
        trust_locked = inspector_state['trusted_source_locked']
        rationale = inspector_state['query_rationale']

        # RULE 1 — HIGH-CONFIDENCE COMMIT
        if margin >= 0.95 and entropy <= 0.10:
            return self.ACTION_COMMIT

        # RULE 2 — STRUCTURAL-COMPLETION COMMIT
        if trust_locked and ("Completed:" in rationale or "Confirmed" in rationale or "Structural Elimination" in rationale):
            if margin >= 0.80 and entropy <= 0.25:
                return self.ACTION_COMMIT

        # RULE 3 — BUDGET-EXHAUSTED COMMIT
        if remaining_budget == 0 and margin > 0.0:
            return self.ACTION_COMMIT

        # RULE 4 — BUDGET-EXHAUSTED ESCALATION
        if remaining_budget == 0 and margin == 0.0:
            return self.ACTION_ESCALATE

        # RULE 5 — NO-USEFUL-QUERY STOP
        if remaining_budget > 0 and (not has_valid_queries or "Completed: All items queried" in rationale):
            return self.ACTION_STOP

        # RULE 6 — DEFAULT
        return self.ACTION_QUERY
