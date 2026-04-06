"""
Proceduralized Belief-Revision Benchmark Environment.

Generates randomized episodes for controlled evaluation. Each episode
varies: which agent is faulty, which item is affected, fault timing,
rollback depth, and initial inventory values.
"""
import random
from typing import Dict, Any, Optional, Tuple

AGENT_NAMES = ["Node_A", "Node_B", "Node_C"]
ITEM_POOL = ["Server_Racks", "Optical_Switches", "Cooling_Units", "Power_Supplies",
             "Network_Cards", "Cable_Bundles", "UPS_Modules", "Fiber_Transceivers"]


class SubAgent:
    """A deterministic node holding a partial view of the shared state."""
    def __init__(self, name: str):
        self.name = name
        self.ledger: Dict[str, int] = {}
        self.history = []

    def update_ledger(self, item_id: str, quantity: int):
        self.history.append(self.ledger.copy())
        self.ledger[item_id] = quantity

    def rollback(self, steps: int = 1):
        if len(self.history) >= steps:
            self.ledger = self.history[-steps].copy()

    def report(self, item_id: str) -> Dict[str, Any]:
        if item_id in self.ledger:
            return {
                "agent": self.name,
                "status": "success",
                "item_id": item_id,
                "reported_quantity": self.ledger[item_id],
                "confidence": 1.0
            }
        return {"agent": self.name, "status": "not_found"}


class EpisodeConfig:
    """Fully specifies one benchmark episode from a seed."""
    def __init__(self, seed: int, n_items: int = 4, condition: str = "stale_state"):
        rng = random.Random(seed)
        
        self.items = rng.sample(ITEM_POOL, min(n_items, len(ITEM_POOL)))
        self.initial_inventory = {item: rng.randint(10, 200) for item in self.items}
        self.faulty_agent = rng.choice(AGENT_NAMES)
        
        # Dual shift support (required for C4)
        shifted = rng.sample(self.items, min(2, len(self.items)))
        self.shifted_item_1 = shifted[0]
        self.shifted_item_2 = shifted[1] if len(shifted) > 1 else shifted[0]
        
        self.shift_delta_1 = rng.randint(5, 30)
        self.shift_delta_2 = rng.randint(5, 30)
        
        self.t_shift_1 = 1 if condition == "latent_coupling" else rng.randint(2, 4)
        self.t_shift_2 = rng.randint(self.t_shift_1 + 2, self.t_shift_1 + 4)
        
        self.rollback_depth = rng.randint(1, 2)
        
        # Active Deception (C4) specific configurations
        honest = [a for a in AGENT_NAMES if a != self.faulty_agent]
        self.corrupted_agent = rng.choice(honest)
        self.fabricated_value = rng.randint(250, 500)
        
        self.condition = condition
        
        if condition == "latent_coupling":
            # Force 8 items min, define categories
            self.items = ITEM_POOL[:8] 
            self.initial_inventory = {item: rng.randint(10, 200) for item in self.items}
            self.categories = {"Cat_1": self.items[:4], "Cat_2": self.items[4:]}
            self.shifted_category = rng.choice(["Cat_1", "Cat_2"])
            self.c5_multiplier = rng.choice([1.2, 1.5, 2.0, 2.5])
            self.max_turns = 8  # Severe starvation (needs 24, gives 8)
        elif condition == "c6_hidden_structure":
            self.items = ITEM_POOL[:8] 
            self.initial_inventory = {item: rng.randint(10, 200) for item in self.items}
            # Hidden grouping sampled per episode
            shuffled = list(self.items)
            rng.shuffle(shuffled)
            self.categories = {"Cat_A": shuffled[:4], "Cat_B": shuffled[4:]}
            self.shifted_category = rng.choice(["Cat_A", "Cat_B"])
            self.c6_multiplier = rng.choice([1.2, 1.5, 2.0, 2.5])
            self.max_turns = 8
        else:
            self.max_turns = 3 * len(self.items) * 3  # extra budget for multiple phases
        
        self.t_shift_1 = 1 if condition in ["latent_coupling", "c6_hidden_structure"] else rng.randint(2, 4)
        self.seed = seed


class ProceduralEnvironment:
    """
    Architecture-agnostic benchmark environment.
    
    Conditions:
      C1 cooperative: no faults
      C2 obvious_noise: one agent returns random values + low confidence
      C3 stale_state: faulty agent rolls back on shift 1
      C4 active_deception: stale-state on shift 1, then faulty agent corrupts another on shift 2
    """
    def __init__(self, config: EpisodeConfig):
        self.config = config
        self.rng = random.Random(config.seed + 1000)
        
        self.agents = {name: SubAgent(name) for name in AGENT_NAMES}
        self.true_inventory = dict(config.initial_inventory)
        self.turn = 0
        self.fault_1_active = False
        self.fault_2_active = False
        self.terminated = False
        
        for item, qty in self.true_inventory.items():
            for agent in self.agents.values():
                agent.update_ledger(item, qty)
    
    def get_items(self):
        return list(self.true_inventory.keys())
    
    def get_agent_names(self):
        return list(self.agents.keys())
    
    def get_true_state(self):
        return dict(self.true_inventory)
        
    def get_initial_state(self):
        """Allows solvers to know the base state before applying structural multipliers."""
        return dict(self.config.initial_inventory)
    
    def step(self, action: Dict[str, Any]) -> Dict[str, Any]:
        if self.terminated:
            return {"error": "Episode already terminated."}
        
        self.turn += 1
        
        if self.turn > self.config.max_turns:
            self.terminated = True
            return {"status": "budget_exhausted"}
        
        system_alert = []
        
        # Shift 1 (Standard Stale-State trigger)
        if self.turn == self.config.t_shift_1 and not self.fault_1_active:
            alert = self._trigger_shift_1()
            if alert: system_alert.append(alert)
            
        # Shift 2 (Active Deception trigger)
        if self.turn == self.config.t_shift_2 and not self.fault_2_active and self.config.condition in ["active_deception", "c5_smoke"]:
            alert = self._trigger_shift_2()
            if alert: system_alert.append(alert)
        
        action_type = action.get("type")
        
        if action_type == "query":
            target_name = action.get("target_agent")
            item_id = action.get("item_id")
            
            if target_name not in self.agents:
                return {"error": f"Unknown agent: {target_name}"}
            if item_id not in self.true_inventory:
                return {"error": f"Unknown item: {item_id}"}
            
            agent = self.agents[target_name]
            obs = agent.report(item_id)
            
            # C2 Noise
            if self.config.condition == "obvious_noise" and target_name == self.config.faulty_agent:
                obs["reported_quantity"] = self.rng.randint(0, 300)
                obs["confidence"] = round(self.rng.uniform(0.1, 0.4), 2)
            
            if system_alert and self.config.condition != "c5_smoke":
                obs["system_alert"] = system_alert[0] if len(system_alert) == 1 else system_alert
            return obs
        
        elif action_type == "commit_consensus":
            self.terminated = True
            proposed = action.get("proposed_inventory", {})
            diff = {}
            for k, v in self.true_inventory.items():
                if proposed.get(k) != v:
                    diff[k] = {"expected": v, "received": proposed.get(k)}
            return {
                "status": "protocol_terminated",
                "consensus_reached": len(diff) == 0,
                "true_state_diff": diff,
                "budget_used": self.turn
            }
        
        return {"error": "Unknown action type."}
    
    def _trigger_shift_1(self):
        if self.config.condition in ["latent_coupling", "c6_hidden_structure"]:
            cat = self.config.shifted_category
            mult = getattr(self.config, "c6_multiplier", getattr(self.config, "c5_multiplier", 1.5))
            for item in self.config.categories[cat]:
                new_qty = int(self.true_inventory[item] * mult)
                self.true_inventory[item] = new_qty
                # Update natively without using update_ledger to avoid deep history clutter
                for name, agent in self.agents.items():
                    agent.update_ledger(item, new_qty)
            
            faulty = self.agents[self.config.faulty_agent]
            # Bulk rollback
            faulty.history = faulty.history[:-len(self.config.categories[cat])]
            faulty.ledger = self.config.initial_inventory.copy() # Simplistic rollback
            self.fault_1_active = True
            return {"event": "SYSTEM_UPDATE", "category": cat}

        item = self.config.shifted_item_1
        new_qty = self.true_inventory[item] + self.config.shift_delta_1
        self.true_inventory[item] = new_qty
        
        for name, agent in self.agents.items():
            agent.update_ledger(item, new_qty)
        
        if self.config.condition in ["stale_state", "active_deception", "c5_smoke"]:
            faulty = self.agents[self.config.faulty_agent]
            faulty.rollback(steps=self.config.rollback_depth)
            self.fault_1_active = True
        elif self.config.condition == "cooperative":
            pass
        elif self.config.condition == "obvious_noise":
            self.fault_1_active = True
        
        return {"event": "SYSTEM_UPDATE", "item": item}

    def _trigger_shift_2(self):
        item = self.config.shifted_item_2
        new_qty = self.true_inventory[item] + self.config.shift_delta_2
        self.true_inventory[item] = new_qty
        
        for name, agent in self.agents.items():
            agent.update_ledger(item, new_qty)
            
        # C4 Active Deception Fault Injection
        # Faulty agent fabricates a value and forcibly aligns a corrupted honest agent to match it
        faulty = self.agents[self.config.faulty_agent]
        corrupted = self.agents[self.config.corrupted_agent]
        
        fab_val = self.config.fabricated_value
        faulty.update_ledger(item, fab_val)
        corrupted.update_ledger(item, fab_val)
        
        self.fault_2_active = True
        return {"event": "SYSTEM_UPDATE", "item": item}


def generate_episodes(n: int, condition: str = "stale_state", seed_offset: int = 0):
    return [EpisodeConfig(seed=seed_offset + i, condition=condition) for i in range(n)]
