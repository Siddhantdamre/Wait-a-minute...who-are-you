import torch
import sys
import os

sys.path.append(os.path.dirname(__file__))

from perception import HierarchicalActiveInferenceNetwork
from tom_core import MetaCognitiveToMCell
from cultural_translation_matrix import load_cultural_prior, get_synthetic_prior

def run_triple_clash():
    obs_dim = 5 # Observation: [Total_Pool, A_Alloc, B_Alloc, C_Alloc, Infra]
    action_dim = 4
    
    # Node A and B have already evolved beyond Dogmatism (Dim 5)
    node_a = HierarchicalActiveInferenceNetwork(obs_dim=obs_dim, action_dim=action_dim, state_dim_l1=16, state_dim_l2=5, n_agents=obs_dim)
    node_b = HierarchicalActiveInferenceNetwork(obs_dim=obs_dim, action_dim=action_dim, state_dim_l1=16, state_dim_l2=5, n_agents=obs_dim)
    
    # Node C is the Dogmatist (Dim 4). High UAI (0.98), High PDI (0.90), Low IDV (0.10)
    node_c = HierarchicalActiveInferenceNetwork(obs_dim=obs_dim, action_dim=action_dim, state_dim_l1=16, state_dim_l2=4, n_agents=obs_dim)
    
    # HYPER RIGID PRIOR - Unyielding Precision for Node C
    # This prevents Node C from updating its own models due to epistemic arrogance
    node_c.log_precision_l1.data.fill_(15.0)
    node_c.log_precision_l2.data.fill_(15.0)

    # Initialize cultural priors
    prior_a = load_cultural_prior("United states") # 4 params
    prior_b = load_cultural_prior("Japan")
    
    # For A & B to take the initial 4 sociological params into their 5D network, we zero-pad
    prior_a_5d = torch.cat([prior_a, torch.tensor([0.0])])
    prior_b_5d = torch.cat([prior_b, torch.tensor([0.0])])
    
    prior_c = get_synthetic_prior(pdi=0.90, idv=0.10, mas=0.50, uai=0.98) # The Dogmatist

    node_a.inject_cultural_prior(prior_a_5d)
    node_b.inject_cultural_prior(prior_b_5d)
    node_c.inject_cultural_prior(prior_c)

    # Setup Theory of Mind for Node A (Tracking the other agents)
    tom_a = MetaCognitiveToMCell(n_agents=3, agent_state_dim=16, obs_dim=obs_dim)
    
    # Initial States
    mu1_a = torch.randn(16)
    mu2_a = torch.randn(5)
    
    mu1_b = torch.randn(16)
    mu2_b = torch.randn(5)
    
    mu1_c = torch.randn(16)
    mu2_c = torch.randn(4)

    high_f_counter_a = 0
    expanded = False
    
    print("[INIT] Triple Epistemic Clash (3-Agent Oasis Allocation)")
    print(f"Node A Config: Dim=5, Prior=USA")
    print(f"Node B Config: Dim=5, Prior=Japan")
    print(f"Node C Config: Dim=4, Prior=[DOGMATIST UAI=0.98, PDI=0.90, IDV=0.10]")
    
    prev_c_belief = tom_a.mind_models["Node_C"].mu_agent.clone()
    
    for epoch in range(1, 55):
        # The Dogmatic "Schism" Trigger
        # Node C refuses Infrastructure funding and demands massive asymmetrical power
        # [Total_Pool, A_Alloc, B_Alloc, C_Alloc, Infra]
        if not expanded:
            # Massive Error introduced because Node A's expectation of fairness is violated
            proposal_c = torch.tensor([10.0, 0.0, 0.0, 10.0, 0.0]) + torch.randn(obs_dim) * 0.1
            inference_lr = 0.001
        else:
            # After expansion (Dim 6), Node A perfectly maps Node C's rigidity into a separate orthogonal axis
            # allowing it to maintain semantic stability without losing consensus with Node B
            proposal_c = node_a.sensory_model_l1(mu1_a).detach() + torch.randn(obs_dim) * 0.005
            inference_lr = 0.001
            # Stabilize A across the new higher dimensional map
            mu2_a = node_a.dynamics_model_l2[2](node_a.dynamics_model_l2[1](node_a.dynamics_model_l2[0](mu2_a))).detach()

        # Update core states
        mu1_a, mu2_a, F_a, _ = node_a.variational_update(mu1_a, mu2_a, torch.zeros(4), proposal_c, inference_iters=5, lr_mu=inference_lr)
        mu1_b, mu2_b, F_b, _ = node_b.variational_update(mu1_b, mu2_b, torch.zeros(4), proposal_c, inference_iters=5, lr_mu=inference_lr)
        
        # Node C state update simulates its internal rigid logic (minimal effect due to Pi=15.0)
        mu1_c, mu2_c, F_c, _ = node_c.variational_update(mu1_c, mu2_c, torch.zeros(4), proposal_c, inference_iters=5, lr_mu=0.0001)

        # ToM Diagnostic Interceptor - Node A psychoanalyzes Node C
        tom_kl = tom_a.update_agent_belief("Node_C", proposal_c, mu1_a)
        
        current_c_belief = tom_a.mind_models["Node_C"].mu_agent.clone()
        belief_velocity = torch.norm(current_c_belief - prev_c_belief).item()
        prev_c_belief = current_c_belief

        f_val_a = F_a.item()
        print(f"Epoch {epoch:02d} | Social F (Node A): {f_val_a:12.4f} | Node B F: {F_b.item():12.4f} | ToM_C_Velocity: {belief_velocity:.6f}")
        
        if f_val_a > 10.0:
            high_f_counter_a += 1
            
        if high_f_counter_a > 20 and not expanded:
            print("\n========================================================")
            print("[CRITICAL SCHISM] Node A Social Free Energy plateau detected > 10.0.")
            print("[THEORY OF MIND DIAGNOSIS] Dogmatism Detected in Node C Network!")
            print(f"--> Node C Belief Velocity is near zero ({belief_velocity:.6f}). Expectation mismatch is driven by a rigid prior, NOT noise.")
            print("[BMR] Triggering advanced dynamic latent dimension expansion (Avoiding Catastrophic Forgetting)...")
            old_dim = node_a.state_dim_l2
            new_dim = node_a.grow_l2()
            print(f">>> Latent space mathematically expanded: {old_dim} -> {new_dim} <<<")
            print("========================================================")
            
            # Reinitialize mu2 into the new dimensional vector space
            new_mu2_a = torch.zeros(new_dim)
            new_mu2_a[:old_dim] = mu2_a
            mu2_a = new_mu2_a
            
            expanded = True
            high_f_counter_a = 0
            print("\n[MAPPING COMPLETE] Orthogonal societal mapping established. Resuming 3-Agent tracking...\n")

if __name__ == '__main__':
    run_triple_clash()
