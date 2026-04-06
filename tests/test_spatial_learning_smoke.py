from spatial.spatial_memory import SpatialMemory
from spatial.spatial_inference import SpatialCultureInference

memory = SpatialMemory()

# Simulate learning
memory.store(
    lat=18.5204, lon=73.8567,
    region="Pune",
    values=["Courage", "Community"],
    confidence=0.9
)

memory.store(
    lat=19.0760, lon=72.8777,
    region="Mumbai",
    values=["Ambition", "Community"],
    confidence=0.8
)

inference = SpatialCultureInference()

print("\nPUNE VALUES:")
print(inference.infer_values(18.52, 73.85))

print("\nMUMBAI VALUES:")
print(inference.infer_values(19.07, 72.87))
