class VisionInterface:
    def describe(self, image_path: str) -> str:
        raise NotImplementedError
    
from transformers import BlipProcessor, BlipForConditionalGeneration
from PIL import Image


class BlipVision(VisionInterface):
    def __init__(self, model_name="Salesforce/blip-image-captioning-base"):
        self.processor = BlipProcessor.from_pretrained(model_name)
        self.model = BlipForConditionalGeneration.from_pretrained(model_name)

    def describe(self, image_path: str) -> str:
        image = Image.open(image_path).convert("RGB")
        inputs = self.processor(image, return_tensors="pt")
        output = self.model.generate(**inputs, max_new_tokens=50)
        caption = self.processor.decode(output[0], skip_special_tokens=True)
        return caption

def caption_to_intent(caption: str) -> dict:
    return {
        "theme": "heritage",
        "region": "unknown",
        "mode": "story",
        "visual_context": caption
    }
