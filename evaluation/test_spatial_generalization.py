from spatial.spatial_inference import SpatialCultureInference
from collections import Counter
import math

def cosine(a, b):
    keys = set(a) | set(b)
    dot = sum(a[k]*b[k] for k in keys)
    na = math.sqrt(sum(a[k]**2 for k in keys))
    nb = math.sqrt(sum(b[k]**2 for k in keys))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


spatial = SpatialCultureInference()

v1 = Counter(spatial.infer_values(18.5204, 73.8567))  # Pune
v2 = Counter(spatial.infer_values(18.5300, 73.8500))  # Nearby
v3 = Counter(spatial.infer_values(28.6139, 77.2090))  # Delhi

print("Pune–Nearby Similarity:", cosine(v1, v2))
print("Pune–Delhi Similarity:", cosine(v1, v3))
