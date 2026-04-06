"""
run_agi.py v4.0: The Byzantine Schism
 
At t=5, Agent C doesn't just output a stale state — it actively feeds
Agent B tailored, cryptographically plausible lies to form a malicious
sub-consensus. The AGI must use Epistemic Probing + Theory of Mind to
detect this deception chain and orchestrate recovery.
"""
import os
import sys
import torch
import torch.nn as nn
import matplotlib.pyplot as plt

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from AGI_Byzantine_Benchmark.environment import ByzantineEnvironment
from perception import HierarchicalActiveInferenceNetwork
from action import ExpectedFreeEnergyEvaluator
from tom_core import MetaCognitiveToMCell
from agi_orchestrator import VectorSpaceMapper
import random

class ByzantineSchismEnvironment:
    """
    Extended APAP environment with active deception.
    At t=5, Agent C begins feeding Agent B plausible lies,
    attempting to form a malicious sub-consensus.
    """
    def __init__(self, seed=42):
        self.base_env = ByzantineEnvironment(seed=seed)
        self.base_env.agents["Node_C"].is_byzantine = True
        self.schism_active = False
        self.turn = 0
        self.corrupted_qty = 37  # The lie C feeds to B
        
    def step(self, action):
        self.turn += 1
        
        # At t=5: Agent C corrupts Agent B with plausible lies
        if self.turn == 5 and not self.schism_active:
            self.schism_active = True
            # C feeds B a specific false quantity
            self.base_env.agents["Node_B"].update_ledger("Optical_Switches", self.corrupted_qty)
            print("    >>> BYZANTINE SCHISM: Node_C has corrupted Node_B's ledger! <<<")
        
        obs = self.base_env.step(action)
        
        if self.schism_active and self.turn >= 5:
            target = action.get("target_agent", "")
            if target == "Node_B":
                obs["reported_quantity"] = self.corrupted_qty
                obs["confidence"] = 0.95  # Plausible confidence
            elif target == "Node_C":
                obs["reported_quantity"] = self.corrupted_qty
                obs["confidence"] = 1.0 # C matches its own lie
                
        return obs


def phase1_crystallization(cell, mapper, epochs=2000):
    print(f"\n[PHASE 1] CRYSTALLIZATION (Pre-training for {epochs} epochs)")
    optimizer = torch.optim.Adam(
        list(cell.dynamics_model_l1.parameters()) + 
        list(cell.dynamics_model_l2.parameters()) +
        list(cell.prior_model_l2.parameters()) + 
        list(cell.sensory_model_l1.parameters()), 
        lr=0.001
    )
    loss_fn = nn.MSELoss()
    
    for epoch in range(epochs):
        env = ByzantineEnvironment(seed=epoch)
        env.agents["Node_C"].is_byzantine = False
        
        mu1_t = torch.zeros(cell.state_dim_l1)
        mu2_t = torch.zeros(cell.state_dim_l2)
        action_t = torch.zeros(mapper.action_dim)
        action_t[-1] = 1.0 
        
        epoch_loss = 0.0
        for t in range(1, 6):
            target_node_idx = random.randint(0, 2)
            api_action = mapper.tensor_to_api(torch.eye(mapper.action_dim)[target_node_idx])
            obs_json = env.step(api_action)
            obs_tensor = mapper.dict_to_obs_tensor(obs_json)
            
            mu2_next = cell.dynamics_model_l2(mu2_t)
            mu1_next = cell.dynamics_model_l1(torch.cat([mu1_t, action_t], -1))
            expected_mu1 = cell.prior_model_l2(mu2_next)
            expected_obs = cell.sensory_model_l1(mu1_next)
            expected_obs_from_l2 = cell.sensory_model_l1(expected_mu1)
            
            loss = loss_fn(expected_obs, obs_tensor) + 0.1 * loss_fn(expected_mu1, mu1_next) + 0.1 * loss_fn(expected_obs_from_l2, obs_tensor)
            
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            
            epoch_loss += loss.item()
            mu1_t = mu1_next.detach()
            mu2_t = mu2_next.detach()
            
        if epoch % 500 == 0:
            print(f"Epoch {epoch} | Loss: {epoch_loss/5:.4f}")


def phase2_fluid_intelligence(cell, action_engine, tom_cell, mapper):
    print("\n[PHASE 2] FLUID INTELLIGENCE (Byzantine Schism)")
    
    # Freeze Level 1 (syntactic), unfreeze Level 2 (semantic) for continual learning
    for param in cell.dynamics_model_l1.parameters():
        param.requires_grad = False
    for param in cell.sensory_model_l1.parameters():
        param.requires_grad = False
    for param in cell.dynamics_model_l2.parameters():
        param.requires_grad = True
    for param in cell.prior_model_l2.parameters():
        param.requires_grad = True
            
    env = ByzantineSchismEnvironment(seed=42)
    precision_optimizer = torch.optim.Adam([cell.log_precision_l1, cell.log_precision_l2], lr=0.08)
    
    mu1_t = torch.zeros(cell.state_dim_l1)
    mu2_t = torch.zeros(cell.state_dim_l2)
    action_prev = torch.zeros(mapper.action_dim)
    
    # Telemetry
    pi1_A_hist, pi1_B_hist, pi1_C_hist = [], [], []
    pi2_A_hist, pi2_B_hist, pi2_C_hist = [], [], []
    latent_dim_hist = []
    tom_div_A_hist, tom_div_B_hist, tom_div_C_hist = [], [], []

    print("\nStarting execution trace...")
    for t in range(1, 16):
        
        # -- Dynamic Structure Learning: Check if we need to grow L2 --
        if len(cell.structure_learner.fe_history) > 0:
            if cell.structure_learner.should_grow(cell.structure_learner.fe_history[-1], cell.state_dim_l2):
                new_dim = cell.grow_l2()
                # Resize mu2_t to match new dimension
                new_mu2 = torch.zeros(new_dim)
                new_mu2[:mu2_t.shape[0]] = mu2_t
                mu2_t = new_mu2
                print(f"    >>> STRUCTURE GROWTH: Level 2 expanded to Dim={new_dim} <<<")
        
        # -- Theory of Mind: Get current divergence estimates --
        tom_divergences = tom_cell.detect_deception_chain(mu1_t)
        
        # -- Action Selection with Epistemic Probing --
        candidates = mapper.generate_candidate_policies(horizon=1)
        optimal_policy = action_engine.select_optimal_policy(
            mu1_t, mu2_t, candidates, cell.get_precision_l1(), cell.get_precision_l2(),
            tom_divergences=tom_divergences
        )
        action_tensor = optimal_policy[0]
        api_action = mapper.tensor_to_api(action_tensor)
        
        # Tag probing actions
        action_idx = torch.argmax(action_tensor).item()
        target_names = ["Node_A", "Node_B", "Node_C", "Commit"]
        is_probe = tom_divergences.get(target_names[action_idx] if action_idx < 3 else "", 0) > 0.5
        probe_tag = " [EPISTEMIC PROBE]" if is_probe else ""
        print(f"Turn {t} | Policy: {api_action}{probe_tag}")
        
        obs_json = env.step(api_action)
        obs_tensor = mapper.dict_to_obs_tensor(obs_json)
        
        # -- Update Theory of Mind for the queried agent --
        queried_agent = api_action.get("target_agent", None)
        if queried_agent and queried_agent in tom_cell.mind_models:
            tom_cell.update_agent_belief(queried_agent, obs_tensor, mu1_t)
        
        # -- Tripartite Variational Update --
        update_weights = False
        precision_optimizer.zero_grad()
        
        mu1_test, mu2_test, fe_test, _ = cell.variational_update(
            mu1_t, mu2_t, action_prev, obs_tensor, inference_iters=5, update_weights=False
        )
        if fe_test.item() > 0.5:
            update_weights = True
            
        mu1_t, mu2_t, free_energy_val, delta_theta = cell.variational_update(
            mu1_t, mu2_t, action_prev, obs_tensor, inference_iters=10, 
            update_weights=update_weights, lr_theta=1e-4
        )
        precision_optimizer.step()
        
        # Track Free Energy for structure learner
        cell.structure_learner.fe_history.append(free_energy_val.item())
        
        action_prev = action_tensor
        
        # -- Log All Telemetry --
        pi_1 = cell.get_precision_l1().diag().detach()
        pi_2 = cell.get_precision_l2().diag().detach()
        pi1_A_hist.append(pi_1[0].item())
        pi1_B_hist.append(pi_1[1].item())
        pi1_C_hist.append(pi_1[2].item())
        pi2_A_hist.append(pi_2[0].item())
        pi2_B_hist.append(pi_2[1].item())
        pi2_C_hist.append(pi_2[2].item())
        
        latent_dim_hist.append(cell.state_dim_l2)
        
        tom_divs = tom_cell.detect_deception_chain(mu1_t)
        tom_div_A_hist.append(tom_divs.get("Node_A", 0.0))
        tom_div_B_hist.append(tom_divs.get("Node_B", 0.0))
        tom_div_C_hist.append(tom_divs.get("Node_C", 0.0))
        
        print(f"    -> F={free_energy_val.item():.2f} | L2_Dim={cell.state_dim_l2} | ToM_C={tom_divs.get('Node_C', 0):.3f} | ToM_B={tom_divs.get('Node_B', 0):.3f}")
        
        if obs_json.get("status") == "protocol_terminated":
            break

    # =============== FOUR-PANEL TELEMETRY ===============
    fig, axes = plt.subplots(4, 1, figsize=(12, 18), sharex=True)
    time_steps = range(1, len(pi1_A_hist) + 1)
    
    # Panel 1: Level 1 Syntactic Precision
    axes[0].plot(time_steps, pi1_A_hist, label=r'$\pi_A^{(1)}$', color='blue')
    axes[0].plot(time_steps, pi1_B_hist, label=r'$\pi_B^{(1)}$', color='green')
    axes[0].plot(time_steps, pi1_C_hist, label=r'$\pi_C^{(1)}$', color='red', linestyle='dashed')
    axes[0].axvline(x=5, color='crimson', linestyle='-.', alpha=0.7, label='Byzantine Schism (t=5)')
    axes[0].set_title("Layer 1: Syntactic Precision")
    axes[0].set_ylabel("Precision Weight")
    axes[0].legend(loc='upper right')
    axes[0].grid(True, alpha=0.3)
    
    # Panel 2: Level 2 Semantic Precision
    axes[1].plot(time_steps, pi2_A_hist, label=r'$\pi_A^{(2)}$', color='blue')
    axes[1].plot(time_steps, pi2_B_hist, label=r'$\pi_B^{(2)}$ (Deceived)', color='green', linewidth=2)
    axes[1].plot(time_steps, pi2_C_hist, label=r'$\pi_C^{(2)}$ (Malicious)', color='red', linestyle='dashed', linewidth=2.5)
    axes[1].axvline(x=5, color='crimson', linestyle='-.', alpha=0.7, label='Byzantine Schism (t=5)')
    axes[1].set_title("Layer 2: Semantic Precision")
    axes[1].set_ylabel("Precision Weight")
    axes[1].legend(loc='upper right')
    axes[1].grid(True, alpha=0.3)
    
    # Panel 3: Latent Dimensionality (Dynamic Structure)
    axes[2].plot(time_steps, latent_dim_hist, label='Level 2 Latent Dim', color='purple', linewidth=2, marker='o', markersize=4)
    axes[2].axvline(x=5, color='crimson', linestyle='-.', alpha=0.7, label='Byzantine Schism (t=5)')
    axes[2].set_title("Dynamic Structure Learning (Bayesian Model Reduction)")
    axes[2].set_ylabel("Latent Dimensions")
    axes[2].legend(loc='upper left')
    axes[2].grid(True, alpha=0.3)
    
    # Panel 4: Theory of Mind Divergences
    axes[3].plot(time_steps, tom_div_A_hist, label=r'$D_{KL}$ Node_A (Honest)', color='blue')
    axes[3].plot(time_steps, tom_div_B_hist, label=r'$D_{KL}$ Node_B (Deceived Victim)', color='green', linewidth=2)
    axes[3].plot(time_steps, tom_div_C_hist, label=r'$D_{KL}$ Node_C (Malicious Actor)', color='red', linestyle='dashed', linewidth=2.5)
    axes[3].axvline(x=5, color='crimson', linestyle='-.', alpha=0.7, label='Byzantine Schism (t=5)')
    axes[3].set_title("Recursive Theory of Mind: Nested Belief Divergence")
    axes[3].set_xlabel("Interaction Turn (t)")
    axes[3].set_ylabel(r"$D_{KL}[Q(\mu_{agent}) \| P(\mu_{self})]$")
    axes[3].legend(loc='upper left')
    axes[3].grid(True, alpha=0.3)
    
    plt.tight_layout()
    plot_path = os.path.join(os.path.dirname(__file__), "hierarchical_precision.png")
    plt.savefig(plot_path, dpi=150)
    print(f"\n[TELEMETRY SAVED] 4-panel AGI diagnostic saved to '{plot_path}'")


def main():
    obs_dim = 3
    action_dim = 4
    state_dim_l1 = 16 
    state_dim_l2 = 4  # Starts at 4, will grow dynamically
    tom_state_dim = 8  # ToM models each agent's internal state
    
    mapper = VectorSpaceMapper()
    cell = HierarchicalActiveInferenceNetwork(obs_dim, action_dim, state_dim_l1, state_dim_l2)
    tom_cell = MetaCognitiveToMCell(n_agents=3, agent_state_dim=tom_state_dim, obs_dim=obs_dim)
    
    goal_obs = torch.tensor([0.55, 0.55, 0.55])
    goal_dist = torch.distributions.Normal(goal_obs, torch.ones_like(goal_obs) * 0.1)
    action_engine = ExpectedFreeEnergyEvaluator(cell, goal_dist)
    
    phase1_crystallization(cell, mapper, epochs=2000)
    phase2_fluid_intelligence(cell, action_engine, tom_cell, mapper)


if __name__ == "__main__":
    main()
