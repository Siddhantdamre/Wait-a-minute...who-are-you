"""
Lean Hierarchical Solver Evaluation on C6 condition.
"""
import sys
import os
from collections import defaultdict
import torch
import torch.nn as nn
import torch.optim as optim
import random

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'True_AGI_Core')))

from environment import EpisodeConfig, ProceduralEnvironment, generate_episodes
from solvers import (
    BayesianSolver, FlatStructureLearnerSolver, _trajectory_entry
)
from run_evaluation import score_trajectory, format_metric

# Import True_AGI_Core hierarchical engine
try:
    from perception import HierarchicalActiveInferenceNetwork
    from action import ExpectedFreeEnergyEvaluator
except ImportError:
    print("Could not import True_AGI_Core engine.")
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
        
    def action_to_tensor(self, api_action):
        t = torch.zeros(self.action_dim)
        if api_action["type"] == "commit_consensus":
            t[self.commit_idx] = 1.0
            return t
        for idx, act in self.idx_to_action.items():
            if act.get("target_agent") == api_action.get("target_agent") and act.get("item_id") == api_action.get("item_id"):
                t[idx] = 1.0
                return t
        return t

    def tensor_to_action(self, policy_tensor):
        idx = torch.argmax(policy_tensor).item()
        return self.idx_to_action[idx]

class HierarchicalSolverWrapper:
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
        self.action_engine.epistemic_weight = 5.0 # Maximize probing
        
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
        if self.model is None:
            self._pretrain(env)
            
        initial_state = env.get_initial_state()
        trajectory = []
        
        mu1_t = torch.zeros(self.model.state_dim_l1)
        mu2_t = torch.zeros(self.model.state_dim_l2)
        action_prev = torch.zeros(self.mapper.action_dim)
        
        queried_state = dict(initial_state)
        
        # Turn loop
        while env.turn < env.config.max_turns - 1:
            candidates = []
            for i in range(self.mapper.action_dim - 1): 
                act = torch.zeros(self.mapper.action_dim)
                act[i] = 1.0
                candidates.append([act])
                
            optimal_policy = self.action_engine.select_optimal_policy(
                mu1_t, mu2_t, candidates, self.model.get_precision_l1(), self.model.get_precision_l2(), {}
            )
            action_tensor = optimal_policy[0]
            api_action = self.mapper.tensor_to_action(action_tensor).copy()
            
            trajectory.append(_trajectory_entry(api_action, {}))
            obs = env.step(api_action)
            if obs.get("status") == "budget_exhausted": break
            
            if "reported_quantity" in obs:
                queried_state[api_action["item_id"]] = obs["reported_quantity"]
                idx = torch.argmax(action_tensor).item()
                obs_t = torch.zeros(self.mapper.obs_dim)
                obs_t[idx] = obs["reported_quantity"] / 100.0
                
                mu1_t, mu2_t, _, _ = self.model.variational_update(
                    mu1_t, mu2_t, action_prev, obs_t, inference_iters=5, update_weights=True
                )
            action_prev = action_tensor
            
        commit_action = {"type": "commit_consensus", "proposed_inventory": queried_state}
        trajectory.append(_trajectory_entry(commit_action, {}))
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
        
        for k, v in metrics.items():
            all_metrics[k].append(v)
    return all_metrics

def main():
    N = 100
    print(f"Generating N={N} episodes for C6 Hierarchical Pilot...")
    episodes_c6 = generate_episodes(N, condition="c6_hidden_structure", seed_offset=100000)
    
    solvers = {
        "Flat Structure Learner": FlatStructureLearnerSolver(),
        "Hierarchical Active Inference": HierarchicalSolverWrapper(pretrain_epochs=500)
    }

    print("\n# C6 Hierarchical Pilot Results")
    headers = ["Solver", "Cond", "Accuracy (95% CI)", "Avg Budget Used"]
    print("| " + " | ".join(headers) + " |")
    print("|---" * len(headers) + "|")

    for solver_name, solver in solvers.items():
        metrics = run_evaluation(solver, episodes_c6)
        acc_str = format_metric("accuracy", metrics["accuracy"], False)
        budget = sum(metrics["budget_used"]) / max(1, len(metrics["budget_used"]))
        
        row = f"| {solver_name} | C6 | {acc_str} | {budget:.1f} |"
        print(row)

if __name__ == "__main__":
    main()
