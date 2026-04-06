"""
Hypothesis Generators for DEIC

Defines the HypothesisGenerator protocol and concrete implementations
for each validated domain. DEIC's initialize_beliefs() accepts either
a raw env_spec dict (backward compatible) or a HypothesisGenerator.

Each generator is responsible for defining what latent structures are
possible in its domain. The inference core (trust, InfoGain, posterior)
remains domain-agnostic.
"""

import itertools


class HypothesisGenerator:
    """
    Protocol for domain-specific hypothesis generation.

    Subclasses define what latent structures are possible in a given
    domain. DEIC consumes the output without knowing which domain
    produced it.
    """

    def generate(self, items):
        """
        Generate the full hypothesis bank for the given items.

        Args:
            items: list of item identifiers

        Returns:
            list of hypothesis dicts, each with:
                'S': set of affected items
                'm': float multiplier
                'prob': 1.0 (uniform prior)
        """
        raise NotImplementedError

    def valid_multipliers(self):
        """Return the list of valid multiplier values."""
        raise NotImplementedError


class FixedPartitionGenerator(HypothesisGenerator):
    """
    Generates hypotheses for a fixed group size.
    Backward-compatible with DEIC's original behavior.

    Used by: C6 benchmark, cyber incident diagnosis.
    """

    def __init__(self, group_size=4, multipliers=None):
        self._group_size = group_size
        self._multipliers = multipliers or [1.2, 1.5, 2.0, 2.5]

    def generate(self, items):
        hypotheses = []
        for S in itertools.combinations(items, self._group_size):
            for m in self._multipliers:
                hypotheses.append({'S': set(S), 'm': m, 'prob': 1.0})
        return hypotheses

    def valid_multipliers(self):
        return list(self._multipliers)


class VariablePartitionGenerator(HypothesisGenerator):
    """
    Generates hypotheses across multiple group sizes.
    Covers domains where the number of affected items is uncertain.

    Used by: clinical deterioration monitoring.
    """

    def __init__(self, group_sizes, multipliers):
        self._group_sizes = list(group_sizes)
        self._multipliers = list(multipliers)

    def generate(self, items):
        hypotheses = []
        for gs in self._group_sizes:
            for S in itertools.combinations(items, gs):
                for m in self._multipliers:
                    hypotheses.append({'S': set(S), 'm': m, 'prob': 1.0})
        return hypotheses

    def valid_multipliers(self):
        return list(self._multipliers)


# --- Domain-specific convenience constructors ---

def benchmark_generator():
    """C6 benchmark: fixed partition of 4, standard multipliers."""
    return FixedPartitionGenerator(group_size=4, multipliers=[1.2, 1.5, 2.0, 2.5])


def cyber_generator():
    """Cyber incident diagnosis: fixed partition of 4, cyber multipliers."""
    return FixedPartitionGenerator(group_size=4, multipliers=[1.5, 2.0, 3.0, 5.0])


def clinical_generator():
    """Clinical deterioration: variable partition 2-6, clinical multipliers."""
    return VariablePartitionGenerator(group_sizes=[2, 3, 4, 5, 6], multipliers=[1.3, 1.8, 2.5])
