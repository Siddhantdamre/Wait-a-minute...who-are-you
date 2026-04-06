"""
DEIC — Discrete Executive Inference Core

Domain-agnostic hidden-state belief revision engine.
Infers latent structure from sparse observations, tracks source
reliability, and selects queries by expected information gain
under a fixed budget.

No benchmark-specific code. No environment-specific imports.
"""

import itertools
import math
import random


class DEIC:
    """
    Maintains a discrete hypothesis bank over hidden group structure
    and provides adaptive trust discovery plus active query selection.

    Typical usage loop:
        engine = DEIC()
        engine.initialize_beliefs(env_spec)
        while budget_remaining:
            source, item = engine.select_query(budget_state)
            value = <query the environment>
            engine.update_observation(source, item, value, t)
        answer = engine.propose_state()
    """

    def __init__(self, adaptive_trust=True):
        self.adaptive_trust = adaptive_trust
        self._items = []
        self._sources = []
        self._initial_values = {}
        self._group_size = 4
        self._valid_multipliers = []
        self._hypotheses = []
        self._queried_values = {}       # item -> observed value
        self._trusted_source = None
        self._source_observations = {}  # source -> list of (item, value)

    # ------------------------------------------------------------------
    # API: initialize_beliefs
    # ------------------------------------------------------------------
    def initialize_beliefs(self, env_spec):
        """
        Prepare the hypothesis bank for a new episode.

        Input:
            env_spec: dict with keys:
                'items'             — list of item identifiers
                'sources'           — list of source/agent identifiers
                'group_size'        — int, items per latent group
                'valid_multipliers' — list of float shift factors
                'initial_values'    — dict mapping item -> baseline value

        Output: None
        State:  Populates internal hypothesis matrix. Resets all
                episode-specific tracking.
        """
        self._items = list(env_spec['items'])
        self._sources = list(env_spec['sources'])
        self._group_size = env_spec.get('group_size', 4)
        self._valid_multipliers = list(env_spec.get('valid_multipliers', [1.2, 1.5, 2.0, 2.5]))
        self._initial_values = dict(env_spec['initial_values'])

        self._queried_values = {}
        self._trusted_source = None
        self._source_observations = {s: [] for s in self._sources}

        # Build hypothesis bank: each hypothesis is (shifted_set, multiplier)
        all_combos = list(itertools.combinations(self._items, self._group_size))
        self._hypotheses = []
        for S in all_combos:
            for m in self._valid_multipliers:
                self._hypotheses.append({
                    'S': set(S),
                    'm': m,
                    'prob': 1.0
                })
        self._normalize()

    # ------------------------------------------------------------------
    # API: update_observation
    # ------------------------------------------------------------------
    def update_observation(self, source, item, value, t):
        """
        Incorporate one observation into the belief state.

        Input:
            source — identifier of the queried source
            item   — identifier of the queried item
            value  — the returned observation value
            t      — current time step (for logging; not used in core logic)

        Output: None
        State:  If adaptive trust is enabled: if the value differs from
                the baseline, this source is immediately locked as trusted
                and the observation is recorded as structural evidence.
                Otherwise the value is accumulated for majority resolution.
                After trust is established, observations from the trusted
                source are used to eliminate inconsistent hypotheses.
        """
        self._source_observations[source].append((item, value))

        # Phase 1: Trust discovery (no trusted source yet)
        if self._trusted_source is None:
            if self.adaptive_trust:
                if value != self._initial_values.get(item):
                    # A shifted value proves this source sees post-shift state
                    self._trusted_source = source
                    self._queried_values[item] = value
                    # Also absorb any previously observed consensus values
                    # from items where all sources returned baseline
                    self._absorb_consensus_observations()
                    self._update_posterior()
                    return
                else:
                    # Unshifted — ambiguous. But if all sources have now
                    # reported on this item and agree, record consensus.
                    item_obs = [(s, v) for s, obs_list in
                                self._source_observations.items()
                                for it, v in obs_list if it == item]
                    if len(item_obs) >= len(self._sources):
                        vals = [v for _, v in item_obs]
                        majority_val = max(set(vals), key=vals.count)
                        self._queried_values[item] = majority_val
            # Non-adaptive or ambiguous: store for later majority resolution
            return

        # Phase 2: Trusted source established — direct structural update
        if source == self._trusted_source:
            self._queried_values[item] = value
            self._update_posterior()

    # ------------------------------------------------------------------
    # API: update_trust
    # ------------------------------------------------------------------
    def update_trust(self):
        """
        Recompute trust scores based on accumulated observations.

        Input:  None
        Output: dict mapping each source to a trust score (0.0–1.0)
        State:  If no trusted source has been identified yet and
                adaptive trust is disabled, attempts majority-vote
                resolution across sources that reported on the same item.
        """
        trust = {s: 0.5 for s in self._sources}

        if self._trusted_source is not None:
            for s in self._sources:
                trust[s] = 1.0 if s == self._trusted_source else 0.2
            return trust

        # Attempt majority resolution for non-adaptive mode
        if not self.adaptive_trust:
            item_reports = {}
            for s, obs_list in self._source_observations.items():
                for item, val in obs_list:
                    if item not in item_reports:
                        item_reports[item] = []
                    item_reports[item].append((s, val))

            for item, reports in item_reports.items():
                if len(reports) >= len(self._sources):
                    vals = [v for _, v in reports]
                    majority_val = max(set(vals), key=vals.count)
                    self._queried_values[item] = majority_val
                    for s, v in reports:
                        if v == majority_val and self._trusted_source is None:
                            self._trusted_source = s
                    if self._trusted_source:
                        self._update_posterior()
                        break

        if self._trusted_source:
            trust[self._trusted_source] = 1.0
        return trust

    # ------------------------------------------------------------------
    # API: score_hypotheses
    # ------------------------------------------------------------------
    def score_hypotheses(self):
        """
        Inspect the current belief state.

        Input:  None
        Output: list of (hypothesis_descriptor, probability) for active
                hypotheses only. Each descriptor is a dict with keys
                'shifted_items' (frozenset) and 'multiplier' (float).
        State:  None (read-only)
        """
        result = []
        for h in self._hypotheses:
            if h['prob'] > 0:
                result.append(({
                    'shifted_items': frozenset(h['S']),
                    'multiplier': h['m']
                }, h['prob']))
        return result

    # ------------------------------------------------------------------
    # API: select_query
    # ------------------------------------------------------------------
    def select_query(self, budget_state):
        """
        Choose the next observation to maximize expected information gain.

        Input:
            budget_state: dict with keys:
                'remaining_turns'  — int
                'queried_pairs'    — set of (source, item) already queried

        Output: (target_source, target_item) tuple
        State:  None (read-only; caller must execute the query and
                call update_observation with the result)
        """
        queried_pairs = budget_state.get('queried_pairs', set())

        # If no trusted source yet: cycle through sources on unqueried items
        if self._trusted_source is None:
            unqueried_items = [it for it in self._items if it not in self._queried_values]
            if not unqueried_items:
                unqueried_items = self._items
            test_item = unqueried_items[0]
            for s in self._sources:
                if (s, test_item) not in queried_pairs:
                    return (s, test_item)
            # Fallback: any unqueried pair
            for s in self._sources:
                for it in self._items:
                    if (s, it) not in queried_pairs:
                        return (s, it)
            return (self._sources[0], self._items[0])

        # Trusted source established: pick item by InfoGain
        unqueried = [it for it in self._items if it not in self._queried_values]
        if not unqueried:
            return (self._trusted_source, self._items[0])

        active_h = [h for h in self._hypotheses if h['prob'] > 0]
        if len(active_h) <= 1:
            return (self._trusted_source, unqueried[0])

        best_item = unqueried[0]
        min_expected_entropy = float('inf')

        for test_item in unqueried:
            predictions = {}
            for h in active_h:
                exp = (int(self._initial_values[test_item] * h['m'])
                       if test_item in h['S']
                       else self._initial_values[test_item])
                if exp not in predictions:
                    predictions[exp] = []
                predictions[exp].append(h)

            expected_entropy = 0.0
            for exp_val, matching_h in predictions.items():
                p_val = sum(h['prob'] for h in matching_h)
                ent = 0.0
                if p_val > 0:
                    for h in matching_h:
                        p_h_given_val = h['prob'] / p_val
                        if p_h_given_val > 0:
                            ent -= p_h_given_val * math.log2(p_h_given_val)
                expected_entropy += p_val * ent

            if expected_entropy < min_expected_entropy:
                min_expected_entropy = expected_entropy
                best_item = test_item

        return (self._trusted_source, best_item)

    # ------------------------------------------------------------------
    # API: propose_state
    # ------------------------------------------------------------------
    def propose_state(self):
        """
        Produce the MAP estimate of the hidden world state.

        Input:  None
        Output: dict mapping each item to its estimated current value
        State:  None (read-only)
        """
        active_h = [h for h in self._hypotheses if h['prob'] > 0]

        if active_h:
            best_h = random.choice(active_h)
            shifted_set, mult = best_h['S'], best_h['m']
        else:
            shifted_set, mult = set(), 1.0

        proposed = {}
        for it in self._items:
            if it in shifted_set:
                proposed[it] = int(self._initial_values[it] * mult)
            else:
                proposed[it] = self._initial_values[it]
        return proposed

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _normalize(self):
        total = sum(h['prob'] for h in self._hypotheses)
        if total > 0:
            for h in self._hypotheses:
                h['prob'] /= total

    def _absorb_consensus_observations(self):
        """When trust is locked, absorb any items where all sources
        agreed on a value during the trust-discovery phase."""
        item_obs = {}
        for s, obs_list in self._source_observations.items():
            for item, val in obs_list:
                if item not in item_obs:
                    item_obs[item] = []
                item_obs[item].append((s, val))

        for item, reports in item_obs.items():
            if item in self._queried_values:
                continue
            if len(reports) >= len(self._sources):
                vals = [v for _, v in reports]
                majority_val = max(set(vals), key=vals.count)
                self._queried_values[item] = majority_val

    def _update_posterior(self):
        for h in self._hypotheses:
            possible = True
            for it, val in self._queried_values.items():
                exp = (int(self._initial_values[it] * h['m'])
                       if it in h['S']
                       else self._initial_values[it])
                if val != exp:
                    possible = False
                    break
            h['prob'] = 1.0 if possible else 0.0
        self._normalize()
