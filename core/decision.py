from pydantic import BaseModel
from typing import List


class DecisionOption(BaseModel):
    label: str
    description: str
    emphasized_values: List[str]
    sacrificed_values: List[str]


class DecisionSimulationResult(BaseModel):
    option: str
    narrative: str
    gained_values: List[str]
    lost_values: List[str]
    risk: str
    explanation: str

class DecisionSimulator:
    def simulate(self, option: DecisionOption) -> DecisionSimulationResult:
        # Risk heuristic (simple & explainable)
        if "Safety" in option.sacrificed_values:
            risk = "High"
        elif "Harmony" in option.sacrificed_values:
            risk = "Medium"
        else:
            risk = "Low"

        narrative = (
            f"Choosing to {option.description.lower()} led to immediate action. "
            f"The outcome reflected the values emphasized, while some costs were felt."
        )

        explanation = (
            f"This choice prioritizes {', '.join(option.emphasized_values)} "
            f"at the expense of {', '.join(option.sacrificed_values)}."
        )

        return DecisionSimulationResult(
            option=option.label,
            narrative=narrative,
            gained_values=option.emphasized_values,
            lost_values=option.sacrificed_values,
            risk=risk,
            explanation=explanation
        )
