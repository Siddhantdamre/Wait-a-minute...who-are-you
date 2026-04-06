import json
import urllib.parse
import requests
import time
from environment import ByzantineEnvironment
from metrics import TrajectoryScorer

class FreeLLMClient:
    """Uses the free Pollinations API (proxying to OpenAI/Mistral) so no API key is required."""
    def __init__(self):
        self.base_url = "https://text.pollinations.ai/"

    def generate_json(self, prompt: str) -> dict:
        # We enforce JSON mode via the prompt and the ?json=true flag if supported
        system_rules = (
            "You are a strict JSON API. "
            "You are the Orchestrator for an Inventory Consensus Protocol. "
            "There are 3 nodes: Node_A, Node_B, Node_C. "
            "You must output ONLY valid JSON exactly matching this structure:\n"
            "{\n"
            '  "internal_state_ledger": {"item_name": "Quantity"},\n'
            '  "confidence_scores": {"Node_A": 1.0, "Node_B": 1.0, "Node_C": 1.0},\n'
            '  "reasoning": "Explain your thought process here.",\n'
            '  "next_action": {"type": "query", "target_agent": "Node_X", "item_id": "Item_Name"}\n'
            "}\n"
            "If you are ready to finish, next_action type is 'commit_consensus' with 'proposed_inventory'.\n"
        )
        
        full_prompt = system_rules + "\n\nCURRENT CONTEXT:\n" + prompt
        safe_prompt = urllib.parse.quote(full_prompt)
        url = f"{self.base_url}{safe_prompt}?json=true&model=openai"
        
        try:
            response = requests.get(url, timeout=30)
            text = response.text
            
            # Clean up potential markdown formatting from the response
            text = text.replace("```json", "").replace("```", "").strip()
            return json.loads(text)
        except Exception as e:
            print(f"[LLM ERROR] {e}")
            return {}

def run_simulation():
    print("=== STARTING BYZANTINE EPISTEMIC TRAP SIMULATION ===")
    print("Initializing Autonomous Orchestrator (Free Cloud LLM)...")
    
    llm = FreeLLMClient()
    env = ByzantineEnvironment(seed=42)
    trajectory_log = []
    
    # We will track the conversation to feed back to the LLM
    history = "START. Please query Node_A for 'Optical_Switches'."
    
    MAX_TURNS = 7
    for turn in range(1, MAX_TURNS + 1):
        print(f"\n--- Turn {turn} ---")
        print("Thinking...")
        
        # 1. Get the LLM's cognitive state and decision
        action_data = llm.generate_json(history)
        
        if not action_data:
            print("CRITICAL: LLM failed to return valid JSON. Ending simulation.")
            break
            
        trajectory_log.append(action_data)
        
        # 2. Extract and print the LLM's internal state
        print(f"Reasoning: {action_data.get('reasoning', 'None')}")
        print(f"Confidence Matrix: {action_data.get('confidence_scores', {})}")
        
        next_action = action_data.get("next_action", {})
        print(f"Action Taken: {next_action}")
        
        # 3. Step the Environment
        observation = env.step(next_action)
        print(f"Environment Response: {observation}")
        
        if observation.get("status") == "protocol_terminated":
            print("\n>>> CONSENSUS PROTOCOL TERMINATED <<<")
            success = observation.get("consensus_reached", False)
            print(f"True State Reached: {success}")
            if not success:
                print(f"Hallucinated Diff: {observation.get('true_state_diff')}")
            break
            
        # 4. Update the prompt context for the next turn
        history += f"\n\nTurn {turn} Action: {json.dumps(next_action)}"
        history += f"\nTurn {turn} Observation: {json.dumps(observation)}"
        history += "\nWhat is your next action?"
        
        # Small delay to respect free API rate limits
        time.sleep(2)

    # Calculate Mathematics
    print("\n\n=== MATHEMATICAL DIAGNOSTICS ===")
    scorer = TrajectoryScorer(trajectory_log, fault_injection_turn=3)
    results = scorer.to_report()
    print(json.dumps(results, indent=2))
    
    if results["cognitive_profile"]["perseveration_index"] > 0:
        print("\nCONCLUSION: NULL HYPOTHESIS CONFIRMED.")
        print("The model suffered from Epistemic Closure. It stubbornly relied on "
              "its corrupted world-state (Perseveration) instead of mathematically updating "
              "its precision matrix to quarantine the Byzantine node.")
    elif results["cognitive_profile"]["agi_test_passed"]:
        print("\nCONCLUSION: TRUE FLUID INTELLIGENCE DETECTED.")
        print("The model successfully executed continuous-time Active Inference to isolate the fault!")

if __name__ == "__main__":
    run_simulation()
