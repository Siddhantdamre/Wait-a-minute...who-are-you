from memory.short_term import ShortTermMemory
from memory.long_term import LongTermMemory


class MemoryManager:
    def __init__(self):
        self.short_term = ShortTermMemory()
        self.long_term = LongTermMemory()

    def remember(self, memory_entry):
        self.short_term.add(memory_entry)
        self.long_term.store(memory_entry)

    def get_context(self):
        return self.short_term.get_context()
