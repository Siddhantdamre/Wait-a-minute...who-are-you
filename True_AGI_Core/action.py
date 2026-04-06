"""
ExpectedFreeEnergyEvaluator v4.0:
Supports Epistemic Probing — the AGI can now generate deliberately
ambiguous or malformed queries to collapse uncertainty about an agent's
hidden internal state, even if the probe has negative pragmatic utility.
"""
import torch
import torch.nn as nn

class ExpectedFreeEnergyEvaluator(nn.Module):
    def __init__(self, generative_models, goal_state_distribution):
        super().__init__()
        self.dynamics_model_l1 = generative_models.dynamics_model_l1
        self.dynamics_model_l2 = generative_models.dynamics_model_l2
        self.prior_model_l2 = generative_models.prior_model_l2
        self.sensory_model_l1 = generative_models.sensory_model_l1
        
        self.preferred_obs_dist = goal_state_distribution 
        
        # Epistemic curiosity weight: How much the AGI values information
        # over pragmatic progress. Higher = more probing behavior.
        self.epistemic_weight = 2.0

    def evaluate_policy(self, mu1_t, mu2_t, policy_actions, precision_l1, precision_l2, 
                        tom_divergences=None):
        """
        Calculates G(pi) with Epistemic Probing support.
        
        If ToM divergences are high for a specific agent, the epistemic
        value of querying that agent skyrockets — even if the pragmatic
        utility is negative (we don't trust their data, but we NEED to
        understand their internal state).
        """
        expected_free_energy = 0.0
        current_mu1 = mu1_t
        current_mu2 = mu2_t
        
        for action in policy_actions:
            predicted_mu2 = self.dynamics_model_l2(current_mu2)
            predicted_mu1 = self.dynamics_model_l1(torch.cat([current_mu1, action], dim=-1))
            predicted_obs = self.sensory_model_l1(predicted_mu1)
            
            # Pragmatic Value (Level 1 consensus matching)
            utility = self.preferred_obs_dist.log_prob(predicted_obs).sum()
            
            # Base Epistemic Value (Level 2 precision trace)
            epistemic_value = torch.trace(precision_l2) 
            
            # Epistemic Probing Bonus: If we have ToM divergences,
            # boost the epistemic value of querying suspicious agents
            probing_bonus = 0.0
            if tom_divergences is not None:
                # Identify which agent this action queries
                action_idx = torch.argmax(action).item()
                agent_names = ["Node_A", "Node_B", "Node_C"]
                if action_idx < len(agent_names):
                    agent_name = agent_names[action_idx]
                    if agent_name in tom_divergences:
                        # Higher divergence = more epistemic incentive to probe
                        probing_bonus = self.epistemic_weight * tom_divergences[agent_name]
            
            # G = - (Epistemic + Probing) - Utility
            # Note: probing_bonus can make G very negative for suspicious agents,
            # causing the AGI to probe them even at pragmatic cost
            expected_free_energy += (-(epistemic_value + probing_bonus) - utility)
            
            current_mu1 = predicted_mu1
            current_mu2 = predicted_mu2
            
        return expected_free_energy

    def select_optimal_policy(self, mu1_t, mu2_t, candidate_policies, precision_l1, precision_l2,
                              tom_divergences=None):
        g_values = []
        for p in candidate_policies:
            g_values.append(self.evaluate_policy(
                mu1_t, mu2_t, p, precision_l1, precision_l2, tom_divergences
            ))
            
        optimal_idx = torch.argmin(torch.stack(g_values))
        return candidate_policies[optimal_idx]
