class ImageGenerator:
    def generate(self, prompt: str, output_path: str):
        raise NotImplementedError
    
from PIL import Image, ImageDraw, ImageFont
import os

class PlaceholderImageGenerator(ImageGenerator):
    def generate(self, prompt: str, output_path: str):
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        img = Image.new("RGB", (1024, 576), color=(245, 240, 230))
        draw = ImageDraw.Draw(img)

        text = prompt[:500]
        draw.multiline_text(
            (40, 40),
            text,
            fill=(30, 30, 30),
            spacing=8
        )

        img.save(output_path)

class StoryboardBuilder:
    def __init__(self, generator=None):
        self.generator = generator or PlaceholderImageGenerator()

    def build(self, story_arc, style="folk-art", output_dir="data/storyboards"):
        sections = [
            ("setup", story_arc.setup),
            ("inciting", story_arc.inciting_event),
            ("conflict", story_arc.conflict),
            ("climax", story_arc.climax),
            ("resolution", story_arc.resolution),
        ]

        outputs = []
        for name, text in sections:
            prompt = self._compose_prompt(text, style)
            path = f"{output_dir}/{name}.png"
            self.generator.generate(prompt, path)
            outputs.append(path)

        return outputs

    def _compose_prompt(self, text: str, style: str):
        return f"Illustration in {style} style: {text}"

