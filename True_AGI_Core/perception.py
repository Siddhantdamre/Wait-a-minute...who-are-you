"""
HierarchicalActiveInferenceNetwork v4.0:
Integrates Dynamic Structure Learning and Theory of Mind
into the tripartite variational update loop.
"""
import torch
import torch.nn as nn
from structure_learner import DynamicStructureLearner, grow_linear_layer

class HierarchicalActiveInferenceNetwork(nn.Module):
    def __init__(self, obs_dim, action_dim, state_dim_l1=16, state_dim_l2=4, n_agents=3):
        super().__init__()
        self.obs_dim = obs_dim
        self.action_dim = action_dim
        self.state_dim_l1 = state_dim_l1  
        self.state_dim_l2 = state_dim_l2  # NOW MUTABLE via structure learning
        self.n_agents = n_agents
        
        # Level 2: Semantic Dynamics (mutable architecture)
        self.dynamics_model_l2 = nn.Sequential(
            nn.Linear(state_dim_l2, 32),
            nn.ReLU(),
            nn.Linear(32, state_dim_l2)
        )
        self.prior_model_l2 = nn.Sequential(
            nn.Linear(state_dim_l2, 32),
            nn.ReLU(),
            nn.Linear(32, state_dim_l1)
        )
        
        # Level 1: Syntactic Dynamics (frozen architecture)
        self.dynamics_model_l1 = nn.Sequential(
            nn.Linear(state_dim_l1 + action_dim, 32),
            nn.ReLU(),
            nn.Linear(32, state_dim_l1)
        )
        self.sensory_model_l1 = nn.Sequential(
            nn.Linear(state_dim_l1, 32),
            nn.ReLU(),
            nn.Linear(32, obs_dim)
        )
        
        # Dual Dynamic Precision Matrices
        self.log_precision_l1 = nn.Parameter(torch.ones(n_agents) * 5.0) 
        self.log_precision_l2 = nn.Parameter(torch.ones(n_agents) * 5.0) 
        
        # Level 2 variance tracking for Occam's Window pruning
        self.sigma_l2 = nn.Parameter(torch.ones(state_dim_l2) * 1.0)
        
        self.inv_sigma_l1_temporal = torch.eye(state_dim_l1) 

        # Dynamic Structure Learner
        self.structure_learner = DynamicStructureLearner(min_dim=2, max_dim=12, grow_threshold=2)

    def get_precision_l1(self):
        return torch.diag(torch.exp(self.log_precision_l1))
        
    def get_precision_l2(self):
        return torch.diag(torch.exp(self.log_precision_l2))

    def inject_cultural_prior(self, cultural_tensor):
        """
        Anchors the Level 2 semantic manifold to a specific cultural worldview by
        skewing the initial dynamics map based on Hofstede parameters.
        """
        with torch.no_grad():
            # Inject cultural tensor as a bias perturbation into the first hidden layer (shape 32 x dim)
            # This directly couples the neural priors to sociological data.
            # We scale it significantly to induce a measureable 'Epistemic Clash'.
            self.dynamics_model_l2[0].bias.data += cultural_tensor.sum() * 1.5
            # We also slightly perturb the mapping matrix directly.
            if len(cultural_tensor) == self.dynamics_model_l2[0].weight.data.shape[1]:
                self.dynamics_model_l2[0].weight.data += (cultural_tensor.unsqueeze(0) * 0.5)


    def grow_l2(self):
        """Autonomously append a new latent dimension to Level 2."""
        old_dim = self.state_dim_l2
        new_dim = old_dim + 1
        self.state_dim_l2 = new_dim
        
        # Grow dynamics_model_l2 input and output
        self.dynamics_model_l2[0] = grow_linear_layer(self.dynamics_model_l2[0], new_in_dim=new_dim)
        self.dynamics_model_l2[2] = grow_linear_layer(self.dynamics_model_l2[2], new_out_dim=new_dim)
        
        # Grow prior_model_l2 input
        self.prior_model_l2[0] = grow_linear_layer(self.prior_model_l2[0], new_in_dim=new_dim)
        
        # Extend sigma_l2
        new_sigma = torch.ones(new_dim)
        new_sigma[:old_dim] = self.sigma_l2.data
        self.sigma_l2 = nn.Parameter(new_sigma)
        
        # Re-create temporal covariance for L2
        return new_dim

    def variational_update(self, mu1_prev, mu2_prev, action_prev, obs_t, 
                           inference_iters=15, lr_mu=0.01, lr_theta=1e-4, update_weights=False):
        """
        Tripartite Optimization with dynamic structure awareness.
        """
        with torch.no_grad():
            mu2_prior = self.dynamics_model_l2(mu2_prev)
            mu1_temporal_prior = self.dynamics_model_l1(torch.cat([mu1_prev, action_prev], -1))

        mu1_t = mu1_temporal_prior.clone().requires_grad_(True)
        mu2_t = mu2_prior.clone().requires_grad_(True)
        
        Pi_1 = self.get_precision_l1()
        Pi_2 = self.get_precision_l2()
        inv_sigma_l2 = torch.diag(1.0 / (self.sigma_l2 + 1e-6))
        
        param_groups = [{'params': [mu1_t, mu2_t], 'lr': lr_mu}]
        
        theta_params = []
        if update_weights:
            theta_params = list(self.dynamics_model_l2.parameters()) + list(self.prior_model_l2.parameters())
            for p in theta_params:
                p.requires_grad = True
            param_groups.append({'params': theta_params, 'lr': lr_theta})
            
        optimizer = torch.optim.SGD(param_groups)
        initial_weights = sum(p.clone().detach().abs().sum().item() for p in theta_params) if update_weights else 0.0

        for _ in range(inference_iters):
            optimizer.zero_grad()
            
            expected_mu1 = self.prior_model_l2(mu2_t)
            expected_obs_from_l1 = self.sensory_model_l1(mu1_t)
            
            # Level 1 Syntactic Error
            err_obs = obs_t - expected_obs_from_l1
            F_sensory = 0.5 * torch.matmul(torch.matmul(err_obs, Pi_1), err_obs)
            
            # Level 2 Semantic Error
            expected_obs_from_l2 = self.sensory_model_l1(expected_mu1)
            err_semantic = expected_obs_from_l1 - expected_obs_from_l2
            F_semantic = 0.5 * torch.matmul(torch.matmul(err_semantic, Pi_2), err_semantic)
            
            # Temporal Coherence
            err_dyn1 = mu1_t - mu1_temporal_prior
            F_temporal_1 = 0.5 * torch.matmul(torch.matmul(err_dyn1, self.inv_sigma_l1_temporal), err_dyn1)
            
            err_dyn2 = mu2_t - mu2_prior
            F_temporal_2 = 0.5 * torch.matmul(torch.matmul(err_dyn2, inv_sigma_l2), err_dyn2)
            
            total_free_energy = F_sensory + F_semantic + F_temporal_1 + F_temporal_2
            
            total_free_energy.backward(retain_graph=True)
            optimizer.step()
            
        final_weights = sum(p.clone().detach().abs().sum().item() for p in theta_params) if update_weights else 0.0
        delta_theta = abs(final_weights - initial_weights)
            
        return mu1_t.detach(), mu2_t.detach(), total_free_energy.detach(), delta_theta
