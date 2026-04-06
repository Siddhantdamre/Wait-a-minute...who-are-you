# [FILE] core/narrative.py
# Restoring this dependency so agent.py imports don't crash
class NarrativePlanner:
    def __init__(self, api_key):
        self.client = None
    def plan(self, requirements, history):
        return {"arc": "Standard Folklore", "theme": requirements.get("theme")}
