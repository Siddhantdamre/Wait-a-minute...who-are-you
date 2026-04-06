class MultimodalOrchestrator:
    def __init__(self):
        self.voice = None
        self.visual = None

        # Try to load voice (optional)
        try:
            from expression.voice import SystemVoice as VoiceSynthesizer
            self.voice = VoiceSynthesizer()
        except Exception:
            self.voice = None

        # Try to load visuals (optional)
        try:
            from expression.storyboard import StoryboardBuilder as ImageEngine
            self.visual = ImageEngine()
        except Exception:
            self.visual = None

    def generate_all(self, narrative):
        outputs = {}

        # To this:
        outputs["text"] = narrative  # ✅ narrative is already the string

        # Voice is optional
        if self.voice:
            try:
                outputs["voice"] = self.voice.speak(narrative.text, output_path="output.mp3", rate=1)
            except Exception:
                outputs["voice"] = None

        # Visuals are optional
        if self.visual:
            try:
                outputs["images"] = self.visual.build(narrative)
            except Exception:
                outputs["images"] = None

        return outputs
