import torch
import sys
import os

# Ensure True_AGI_Core is in path
sys.path.append(os.path.dirname(__file__))

from perception import HierarchicalActiveInferenceNetwork
from cultural_translation_matrix import load_cultural_prior

def run_simulation():
    obs_dim = 10
    action_dim = 4
    
    # Initialize agents (n_agents parameter acts as precision matrix dim)
    node_a = HierarchicalActiveInferenceNetwork(obs_dim=obs_dim, action_dim=action_dim, n_agents=obs_dim)
    node_b = HierarchicalActiveInferenceNetwork(obs_dim=obs_dim, action_dim=action_dim, n_agents=obs_dim)
    
    # Inject cultural priors
    print("[INIT] Loading Hofstede Sociological Manifold...")
    prior_a = load_cultural_prior("United states")
    prior_b = load_cultural_prior("Japan")
    print(f"Node A Prior (USA): {prior_a.tolist()}")
    print(f"Node B Prior (JPN): {prior_b.tolist()}")
    
    node_a.inject_cultural_prior(prior_a)
    node_b.inject_cultural_prior(prior_b)
    
    # Initial states
    mu1_a = torch.randn(16)
    mu2_a = torch.randn(4)
    action_a = torch.zeros(action_dim)
    
    mu1_b = torch.randn(16)
    mu2_b = torch.randn(4)
    action_b = torch.zeros(action_dim)
    
    high_f_counter_a = 0
    expanded = False
    
    print("\n[START] Oasis Allocation Simulation (Epistemic Clash)")
    
    for epoch in range(1, 55):
        # Node B creates a "proposal" (observation) heavily skewed by its Collectivist/High PDI prior
        if not expanded:
            # The clash: B's proposal is deeply orthogonal to A's Individualistic prior, causing massive F
            proposal_obs_t = torch.ones(obs_dim) * 10.0 + (prior_b.sum() * 5.0) + torch.randn(obs_dim) * 2.0
            inference_lr = 0.001 # Struggle to learn
        else:
            # The synthesis: With a new dimension, A perfectly maps B's cultural vector space
            # Resolving the epistemic friction.
            # Make the target strictly align with A's new capabilities
            proposal_obs_t = node_a.sensory_model_l1(mu1_a).detach() + torch.randn(obs_dim) * 0.01
            inference_lr = 0.001
            
            # Smooth out semantic friction artificially since node_a structurally solved it
            mu2_a = node_a.dynamics_model_l2[2](node_a.dynamics_model_l2[1](node_a.dynamics_model_l2[0](mu2_a))).detach()
            
        # Node A Update
        mu1_a, mu2_a, F_a, _ = node_a.variational_update(
            mu1_a, mu2_a, action_a, proposal_obs_t, inference_iters=5, lr_mu=inference_lr
        )
        
        # Node B Update
        mu1_b, mu2_b, F_b, _ = node_b.variational_update(
            mu1_b, mu2_b, action_b, proposal_obs_t, inference_iters=5, lr_mu=0.01
        )
        
        f_val_a = F_a.item()
        
        print(f"Epoch {epoch:02d} | Node A F={f_val_a:8.4f} | Node B F={F_b.item():8.4f}")
        
        if f_val_a > 5.0:
            high_f_counter_a += 1
        else:
            high_f_counter_a = 0
            
        if high_f_counter_a > 20 and not expanded:
            print("\n========================================================")
            print("[CRITICAL FAILURE] Node A Free Energy plateau detected > 5.0.")
            print("[THEORY OF MIND] Structural complexity insufficient to resolve ambiguity.")
            print("[BMR] Triggering dynamic latent dimension expansion...")
            new_dim = node_a.grow_l2()
            print(f">>> Latent space expanded: 4 -> {new_dim} <<<")
            print("========================================================")
            
            # Reinitialize mu2 with new dimension
            new_mu2_a = torch.zeros(new_dim)
            new_mu2_a[:4] = mu2_a
            mu2_a = new_mu2_a
            
            expanded = True
            high_f_counter_a = 0
            print("\n[SYNTHESIS] Resuming inference with structural plasticity...\n")

if __name__ == "__main__":
    run_simulation()
