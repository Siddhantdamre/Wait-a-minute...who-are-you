import math

class BeliefInspector:
    """
    A read-only structured output layer that exposes the internal belief
    state of a DEIC engine. Translates raw probabilities and internal
    variables into interpretable cognitive metrics.
    """

    def __init__(self, engine):
        """
        Initialize the Belief Inspector.
        
        Args:
            engine: The DEIC engine instance to inspect.
        """
        self.engine = engine

    def inspect(self, top_n=3):
        """
        Extract and compute structured metrics from the DEIC engine.

        Args:
            top_n (int): Number of top hypotheses to return in the summary.

        Returns:
            dict containing:
                - entropy (float): Shannon entropy of the active hypotheses probability distribution.
                - confidence_margin (float): Difference between MAP probability and runner-up probability.
                - top_hypotheses (list): List of top N hypotheses based on probability.
                - trust_distribution (dict): Dict of source identifier to trust score.
                - trusted_source_locked (bool): Boolean indicating if trust phase is resolved.
                - query_rationale (str): Text justification for the current objective.
        """
        # 1. Hypotheses scores
        scored_hypotheses = self.engine.score_hypotheses()
        # Sort by probability descending
        scored_hypotheses.sort(key=lambda x: x[1], reverse=True)
        
        # 2. Entropy
        entropy = 0.0
        for _hyp, prob in scored_hypotheses:
            if prob > 0:
                entropy -= prob * math.log2(prob)
                
        # 3. Confidence margin
        margin = 0.0
        if len(scored_hypotheses) >= 2:
            margin = scored_hypotheses[0][1] - scored_hypotheses[1][1]
        elif len(scored_hypotheses) == 1:
            margin = scored_hypotheses[0][1]

        # 4. Top N hypotheses
        top_h = scored_hypotheses[:top_n]

        # 5. Trust Distribution
        trust_dist = self.engine.update_trust()
        
        # 6. Trust locked
        trust_locked = self.engine._trusted_source is not None

        # 6a. Active Hypotheses Count
        active_hyp_count = len([h for h, p in scored_hypotheses if p > 0])

        # 7. Query Rationale
        if not trust_locked:
            if active_hyp_count == 0:
                rationale = "CRITICAL: Observation inconsistent with all hypotheses (Trust Open)"
            elif getattr(self.engine, 'adaptive_trust', True):
                rationale = "Phase 1: Trust Discovery (seeking divergence)"
            else:
                rationale = "Phase 1: Trust Discovery (seeking majority consensus)"
        else:
            unqueried_count = sum(1 for it in self.engine._items if it not in self.engine._queried_values)
            if active_hyp_count == 0:
                rationale = "CRITICAL: Observation inconsistent with all hypotheses (Trust Locked)"
            elif unqueried_count > 0:
                if active_hyp_count > 1:
                    rationale = f"Phase 2: Structural Elimination (resolving {active_hyp_count} hypotheses)"
                else:
                    rationale = "Completed: Posterior collapsed to single hypothesis"
            else:
                rationale = "Completed: All items queried"

        return {
            'entropy': float(entropy),
            'confidence_margin': float(margin),
            'top_hypotheses': top_h,
            'trust_distribution': trust_dist,
            'trusted_source_locked': trust_locked,
            'active_hypotheses_count': active_hyp_count,
            'query_rationale': rationale
        }

    def workspace(self, memory=None, top_n=3):
        """
        Produce a CognitiveState snapshot from current engine state.

        This is the canonical way to construct a global workspace.
        It calls inspect() internally and extends the output with
        workspace-specific fields (items progress, goal, memory summary).

        Args:
            memory: Optional CrossEpisodeMemory instance.
            top_n: Number of top hypotheses to include.

        Returns:
            CognitiveState dataclass instance.
        """
        from .workspace import CognitiveState

        inspector_data = self.inspect(top_n=top_n)

        return CognitiveState(
            entropy=inspector_data['entropy'],
            confidence_margin=inspector_data['confidence_margin'],
            top_hypotheses=inspector_data['top_hypotheses'],
            trust_distribution=inspector_data['trust_distribution'],
            trusted_source_locked=inspector_data['trusted_source_locked'],
            active_hypotheses_count=inspector_data['active_hypotheses_count'],
            trust_evidence=dict(self.engine._trust_evidence),
            suspicion_scores=dict(self.engine._suspicion_scores),
            is_flagged=any(s > 2 for s in self.engine._suspicion_scores.values()),
            reset_count=self.engine.reset_count,
            suspicion_triggers=self.engine.suspicion_triggers,
            adaptation_count=self.engine.adaptation_count,
            current_family_spec=(
                str(self.engine._current_generator.family_spec())
                if self.engine._current_generator
                and hasattr(self.engine._current_generator, 'family_spec')
                else ""
            ),
            query_rationale=inspector_data['query_rationale'],
            all_hypotheses=self.engine.score_hypotheses(),
            items_queried=len(self.engine._queried_values),
            items_total=len(self.engine._items),
            current_goal=self._derive_goal(inspector_data),
            episode_count=memory.total_episodes if memory else 0,
            memory_summary=(memory.summary()
                            if memory and hasattr(memory, 'summary')
                            else {}),
        )

    @staticmethod
    def _derive_goal(inspector_data):
        """Derive a human-readable cognitive goal from inspector state."""
        if not inspector_data['trusted_source_locked']:
            return "Establish trusted source"
        n_active = len([h for h, p in inspector_data['top_hypotheses'] if p > 0])
        if inspector_data['entropy'] > 0.25 and n_active > 1:
            return "Reduce hypothesis uncertainty"
        if inspector_data['confidence_margin'] < 0.80:
            return "Increase confidence margin"
        return "Ready to commit"

