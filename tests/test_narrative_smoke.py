import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))
from core.agent import StoryAgent

# STEP 1: Create agent
agent = StoryAgent()

# STEP 2: Fake intent (normally from interpret())
intent = {
    "theme": "courage",
    "region": "Maharashtra",
    "mode": "story",
    "age": "child"
}

# STEP 3: Fake retrieved context (normally from RAG)
context_docs = [
    {
        "content": "A shepherd once guarded his flock during a fierce storm."
    }
]

# STEP 4: Generate story
story = agent.narrate(intent, context_docs)

# STEP 5: Print output
print("\n===== STORY OUTPUT =====\n")
print(story)
