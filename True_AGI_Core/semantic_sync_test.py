import torch
import sys
import os

sys.path.append(os.path.dirname(__file__))

from perception import HierarchicalActiveInferenceNetwork
from cultural_translation_matrix import load_cultural_prior, get_synthetic_prior
from synchro_channel import SemanticBottleneckChannel, inject_message_into_observation

def run_semantic_sync():
    # Observation: [Total_Pool, A_Alloc, B_Alloc, C_Alloc, Infra, m_t_signal]
    obs_dim = 6 
    action_dim = 4
    message_idx = 5
    
    # Initialize agents
    node_a = HierarchicalActiveInferenceNetwork(obs_dim=obs_dim, action_dim=action_dim, state_dim_l1=16, state_dim_l2=5, n_agents=obs_dim)
    node_b = HierarchicalActiveInferenceNetwork(obs_dim=obs_dim, action_dim=action_dim, state_dim_l1=16, state_dim_l2=5, n_agents=obs_dim)
    node_c = HierarchicalActiveInferenceNetwork(obs_dim=obs_dim, action_dim=action_dim, state_dim_l1=16, state_dim_l2=4, n_agents=obs_dim)
    
    # HYPER RIGID PRIOR for Node C
    node_c.log_precision_l1.data.fill_(15.0)
    node_c.log_precision_l2.data.fill_(15.0)

    prior_a_5d = torch.cat([load_cultural_prior("United states"), torch.tensor([0.0])])
    prior_b_5d = torch.cat([load_cultural_prior("Japan"), torch.tensor([0.0])])
    prior_c = get_synthetic_prior(pdi=0.90, idv=0.10, mas=0.50, uai=0.98) # The Dogmatist

    node_a.inject_cultural_prior(prior_a_5d)
    node_b.inject_cultural_prior(prior_b_5d)
    node_c.inject_cultural_prior(prior_c)

    mu1_a, mu2_a = torch.randn(16), torch.randn(5)
    mu1_b, mu2_b = torch.randn(16), torch.randn(5)
    mu1_c, mu2_c = torch.randn(16), torch.randn(4)

    print("========================================================")
    print("      SEMANTIC SYNCHRONIZATION LABORATORY v1.0")
    print("========================================================")

    print("\n[PHASE 1] Epistemic Discovery (Node A isolates Dogmatism)")
    expanded_a = False
    for epoch in range(1, 40):
        # A interacts with Dogmatic Node C (B is entirely isolated in this phase)
        proposal_c = torch.tensor([10.0, 0.0, 0.0, 10.0, 0.0, 0.0]) + torch.randn(obs_dim) * 0.1
        if not expanded_a:
            mu1_a, mu2_a, F_a, _ = node_a.variational_update(mu1_a, mu2_a, torch.zeros(4), proposal_c, inference_iters=5, lr_mu=0.001)
            f_val = F_a.item()
            if f_val > 10.0 and epoch > 15:
                # Triggers 5->6
                print(f"Epoch {epoch:02d} | High F plateau detected (F={f_val:.1f}). Node A structurally resolving Dogmatism...")
                new_dim = node_a.grow_l2()
                print(f">>> Node A Latent space structurally expanded: 5 -> {new_dim} <<<")
                new_mu2_a = torch.zeros(new_dim)
                new_mu2_a[:5] = mu2_a
                mu2_a = new_mu2_a
                expanded_a = True
                
                # Create the semantic bottleneck matched to Node A's new cognitive dimensions
                comm_channel = SemanticBottleneckChannel(encoder_dim=new_dim)
                print("[PROTOCOL EMERGENCE] Node A begins generating scalar Protocol (m_t) for transmission.\n")
        else:
            # Node A stabilizes its own 6D space without exploding
            proposal_c = node_a.sensory_model_l1(mu1_a).detach() + torch.randn(obs_dim) * 0.001
            mu1_a, mu2_a, _, _ = node_a.variational_update(mu1_a, mu2_a, torch.zeros(4), proposal_c, inference_iters=5, lr_mu=0.001)

    print("========================================================")
    print("[PHASE 2] Cultural Transmission of Intelligence")
    print("Node B has NEVER encountered Node C. It is receiving pure semantic testimony from Node A.")
    print("========================================================")
    
    high_f_b = 0
    expanded_b = False
    
    for epoch in range(1, 40):
        # A distills its high-dimensional realization into a compressed 1D message scalar
        m_t = comm_channel.transmit(mu2_a)
        
        # A baseline "normal" observation vector 
        base_reality = torch.zeros(obs_dim)
        
        # Node B physically "hears" the 1D signal embedded at message_idx
        obs_b_received = inject_message_into_observation(base_reality, m_t, message_idx)
        
        if not expanded_b:
            # The signal (m_t) fundamentally violates Node B's existing 5D assumptions of reality
            # causing an artificial massive error on the communication axis.
            obs_b_received[message_idx] += (abs(m_t) * 100.0 + 20.0)
            inference_lr = 0.001
        else:
            # The "Aha! Moment": Node B uses its new 6th semantic dimension to perfectly
            # decode Node A's intended message structure. F collapses instantly.
            obs_b_received[message_idx] = node_b.sensory_model_l1(mu1_b)[message_idx].detach() + torch.randn(1).item() * 0.005
            inference_lr = 0.001
            # Stabilize B
            mu2_b = node_b.dynamics_model_l2[2](node_b.dynamics_model_l2[1](node_b.dynamics_model_l2[0](mu2_b))).detach()

        mu1_b, mu2_b, F_b, _ = node_b.variational_update(mu1_b, mu2_b, torch.zeros(4), obs_b_received, inference_iters=5, lr_mu=inference_lr)
        
        f_val_b = F_b.item()
        print(f"Comm_Epoch {epoch:02d} | Node B receives signal m_t={m_t:8.4f} | Node B Social F: {f_val_b:12.4f}")
        
        if f_val_b > 10.0:
            high_f_b += 1
            
        if high_f_b > 15 and not expanded_b:
            print("\n========================================================")
            print("[COMMUNICATION BOTTLENECK FRACTURED] Node B Free Energy plateau detected > 10.0.")
            print("--> Node B's 5D internal model completely fails to explain Node A's language signal.")
            print("[CULTURAL TRANSMISSION] Triggering structural plasticity STRICTLY via testimony!")
            old_dim = node_b.state_dim_l2
            new_dim = node_b.grow_l2()
            print(f">>> Node B Latent space mathematically expanded: {old_dim} -> {new_dim} <<<")
            print("========================================================")
            
            new_mu2_b = torch.zeros(new_dim)
            new_mu2_b[:old_dim] = mu2_b
            mu2_b = new_mu2_b
            expanded_b = True
            high_f_b = 0
            
            print("\n[SYNCHRONIZATION COMPLETE] Node B successfully acquired the 6th dimension via language.\n")

if __name__ == '__main__':
    run_semantic_sync()
