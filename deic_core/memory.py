from collections import Counter

class CrossEpisodeMemory:
    """
    Minimal prior-bias layer. Collects statistics across episodes to 
    inform the initialization of future episodes. Does NOT change DEIC core
    inference logic.
    """

    def __init__(self):
        self.group_size_counts = Counter()
        self.multiplier_counts = Counter()
        self.total_episodes = 0

    def observe_episode_outcome(self, metadata, success, chosen_hypothesis):
        """
        Record the properties of a successful episode to guide future priors.
        """
        if not success:
            return
            
        self.total_episodes += 1
        
        S = chosen_hypothesis.get('S', [])
        m = chosen_hypothesis.get('m', 1.0)
        
        self.group_size_counts[len(S)] += 1
        self.multiplier_counts[m] += 1

    def prior_bias(self, hypotheses):
        """
        Produce biased initial probabilities for a list of hypothesis dicts.
        If no history exists, returns uniform probabilities.
        """
        if self.total_episodes == 0:
            return [1.0] * len(hypotheses)
            
        probs = []
        # Support fallback to 1 class size smoothing if counts are uniform
        gs_space_size = len(self.group_size_counts) or 1
        m_space_size = len(self.multiplier_counts) or 1

        for h in hypotheses:
            S_len = len(h.get('S', []))
            m = h.get('m', 1.0)
            
            p_size = (self.group_size_counts.get(S_len, 0) + 1.0) / (self.total_episodes + gs_space_size)
            p_mult = (self.multiplier_counts.get(m, 0) + 1.0) / (self.total_episodes + m_space_size)
            
            probs.append(p_size * p_mult)
            
        return probs

    def summary(self):
        """Return a summary dict for the global workspace."""
        return {
            'total_episodes': self.total_episodes,
            'group_size_counts': dict(self.group_size_counts),
            'multiplier_counts': dict(self.multiplier_counts),
        }

    def reset(self):
        self.group_size_counts.clear()
        self.multiplier_counts.clear()
        self.total_episodes = 0
