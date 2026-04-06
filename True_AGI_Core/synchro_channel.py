import torch
import torch.nn as nn

class SemanticBottleneckChannel(nn.Module):
    """
    A communication channel that allows an AGI node to project its high-dimensional
    structural ontology (Level 2 semantic state) into a 1D scalar signal, and 
    decodes that signal on the receiving end.
    """
    def __init__(self, encoder_dim):
        super().__init__()
        # MessageEncoder (compress high-D state to 1D scalar)
        # Allows Node A to literally 'distill' its 6D understanding into a single float
        self.encoder = nn.Linear(encoder_dim, 1)
        
    def transmit(self, speaker_mu2):
        """
        Compresses the speaker's Level 2 state into a single semantic 'word' (signal m_t).
        """
        with torch.no_grad():
            m_t = self.encoder(speaker_mu2)
        return m_t.item()

def inject_message_into_observation(base_obs, m_t, message_index=5):
    """
    Injects the scalar message m_t into the listener's sensory observation vector.
    Serves as the artificial sensory pathway for 'language' emergence.
    """
    new_obs = base_obs.clone()
    # If the observation vector doesn't have the index, we ensure we append it
    if len(new_obs) <= message_index:
        padding = torch.zeros(message_index - len(new_obs) + 1)
        new_obs = torch.cat([new_obs, padding])
        
    new_obs[message_index] = m_t
    return new_obs
