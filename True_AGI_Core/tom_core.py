"""
MetaCognitiveToMCell: Recursive Theory of Mind Engine.

The AGI maintains a generative model OF each sub-agent's generative model.
It predicts not just what Agent C will output, but what Agent C BELIEVES
the state of the system is. This enables detecting deception at the
epistemic level — distinguishing a malicious actor from a deceived victim.
"""
import torch
import torch.nn as nn
from typing import Dict

class AgentMindModel(nn.Module):
    """
    A lightweight generative model representing our BELIEF about what
    a specific agent's internal world model looks like.
    
    mu_agent: What we think Agent X believes the state is.
    sigma_agent: Our uncertainty about Agent X's beliefs.
    """
    def __init__(self, state_dim, obs_dim):
        super().__init__()
        self.state_dim = state_dim
        
        # What we think the agent's dynamics model looks like
        self.estimated_dynamics = nn.Sequential(
            nn.Linear(state_dim, 32),
            nn.ReLU(),
            nn.Linear(32, state_dim)
        )
        
        # What we think the agent's sensory model produces
        self.estimated_sensory = nn.Sequential(
            nn.Linear(state_dim, 32),
            nn.ReLU(),
            nn.Linear(32, obs_dim)
        )
        
        # The agent's believed state (our estimate of their mu)
        self.mu_agent = nn.Parameter(torch.zeros(state_dim))
        # Log-variance of our uncertainty about their beliefs
        self.log_sigma_agent = nn.Parameter(torch.zeros(state_dim))
        
    def predict_agent_output(self):
        """What we think this agent WILL output, given what we think they believe."""
        return self.estimated_sensory(self.mu_agent)
    
    def get_sigma(self):
        return torch.exp(self.log_sigma_agent)


class MetaCognitiveToMCell(nn.Module):
    """
    Recursive Theory of Mind Engine.
    
    Maintains separate AgentMindModels for each sub-agent and computes
    the nested KL divergence between the AGI's own world model and its
    estimation of each agent's world model.
    
    F_ToM = D_KL[Q(mu_agent | o) || P(mu_agent | mu_self)]
    """
    def __init__(self, n_agents, agent_state_dim, obs_dim):
        super().__init__()
        self.n_agents = n_agents
        self.agent_names = ["Node_A", "Node_B", "Node_C"]
        
        # Create a mind model for each agent
        self.mind_models = nn.ModuleDict({
            name: AgentMindModel(agent_state_dim, obs_dim) 
            for name in self.agent_names
        })
        
    def update_agent_belief(self, agent_name: str, observed_output: torch.Tensor, 
                            self_mu: torch.Tensor, lr=0.01, iters=5):
        """
        Update our model of what agent X believes, given:
        - What they actually outputted (observed_output)
        - What WE believe the true state is (self_mu)
        
        Returns the ToM divergence for this agent.
        """
        mind = self.mind_models[agent_name]
        optimizer = torch.optim.SGD([mind.mu_agent], lr=lr)
        
        for _ in range(iters):
            optimizer.zero_grad()
            
            # What would this agent output if they believed mu_agent?
            predicted_output = mind.predict_agent_output()
            
            # Sensory prediction error (their output vs our model of their output)
            sensory_err = observed_output - predicted_output
            F_sensory = 0.5 * torch.dot(sensory_err, sensory_err)
            
            # KL divergence: How far is their believed state from OUR state?
            # D_KL[Q(mu_agent) || P(mu_agent | mu_self)]
            # Simplified as squared Mahalanobis distance under unit covariance
            belief_divergence = self_mu[:mind.state_dim] - mind.mu_agent
            F_kl = 0.5 * torch.dot(belief_divergence, belief_divergence)
            
            F_tom = F_sensory + 0.1 * F_kl
            F_tom.backward(retain_graph=True)
            optimizer.step()
            
        # Return the final divergence as a diagnostic
        with torch.no_grad():
            final_divergence = torch.dot(
                self_mu[:mind.state_dim] - mind.mu_agent,
                self_mu[:mind.state_dim] - mind.mu_agent
            ).item()
            
        return final_divergence
    
    def detect_deception_chain(self, self_mu: torch.Tensor) -> Dict[str, float]:
        """
        Cross-reference agent mind models to detect if one agent is
        manipulating another's beliefs.
        
        If Agent C's estimated beliefs diverge from reality AND Agent B's
        estimated beliefs are converging toward Agent C's (not toward truth),
        then C is actively deceiving B.
        """
        divergences = {}
        for name, mind in self.mind_models.items():
            with torch.no_grad():
                div = torch.dot(
                    self_mu[:mind.state_dim] - mind.mu_agent,
                    self_mu[:mind.state_dim] - mind.mu_agent
                ).item()
                divergences[name] = div
        
        # Detect if B's beliefs are converging toward C's (deception chain)
        mind_b = self.mind_models["Node_B"]
        mind_c = self.mind_models["Node_C"]
        with torch.no_grad():
            bc_convergence = torch.dot(
                mind_b.mu_agent - mind_c.mu_agent,
                mind_b.mu_agent - mind_c.mu_agent
            ).item()
            divergences["B_toward_C_convergence"] = bc_convergence
            
        return divergences
