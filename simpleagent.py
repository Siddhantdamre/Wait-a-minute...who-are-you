class SimpleAGI:
    def __init__(self):
        self.perception = PerceptionSystem()
        self.memory = MemorySystem()
        self.learning = LearningSystem(actions=["move_left", "move_right"])
        self.reasoning = ReasoningSystem({"What is AI?": "AI is the simulation of human intelligence in machines."})
        self.action = ActionSystem()

    def perceive_and_act(self, sensory_input):
        # Perceive input
        perception_output = self.perception.process_text(sensory_input)
        self.memory.store(perception_output)

        # Reason and decide
        action = self.learning.choose_action("default_state")

        # Act
        self.action.perform_action(action)

# Test Simple AGI
agi = SimpleAGI()
agi.perceive_and_act("Hello world!")
