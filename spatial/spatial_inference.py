from spatial.spatial_memory import SpatialMemory
from spatial.spatial_learner import SpatialValueLearner

class SpatialCultureInference:
    def __init__(self):
        self.memory = SpatialMemory()
        self.learner = SpatialValueLearner()

    def infer_values(self, lat, lon, top_k=3):
        records = self.memory.fetch_all()
        if not records:
            return []

        model = self.learner.learn(records)
        values = self.learner.predict(model, lat, lon)

        return values[:top_k]
