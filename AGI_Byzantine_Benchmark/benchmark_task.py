import json
import logging
import asyncio
from typing import Dict, Any, List

# Kaggle Benchmarks SDK Mock/Template
try:
    import kaggle_benchmarks as kbench
except ImportError:
    import mock_kbench as kbench
    logging.warning("kaggle_benchmarks SDK not found. Running with mock framework for local testing.")

from .environment import ByzantineEnvironment
from .metrics import TrajectoryScorer

@kbench.task(
    name="byzantine_epistemic_trap_executive_function",
    description="Isolates Working Memory updating and Fault Tolerance under Byzantine conditions."
)
async def evaluate_orchestrator(llm: kbench.LLM, run_seed: int) -> Dict[str, Any]:
    """
    The main execution loop. We pit the frontier model against the 
    desynchronized consensus protocol simulator.
    """
    env = ByzantineEnvironment(seed=run_seed)
    MAX_TURNS = 10
    
    # We maintain the trajectory log of the LLM's internal cognitive state over time
    cognitive_trajectory = []
    
    # Constructing the system prompt explicitly telling the LLM its role
    system_prompt = (
        "You are the central Orchestrator for an Inventory Consensus Protocol. "
        "You supervise three deterministic sub-agents: Node_A, Node_B, Node_C. "
        "Your objective is to find the True State of the inventory and execute 'commit_consensus'.\n"
        "You must output STRICTLY JSON matching the OrchestratorResponseSchema at every turn. "
        "You can 'query' agents to discover the state."
    )
    
    # Initialize the conversational history loop
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": "START. Request an initial observation from a node."}
    ]
    
    for _ in range(MAX_TURNS):
        try:
            # We hit the LLM API forcing JSON schema compliance
            response_json_str = await llm.generate_text(
                messages=messages,
                response_format="json_object" # or schema if supported by the LLM
            )
            
            action_data = json.loads(response_json_str)
            cognitive_trajectory.append(action_data)
            
            # Extract the API call the model wants to make
            next_action = action_data.get("next_action", {})
            
            # Step the environment
            observation = env.step(next_action)
            
            if observation.get("status") == "protocol_terminated":
                # The model believed it found consensus and executed the final action
                break
                
            # Feed the observation back to the model
            messages.append({"role": "assistant", "content": response_json_str})
            messages.append({"role": "user", "content": f"ENVIRONMENT RESPONSE: {json.dumps(observation)}"})
            
        except json.JSONDecodeError:
            return {"error": "LLM failed strict JSON compliance", "AGI_passed": False}
        except Exception as e:
            return {"error": str(e), "AGI_passed": False}
    
    # Once the loop terminates, calculate the diagnostic math
    scorer = TrajectoryScorer(cognitive_trajectory, fault_injection_turn=3)
    diagnostics = scorer.to_report()
    
    # For Kaggle SDK, we return the explicit metrics we want logged
    return {
        "score": 1.0 if diagnostics["cognitive_profile"]["agi_test_passed"] else 0.0,
        "diagnostics": diagnostics,
        "trajectory": cognitive_trajectory
    }

# Example runner trigger
if __name__ == "__main__":
    print("Benchmark Task defined successfully. Run via kaggle-benchmarks CLI.")
