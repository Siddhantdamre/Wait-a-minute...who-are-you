# expression/narration.py
import os
import time
from expression.voice import SystemVoice
from expression.emotion import EMOTION_PROFILE

class StoryNarrator:
    def __init__(self):
        self.voice = SystemVoice()

    def narrate_arc(self, story_arc, output_dir="data/audio"):
        os.makedirs(output_dir, exist_ok=True)

        sections = [
            ("setup", story_arc.setup),
            ("inciting", story_arc.inciting_event),
            ("conflict", story_arc.conflict),
            ("climax", story_arc.climax),
            ("resolution", story_arc.resolution),
            ("moral", story_arc.moral),
        ]

        outputs = []
        for name, text in sections:
            profile = EMOTION_PROFILE.get(name, {"rate": 150, "pause": 0.5})
            path = f"{output_dir}/{name}.wav"

            # Optional emphasis for climax/moral
            if name in ("climax", "moral"):
                text = f"{text}"

            self.voice.speak(text, path, rate=profile["rate"])
            outputs.append(path)

            # Pause between arcs (non-blocking for file save)
            time.sleep(profile["pause"])

        # Run the TTS engine ONCE
        self.voice.flush()
        return outputs
