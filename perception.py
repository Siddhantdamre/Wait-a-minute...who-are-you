from transformers import pipeline

class PerceptionSystem:
    def __init__(self):
        # Load a pre-trained language model for text understanding
        self.model = pipeline("sentiment-analysis")

    def process_text(self, text):
        # Analyze the text and return the result
        result = self.model(text)
        return result

# Test Perception System
perception = PerceptionSystem()
text_input = "I feel great today!"
analysis = perception.process_text(text_input)
print("Perception Output:", analysis)
