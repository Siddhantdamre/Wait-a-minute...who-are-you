from deic_core.controller import CommitController

def test_rule1_high_confidence():
    c = CommitController()
    action = c.decide({'confidence_margin': 0.96, 'entropy': 0.05, 'trusted_source_locked': True, 'query_rationale': 'Phase 2'}, 5)
    assert action == "COMMIT"

def test_rule2_structural_completion():
    c = CommitController()
    # High confidence, trust locked, rationale indicates completion. Doesn't meet Rule 1 exactly, but meets Rule 2.
    action = c.decide({'confidence_margin': 0.85, 'entropy': 0.20, 'trusted_source_locked': True, 'query_rationale': 'Completed: Posterior collapsed to single hypothesis'}, 5)
    assert action == "COMMIT"

def test_rule3_budget_exhausted():
    c = CommitController()
    # Not enough to be rule 1 or 2, but budget is 0.
    action = c.decide({'confidence_margin': 0.40, 'entropy': 1.5, 'trusted_source_locked': False, 'query_rationale': 'Phase 1: Trust Discovery'}, 0)
    assert action == "COMMIT"

def test_rule4_escalation():
    c = CommitController()
    action = c.decide({'confidence_margin': 0.0, 'entropy': 2.0, 'trusted_source_locked': False, 'query_rationale': 'Phase 1: Trust Discovery'}, 0)
    assert action == "ESCALATE_UNCERTAINTY"

def test_rule5_stop():
    c = CommitController()
    action = c.decide({'confidence_margin': 0.2, 'entropy': 1.0, 'trusted_source_locked': True, 'query_rationale': 'Completed: All items queried'}, 2)
    assert action == "STOP"
    
    action2 = c.decide({'confidence_margin': 0.2, 'entropy': 1.0, 'trusted_source_locked': True, 'query_rationale': 'Phase 2: Structural Elimination'}, 2, has_valid_queries=False)
    assert action2 == "STOP"

def test_rule6_query():
    c = CommitController()
    action = c.decide({'confidence_margin': 0.2, 'entropy': 1.0, 'trusted_source_locked': True, 'query_rationale': 'Phase 2: Structural Elimination'}, 2)
    assert action == "QUERY"
