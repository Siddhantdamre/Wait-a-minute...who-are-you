class MemorySystem:
    def __init__(self):
        self.memory = []  # A list to store information

    def store(self, data):
        # Add data to memory
        self.memory.append(data)

    def recall(self):
        # Retrieve the last item from memory
        if self.memory:
            return self.memory[-1]
        return None

# Test Memory System
memory = MemorySystem()
memory.store("I learned that Python is awesome!")
print("Memory Recall:", memory.recall())
