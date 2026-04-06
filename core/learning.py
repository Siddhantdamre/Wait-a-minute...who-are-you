class AutobiographicalLearner:
    def infer_preferences(self, memories):
        """
        Infers dominant values for a region or user.
        """
        value_counts = {}

        for _, values, _ in memories:
            for v in values.split(","):
                value_counts[v] = value_counts.get(v, 0) + 1

        if not value_counts:
            return []

        # Return top 2 values
        return sorted(
            value_counts, key=value_counts.get, reverse=True
        )[:2]

# Bias narrative / value graph activation
