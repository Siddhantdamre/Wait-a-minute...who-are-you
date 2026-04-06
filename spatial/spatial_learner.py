import math
from collections import defaultdict

from knowledge import values

class SpatialValueLearner:
    def __init__(self, bandwidth_km=50):
        self.bandwidth = bandwidth_km

    def _distance_km(self, lat1, lon1, lat2, lon2):
        return math.sqrt((lat1 - lat2)**2 + (lon1 - lon2)**2) * 111

    def learn(self, spatial_records):
        """
        Learns value distributions from spatial memory.
        """
        model = []

        for lat, lon, values in spatial_records:
            for v in values.split(","):
                model.append((lat, lon, v))


        return model

    def predict(self, model, query_lat, query_lon):
        """
        Predict dominant values for a location.
        """
        scores = defaultdict(float)

        for lat, lon, value in model:
            d = self._distance_km(lat, lon, query_lat, query_lon)
            if d < self.bandwidth:
                weight = math.exp(-d / self.bandwidth)
                scores[value] += weight

        return sorted(scores, key=scores.get, reverse=True)
