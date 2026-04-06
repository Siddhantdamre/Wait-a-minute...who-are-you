from memory.autobiographical import AutobiographicalEntry
from memory.autobiographical_store import AutobiographicalMemory
from core.learning import AutobiographicalLearner
from datetime import datetime

store = AutobiographicalMemory()

store.store(
    AutobiographicalEntry(
        user_id="u1",
        region="Maharashtra",
        story_theme="courage",
        active_values=["Courage", "Community"],
        confidence=0.9,
        user_feedback="agree",
        timestamp=datetime.utcnow()
    )
)

store.store(
    AutobiographicalEntry(
        user_id="u2",
        region="Maharashtra",
        story_theme="leadership",
        active_values=["Duty", "Community"],
        confidence=0.8,
        user_feedback="agree",
        timestamp=datetime.utcnow()
    )
)

learner = AutobiographicalLearner()
prefs = learner.infer_preferences(
    store.fetch_by_region("Maharashtra")
)

print("\nINFERRED REGIONAL VALUES:")
print(prefs)
