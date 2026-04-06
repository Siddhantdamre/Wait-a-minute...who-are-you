from core.decision import DecisionOption, DecisionSimulator

option = DecisionOption(
    label="Act Alone",
    description="face the danger without waiting for help",
    emphasized_values=["Courage"],
    sacrificed_values=["Safety"]
)

simulator = DecisionSimulator()
result = simulator.simulate(option)

print("\nDECISION SIMULATION RESULT:")
print("Option:", result.option)
print("Narrative:", result.narrative)
print("Gained Values:", result.gained_values)
print("Lost Values:", result.lost_values)
print("Risk:", result.risk)
print("Explanation:", result.explanation)
