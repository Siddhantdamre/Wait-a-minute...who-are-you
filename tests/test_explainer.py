import pytest
from deic_core.workspace import CognitiveState
from deic_core.self_model import SelfModel
from deic_core.planner import PlannerDecision, PlannerMode
from deic_core.explainer import StateExplainer

def test_explainer_operator_style():
    ws = CognitiveState(entropy=5.0, trusted_source_locked=False)
    sm = SelfModel.from_workspace(ws)
    pd = PlannerDecision(mode=PlannerMode.EXPLORE, rationale="testing", recommendation="")
    action = {"type": "query", "target_agent": "A", "item_id": "item_1"}
    
    explainer = StateExplainer()
    html = explainer.generate_explanation(ws, sm, pd, action, style="operator")
    
    assert "[EXPLORE]" in html
    assert "Querying (A, item_1)" in html
    assert "Trust is OPEN" in html

def test_explainer_diagnostic_falsifiability_specific():
    # Setup state for specific counterfactual logic
    ws = CognitiveState(
        entropy=0.5,
        confidence_margin=0.8,
        trusted_source_locked=True,
        trust_distribution={"Agent_A": 1.0},
        top_hypotheses=[
            ({"shifted_items": frozenset({"item_1"}), "val": 2}, 0.9),
            ({"shifted_items": frozenset({"item_1", "item_2"}), "val": 2}, 0.1)
        ],
        all_hypotheses=[({}, 0.9), ({}, 0.1)]
    )
    sm = SelfModel.from_workspace(ws)
    pd = PlannerDecision(mode=PlannerMode.REFINE, rationale="narrowing", recommendation="")
    action = {"type": "query", "target_agent": "A", "item_id": "item_2"}
    
    explainer = StateExplainer()
    diag = explainer.generate_explanation(ws, sm, pd, action, style="diagnostic")
    
    # Needs to mention the runner up's shifted_items {item_1, item_2}
    assert "If evidence confirms shifted_items is {item_1, item_2}, I would switch away" in diag

def test_explainer_diagnostic_falsifiability_abstract():
    # Setup state for abstract counterfactual logic
    ws = CognitiveState(
        entropy=8.0,
        confidence_margin=0.01,
        trusted_source_locked=False,
        top_hypotheses=[({"k": 1}, 0.3), ({"k": 2}, 0.2)],
        all_hypotheses=[({}, 0.3), ({}, 0.2), ({}, 0.1)]
    )
    sm = SelfModel.from_workspace(ws)
    pd = PlannerDecision(mode=PlannerMode.EXPLORE, rationale="lock trust", recommendation="")
    action = {"type": "query", "target_agent": "B", "item_id": "item_X"}
    
    explainer = StateExplainer()
    diag = explainer.generate_explanation(ws, sm, pd, action, style="diagnostic")
    
    assert "Any contradicting evidence from a trusted source" in diag

def test_explainer_escalate():
    ws = CognitiveState(entropy=8.0, trusted_source_locked=False)
    sm = SelfModel.from_workspace(ws)
    pd = PlannerDecision(mode=PlannerMode.ESCALATE, rationale="halt", recommendation="")
    action = {"type": "commit_consensus", "escalated": True, "proposed_inventory": {}}
    
    explainer = StateExplainer()
    op = explainer.generate_explanation(ws, sm, pd, action, style="operator")
    assert "[ESCALATE]" in op
    assert "Escaping to manual review" in op


def test_explainer_diagnostic_omits_advisory_without_trace():
    ws = CognitiveState(
        entropy=0.4,
        confidence_margin=0.9,
        trusted_source_locked=True,
        trust_distribution={"Agent_A": 1.0},
    )
    sm = SelfModel.from_workspace(ws)
    pd = PlannerDecision(mode=PlannerMode.REFINE, rationale="steady", recommendation="")
    action = {"type": "commit_consensus", "escalated": False, "proposed_inventory": {}}

    explainer = StateExplainer()
    diag = explainer.generate_explanation(ws, sm, pd, action, style="diagnostic")

    assert "Advisory Conscience" not in diag
    assert "6. Falsifiability:" in diag


def test_explainer_diagnostic_includes_advisory_only_with_trace():
    ws = CognitiveState(
        entropy=0.6,
        confidence_margin=0.72,
        trusted_source_locked=False,
        conscience_advisory_enabled=True,
        conscience_advisory_trace_complete=True,
        conscience_advisory_label="value_conflict_present",
        conscience_advisory_harm_risk="moderate",
        conscience_advisory_honesty_conflict=True,
        conscience_advisory_responsibility_conflict=False,
        conscience_advisory_repair_needed=False,
    )
    sm = SelfModel.from_workspace(ws)
    pd = PlannerDecision(mode=PlannerMode.REFINE, rationale="steady", recommendation="")
    action = {"type": "commit_consensus", "escalated": False, "proposed_inventory": {}}

    explainer = StateExplainer()
    diag = explainer.generate_explanation(ws, sm, pd, action, style="diagnostic")

    assert "Advisory Conscience" in diag
    assert "Label=value_conflict_present" in diag
    assert "harm_risk=moderate" in diag
    assert "7. Falsifiability:" in diag
