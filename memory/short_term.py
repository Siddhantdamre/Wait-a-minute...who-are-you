class ShortTermMemory:
    def __init__(self, max_turns: int = 5):
        self.max_turns = max_turns
        self.buffer = []

    def add(self, memory_entry):
        self.buffer.append(memory_entry)
        if len(self.buffer) > self.max_turns:
            self.buffer.pop(0)

    def get_context(self):
        return self.buffer

    def clear(self):
        self.buffer = []
