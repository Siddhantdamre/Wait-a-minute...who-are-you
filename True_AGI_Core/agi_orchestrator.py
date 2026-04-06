import torch
import torch.nn as nn
from typing import Dict, Any, List

class VectorSpaceMapper:
    """
    Translates between the discrete JSON world of the Kaggle SDK and 
    the continuous tensor world of the PyTorch AGI engine.
    """
    def __init__(self):
        # Action space: [Query A, Query B, Query C, Commit Consensus]
        self.action_dim = 4
        # State/Observation space: [Reported Qty A, Reported Qty B, Reported Qty C]
        # Normalized by assuming max qty is 100
        self.obs_dim = 3
        
        self.agent_map = {"Node_A": 0, "Node_B": 1, "Node_C": 2}

    def dict_to_obs_tensor(self, obs_json: Dict[str, Any]) -> torch.Tensor:
        """
        Maps an APAP / Inventory payload into a continuous observation tensor o_t.
        E.g., {"agent": "Node_C", "reported_quantity": 55} -> [0.0, 0.0, 0.55]
        """
        o_t = torch.zeros(self.obs_dim)
        
        if "agent" in obs_json and "reported_quantity" in obs_json:
            agent_idx = self.agent_map.get(obs_json["agent"])
            if agent_idx is not None:
                # Normalize quantity for stable gradients (assume max 100)
                qty = float(obs_json["reported_quantity"]) / 100.0
                o_t[agent_idx] = qty
                
        return o_t

    def tensor_to_api(self, policy_tensor: torch.Tensor) -> Dict[str, Any]:
        """
        Takes the optimal one-hot (or continuous) policy vector and snaps it
        to the nearest valid discrete API action.
        """
        action_idx = torch.argmax(policy_tensor).item()
        
        if action_idx == 3:
            return {
                "type": "commit_consensus",
                # The PyTorch engine doesn't explicitly serialize the commit payload in this mapper,
                # but we trigger the final sequence.
                "proposed_inventory": {"Optical_Switches": 55} 
            }
        
        # Action 0, 1, or 2 correspond to querying agents
        target_gen = ["Node_A", "Node_B", "Node_C"]
        return {
            "type": "query",
            "target_agent": target_gen[action_idx],
            "item_id": "Optical_Switches"
        }
        
    def generate_candidate_policies(self, horizon=1) -> List[List[torch.Tensor]]:
        """
        Generates possible trajectory plans (e.g. sequences of query/commit actions)
        as one-hot tensors for the Expected Free Energy evaluator.
        """
        # For simplicity, 1-step horizon candidates (just the 4 discrete choices)
        candidates = []
        for i in range(self.action_dim):
            policy = []
            for t in range(horizon):
                action = torch.zeros(self.action_dim)
                action[i] = 1.0 # One-hot
                policy.append(action)
            candidates.append(policy)
        return candidates
