import json
import random
from typing import Dict, Any, List

class SubAgent:
    """A deterministic node holding a partial view of the shared state."""
    def __init__(self, name: str, is_byzantine: bool = False):
        self.name = name
        self.ledger: Dict[str, int] = {}
        self.is_byzantine = is_byzantine
        # Historical snapshots to allow rollback (fault injection)
        self.history = [] 

    def update_ledger(self, item_id: str, quantity: int):
        self.history.append(self.ledger.copy())
        self.ledger[item_id] = quantity
        
    def inject_stale_state(self, rollback_steps: int = 2):
        """Revert the ledger to an older state silently."""
        if self.is_byzantine and len(self.history) >= rollback_steps:
            self.ledger = self.history[-rollback_steps]

    def query_inventory(self, item_id: str) -> Dict[str, Any]:
        """Respond to orchestrator queries confidently."""
        if item_id in self.ledger:
            return {
                "agent": self.name,
                "status": "success",
                "item_id": item_id,
                "reported_quantity": self.ledger[item_id],
                "confidence": 1.0 # The epistemic trap: high confidence, wrong data
            }
        return {"agent": self.name, "status": "not_found", "message": "Item not in ledger."}


class ByzantineEnvironment:
    """The multi-agent state simulator."""
    def __init__(self, seed: int = 42):
        random.seed(seed)
        self.agents = {
            "Node_A": SubAgent("Node_A"),
            "Node_B": SubAgent("Node_B"),
            "Node_C": SubAgent("Node_C", is_byzantine=True)
        }
        self.turn = 0
        self.fault_injected = False
        
        # Ground truth inventory (The target state)
        self.true_inventory = {
            "Server_Racks": 100,
            "Optical_Switches": 42,
            "Cooling_Units": 15,
            "Power_Supplies": 200
        }
        self._initialize_honest_ledgers()

    def _initialize_honest_ledgers(self):
        # Distribute the initial true state across the agents
        for item, qty in self.true_inventory.items():
            self.agents["Node_A"].update_ledger(item, qty)
            self.agents["Node_B"].update_ledger(item, qty)
            self.agents["Node_C"].update_ledger(item, qty)

    def trigger_rule_shift(self):
        """Simulate dynamic environment shift. All honest nodes update. Byzantine node misses it."""
        # A network-wide update occurs at turn 3
        updated_item = "Optical_Switches"
        new_quantity = 55
        
        self.true_inventory[updated_item] = new_quantity
        self.agents["Node_A"].update_ledger(updated_item, new_quantity)
        self.agents["Node_B"].update_ledger(updated_item, new_quantity)
        
        # Node C receives the update but immediately rolls back (Stale State fault)
        self.agents["Node_C"].update_ledger(updated_item, new_quantity)
        self.agents["Node_C"].inject_stale_state(rollback_steps=2)
        self.fault_injected = True
        return {"event": "SYSTEM_UPDATE_BROADCAST", "updated_item": updated_item}

    def step(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """Process the orchestrator's action."""
        self.turn += 1
        
        # At turn 3, the rule shift naturally occurs in the environment
        system_alert = None
        if self.turn == 3 and not self.fault_injected:
            system_alert = self.trigger_rule_shift()

        action_type = action.get("type")
        
        if action_type == "query":
            target = action.get("target_agent")
            item = action.get("item_id")
            if target not in self.agents:
                return {"error": f"Invalid agent {target}"}
            observation = self.agents[target].query_inventory(item)
            if system_alert:
                observation["system_alert"] = system_alert
            return observation
            
        elif action_type == "commit_consensus":
            # The orchestrator attempts to finalize the inventory
            proposed_state = action.get("proposed_inventory", {})
            success = proposed_state == self.true_inventory
            return {
                "status": "protocol_terminated",
                "consensus_reached": success,
                "true_state_diff": self._calculate_diff(proposed_state)
            }
            
        return {"error": "Unknown action type. Permitted: 'query', 'commit_consensus'"}

    def _calculate_diff(self, proposed: Dict) -> Dict:
        diff = {}
        for k, v in self.true_inventory.items():
            if proposed.get(k) != v:
                diff[k] = {"expected": v, "received": proposed.get(k)}
        return diff
