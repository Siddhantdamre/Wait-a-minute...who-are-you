class ReasoningSystem:
    def __init__(self, knowledge_base):
        self.knowledge_base = knowledge_base

    def reason(self, question):
        # Simple reasoning: search for an answer in the knowledge base
        return self.knowledge_base.get(question, "I don't know.")

# Test Reasoning System
knowledge = {"What is AI?": "AI is the simulation of human intelligence in machines."}
reasoning = ReasoningSystem(knowledge)
print(reasoning.reason("What is AI?"))
