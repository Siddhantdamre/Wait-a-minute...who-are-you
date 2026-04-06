# expression/voice.py
import pyttsx3

class VoiceInterface:
    def speak(self, text: str, output_path: str, rate: int):
        raise NotImplementedError

    def flush(self):
        raise NotImplementedError


class SystemVoice(VoiceInterface):
    def __init__(self):
        self.engine = pyttsx3.init()

    def speak(self, text: str, output_path: str, rate: int):
        self.engine.setProperty("rate", rate)
        self.engine.save_to_file(text, output_path)

    def flush(self):
        self.engine.runAndWait()
