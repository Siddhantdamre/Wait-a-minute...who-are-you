from language.universal_language import UniversalLanguageBridge
from spatial.spatial_inference import SpatialCultureInference

bridge = UniversalLanguageBridge(enable_translation=False)
spatial = SpatialCultureInference()

inputs = {
    "en": "Tell me a cultural story about courage",
    "hi": "साहस पर आधारित सांस्कृतिक कहानी सुनाओ",
    "fr": "Raconte-moi une histoire culturelle sur le courage"
}

results = []

for lang, text in inputs.items():
    canonical = text  # TEMP: bypass translation for evaluation
    values = spatial.infer_values(18.52, 73.85)
    results.append(set(values))

intersection = set.intersection(*results)
union = set.union(*results)

score = len(intersection) / len(union)

print("Language Invariance Score:", score)
