"""
DynamicStructureLearner: Bayesian Model Reduction for Latent Space Resizing.

The AGI autonomously grows or prunes its Level 2 latent dimensions
based on Marginal Likelihood (Model Evidence). No hardcoded architecture.
"""
import torch
import torch.nn as nn

class DynamicStructureLearner(nn.Module):
    """
    Monitors the Variational Free Energy trajectory and the variance
    of each latent dimension. Decides when to GROW (add dimensions) 
    or PRUNE (remove dimensions via Occam's Window).
    """
    def __init__(self, min_dim=2, max_dim=12, grow_threshold=3, prune_variance_threshold=1e-4):
        super().__init__()
        self.min_dim = min_dim
        self.max_dim = max_dim
        self.grow_threshold = grow_threshold  # Consecutive plateaus before growing
        self.prune_variance_threshold = prune_variance_threshold
        
        # Track Free Energy history to detect plateaus
        self.fe_history = []
        self.plateau_counter = 0
        self.structure_log = []  # Log of grow/prune events
        
    def should_grow(self, current_fe: float, current_dim: int) -> bool:
        """
        If Free Energy plateaus for grow_threshold consecutive steps
        despite state and parameter updates, the latent space is 
        insufficient to represent the world. We must grow.
        """
        self.fe_history.append(current_fe)
        
        if current_dim >= self.max_dim:
            return False
            
        if len(self.fe_history) >= 2:
            recent_delta = abs(self.fe_history[-1] - self.fe_history[-2])
            if recent_delta < 0.05 * abs(self.fe_history[-1] + 1e-9):
                self.plateau_counter += 1
            else:
                self.plateau_counter = 0
                
        if self.plateau_counter >= self.grow_threshold:
            self.plateau_counter = 0
            self.structure_log.append(("GROW", current_dim + 1, current_fe))
            return True
        return False
    
    def dims_to_prune(self, sigma_l2: torch.Tensor, current_dim: int) -> list:
        """
        Occam's Window: If the variance of a latent dimension drops
        to near zero, it carries no information. Prune it.
        """
        if current_dim <= self.min_dim:
            return []
            
        prune_indices = []
        for i in range(sigma_l2.shape[0]):
            if sigma_l2[i].item() < self.prune_variance_threshold:
                prune_indices.append(i)
                
        # Never prune below minimum
        max_prunable = current_dim - self.min_dim
        prune_indices = prune_indices[:max_prunable]
        
        if prune_indices:
            self.structure_log.append(("PRUNE", current_dim - len(prune_indices), self.fe_history[-1] if self.fe_history else 0.0))
        
        return prune_indices


def grow_linear_layer(layer: nn.Linear, new_in_dim: int = None, new_out_dim: int = None):
    """
    Grow a linear layer by 1 dimension, preserving existing weights.
    """
    old_weight = layer.weight.data
    old_bias = layer.bias.data
    old_in = layer.in_features
    old_out = layer.out_features
    
    target_in = new_in_dim if new_in_dim is not None else old_in
    target_out = new_out_dim if new_out_dim is not None else old_out
    
    new_layer = nn.Linear(target_in, target_out)
    
    # Copy existing weights
    with torch.no_grad():
        min_in = min(old_in, target_in)
        min_out = min(old_out, target_out)
        new_layer.weight.data[:min_out, :min_in] = old_weight[:min_out, :min_in]
        new_layer.bias.data[:min_out] = old_bias[:min_out]
        
        # Initialize new dimensions with small random values
        if target_in > old_in:
            nn.init.xavier_uniform_(new_layer.weight.data[:, old_in:].unsqueeze(0))
        if target_out > old_out:
            nn.init.xavier_uniform_(new_layer.weight.data[old_out:, :].unsqueeze(0))
            new_layer.bias.data[old_out:] = 0.01
            
    return new_layer


def prune_linear_layer(layer: nn.Linear, keep_indices_in: list = None, keep_indices_out: list = None):
    """
    Prune a linear layer by removing specific dimensions.
    """
    old_weight = layer.weight.data
    old_bias = layer.bias.data
    
    if keep_indices_out is not None:
        old_weight = old_weight[keep_indices_out, :]
        old_bias = old_bias[keep_indices_out]
    if keep_indices_in is not None:
        old_weight = old_weight[:, keep_indices_in]
    
    new_layer = nn.Linear(old_weight.shape[1], old_weight.shape[0])
    with torch.no_grad():
        new_layer.weight.data = old_weight.clone()
        new_layer.bias.data = old_bias.clone()
    return new_layer
