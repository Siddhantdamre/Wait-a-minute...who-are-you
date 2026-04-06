from transformers import pipeline

class UniversalLanguageBridge:
    def __init__(self, enable_translation=False):
        self.enable_translation = enable_translation

        if enable_translation:
            from transformers import pipeline
            self.translator = pipeline(
                "translation",
                model="facebook/nllb-200-distilled-600M"
            )
        else:
            self.translator = None

    def to_canonical(self, text, source_lang):
        # For evaluation & core reasoning
        if not self.enable_translation or source_lang == "en":
            return text
        result = self.translator(
            text,
            src_lang=source_lang,
            tgt_lang="eng_Latn"
        )
        return result[0]["translation_text"]

    def from_canonical(self, text, target_lang):
        if not self.enable_translation or target_lang == "en":
            return text
        result = self.translator(
            text,
            src_lang="eng_Latn",
            tgt_lang=target_lang
        )
        return result[0]["translation_text"]
