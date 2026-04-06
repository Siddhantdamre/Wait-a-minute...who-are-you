from spatial.spatial_memory import SpatialMemory
from spatial.spatial_inference import SpatialCultureInference
import math

memory = SpatialMemory()
spatial = SpatialCultureInference()

def entropy(values):
    from collections import Counter
    c = Counter(values)
    total = sum(c.values())
    return -sum((v/total)*math.log(v/total) for v in c.values())

entropies = []

values_list = [
    ["Community", "Courage"],
    ["Community"],
    ["Community", "Duty"],
    ["Community"],
    ["Community", "Courage"],
]

for i, vals in enumerate(values_list):
    memory.store(
        lat=18.52,
        lon=73.85,
        region="Pune",
        values=vals,
        confidence=0.9
    )
    inferred = spatial.infer_values(18.52, 73.85)
    entropies.append(entropy(inferred))

print("Entropy over time:", entropies)
