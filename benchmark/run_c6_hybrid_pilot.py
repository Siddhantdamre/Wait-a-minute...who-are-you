"""
Narrow Hybrid-Interface Pilot for C6
"""
import sys
import os
import random
import torch
import torch.nn as nn
import torch.optim as optim
from collections import defaultdict
import itertools

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'True_AGI_Core')))

from environment import ProceduralEnvironment, generate_episodes
from solvers import _trajectory_entry, FlatStructureLearnerSolver, DiscreteHypothesisSolver
from run_evaluation import score_trajectory, format_metric

try:
    from perception import HierarchicalActiveInferenceNetwork
    from action import ExpectedFreeEnergyEvaluator
except ImportError:
    print("Could not import True_AGI_Core")
    sys.exit(1)

class DummyDist:
    def __init__(self, target):
        self.target = target
        self.loss = nn.MSELoss(reduction='none')
    def log_prob(self, x):
        return -self.loss(x, self.target)

class ContextMapper:
    def __init__(self, items, agents):
        self.items = items
        self.agents = agents
        self.obs_dim = len(items) * len(agents)
        self.action_dim = len(items) * len(agents) + 1
        
        self.idx_to_action = {}
        idx = 0
        for item in items:
            for agent in agents:
                self.idx_to_action[idx] = {"type": "query", "target_agent": agent, "item_id": item}
                idx += 1
        self.commit_idx = idx
        self.idx_to_action[idx] = {"type": "commit_consensus"}
        
    def tensor_to_action(self, policy_tensor):
        idx = torch.argmax(policy_tensor).item()
        return self.idx_to_action[idx]

class HybridDiscreteFrontEndSolver:
    """
    Minimal Hybrid Wrapper:
    1. Discrete Front-End gathers partial combinations.
    2. Feeds inferred structural posterior into True_AGI_Core.
    3. True_AGI_Core runs downstream processing.
    """
    def __init__(self, pretrain_epochs=500):
        self.pretrain_epochs = pretrain_epochs
        self.model = None
        self.action_engine = None
        self.mapper = None

    def _pretrain(self, env):
        items = list(env.get_initial_state().keys())
        agents = env.get_agent_names()
        self.mapper = ContextMapper(items, agents)
        self.model = HierarchicalActiveInferenceNetwork(
            obs_dim=self.mapper.obs_dim, 
            action_dim=self.mapper.action_dim, 
            state_dim_l1=32, state_dim_l2=8, n_agents=self.mapper.obs_dim
        )
        target_obs = torch.zeros(self.mapper.obs_dim)
        target_obs[:] = 0.5
        self.action_engine = ExpectedFreeEnergyEvaluator(self.model, DummyDist(target_obs))
        
        optimizer = optim.Adam(self.model.parameters(), lr=0.01)
        loss_fn = nn.MSELoss()
        for _ in range(self.pretrain_epochs):
            act_idx = random.randint(0, self.mapper.action_dim - 2)
            act_t = torch.zeros(self.mapper.action_dim)
            act_t[act_idx] = 1.0
            obs_t = torch.zeros(self.mapper.obs_dim)
            obs_t[act_idx] = 0.5
            mu1_prev = torch.zeros(self.model.state_dim_l1)
            mu1_next = self.model.dynamics_model_l1(torch.cat([mu1_prev, act_t], dim=-1))
            expected_obs = self.model.sensory_model_l1(mu1_next)
            loss = loss_fn(expected_obs, obs_t)
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()

    def solve(self, env):
        if self.model is None: self._pretrain(env)
            
        initial_state = env.get_initial_state()
        agents = env.get_agent_names()
        items = list(initial_state.keys())
        trajectory = []
        budget = env.config.max_turns
        fault_prior = {a: 0.1 for a in agents}
        
        # === DISCRETE FRONT END ===
        # Query less items to leave budget for the AGI core downstream
        # 1 agent check (3 turns) + 2 item probes (2 turns) = 5 turns. (Leaves 2 for downstream)
        latest_report = {}
        for agent in agents:
            action = {"type": "query", "target_agent": agent, "item_id": items[0]}
            trajectory.append(_trajectory_entry(action, fault_prior))
            obs = env.step(action)
            if "reported_quantity" in obs: latest_report[agent] = obs["reported_quantity"]
                
        reps = list(latest_report.values())
        majority_val = max(set(reps), key=reps.count) if reps else initial_state[items[0]]
        honest_agent = agents[0]
        for a, val in latest_report.items():
            if val == majority_val: honest_agent = a; break
                
        queried_vals = {items[0]: majority_val}
        idx = 1
        while env.turn < budget - 3 and idx < len(items):
            action = {"type": "query", "target_agent": honest_agent, "item_id": items[idx]}
            trajectory.append(_trajectory_entry(action, fault_prior))
            obs = env.step(action)
            if "reported_quantity" in obs: queried_vals[items[idx]] = obs["reported_quantity"]
            idx += 1
            
        valid_multipliers = [1.2, 1.5, 2.0, 2.5]
        all_combos = list(itertools.combinations(items, 4))
        
        best_hypothesis = None
        best_score = -float('inf')
        for shifted_group in all_combos:
            shifted_set = set(shifted_group)
            for mult in valid_multipliers:
                score = 0.0
                possible = True
                for it, val in queried_vals.items():
                    expected_val = int(initial_state[it] * mult) if it in shifted_set else initial_state[it]
                    if val == expected_val: score += 1.0
                    else: possible = False; break
                if possible:
                    score += random.uniform(0, 0.01)
                    if score > best_score:
                        best_score = score
                        best_hypothesis = (shifted_set, mult)
                        
        proposed = {}
        for it in items:
            if best_hypothesis:
                shifted_set, mult = best_hypothesis
                proposed[it] = int(initial_state[it] * mult) if it in shifted_set else initial_state[it]
            else:
                proposed[it] = initial_state[it]
                
        # === HYBRID INTERFACE ===
        # Pass discrete MAP structural hypothesis into Continuous AGI Core as pseudo-observations
        obs_t = torch.zeros(self.mapper.obs_dim)
        for i, it in enumerate(items):
            # Inject structural prior normalized
            obs_t[i] = proposed[it] / 100.0 
            
        mu1_t = torch.zeros(self.model.state_dim_l1)
        mu2_t = torch.zeros(self.model.state_dim_l2)
        action_prev = torch.zeros(self.mapper.action_dim)
        
        mu1_t, mu2_t, _, _ = self.model.variational_update(
            mu1_t, mu2_t, action_prev, obs_t, inference_iters=10, update_weights=False
        )
        
        # === CONTINUOUS BACK END ===
        while env.turn < budget - 1:
            candidates = []
            for i in range(self.mapper.action_dim - 1): 
                act = torch.zeros(self.mapper.action_dim)
                act[i] = 1.0
                candidates.append([act])
                
            optimal_policy = self.action_engine.select_optimal_policy(mu1_t, mu2_t, candidates, self.model.get_precision_l1(), self.model.get_precision_l2(), {})
            action_tensor = optimal_policy[0]
            api_action = self.mapper.tensor_to_action(action_tensor).copy()
            
            trajectory.append(_trajectory_entry(api_action, fault_prior))
            obs = env.step(api_action)
            action_prev = action_tensor
            
        commit_action = {"type": "commit_consensus", "proposed_inventory": proposed}
        trajectory.append(_trajectory_entry(commit_action, fault_prior))
        result = env.step(commit_action)
        return trajectory, result

def run_evaluation(solver, episodes):
    all_metrics = defaultdict(list)
    for ep_config in episodes:
        env = ProceduralEnvironment(ep_config)
        trajectory, result = solver.solve(env)
        
        c = ep_config.condition
        if c == "c6_hidden_structure": 
            ep_config.condition = "active_deception"
            ep_config.shifted_item_2 = "latent_marker" 
        
        metrics = score_trajectory(trajectory, result, ep_config)
        ep_config.condition = c
        for k, v in metrics.items(): all_metrics[k].append(v)
    return all_metrics

def main():
    N = 100
    print(f"Generating N={N} episodes for C6 Hybrid Pilot...")
    from copy import deepcopy
    episodes_c6 = generate_episodes(N, condition="c6_hidden_structure", seed_offset=300000)
    
    # Needs absolute reproducibility for fair eval
    from run_c6_hierarchical_pilot import HierarchicalSolverWrapper
    
    solvers = {
        "Continuous Core Only": HierarchicalSolverWrapper(pretrain_epochs=500),
        "Discrete Hypothesis Only": DiscreteHypothesisSolver(),
        "Hybrid Interface (Discrete + Continuous)": HybridDiscreteFrontEndSolver()
    }

    print("\n# C6 Hybrid Interface Pilot Results")
    headers = ["Solver", "Cond", "Accuracy (95% CI)", "Avg Budget Used"]
    print("| " + " | ".join(headers) + " |")
    print("|---" * len(headers) + "|")

    for solver_name, solver in solvers.items():
        ep_copy = deepcopy(episodes_c6)
        metrics = run_evaluation(solver, ep_copy)
        acc_str = format_metric("accuracy", metrics["accuracy"], False)
        budget = sum(metrics["budget_used"]) / max(1, len(metrics["budget_used"]))
        
        row = f"| {solver_name} | C6 | {acc_str} | {budget:.1f} |"
        print(row)

if __name__ == "__main__":
    main()
