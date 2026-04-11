LOCAL_MODEL_CONFIGS = {
    "qwen": {
        "label": "Qwen/Qwen2.5-1.5B-Instruct",
        "hf_model_id": "Qwen/Qwen2.5-1.5B-Instruct",
        "max_new_tokens": 96,
        "notes": "Small instruct model with strong structured-output behavior for its size.",
    },
    "smollm": {
        "label": "HuggingFaceTB/SmolLM2-1.7B-Instruct",
        "hf_model_id": "HuggingFaceTB/SmolLM2-1.7B-Instruct",
        "max_new_tokens": 96,
        "notes": "Open small instruct baseline that avoids gated-model friction while staying Kaggle-feasible.",
    },
    "tinyllama": {
        "label": "TinyLlama/TinyLlama-1.1B-Chat-v1.0",
        "hf_model_id": "TinyLlama/TinyLlama-1.1B-Chat-v1.0",
        "max_new_tokens": 96,
        "notes": "Llama-family small instruct baseline that is fully open and easy to run locally.",
    },
    "granite": {
        "label": "ibm-granite/granite-3.1-2b-instruct",
        "hf_model_id": "ibm-granite/granite-3.1-2b-instruct",
        "max_new_tokens": 96,
        "notes": "Small open instruct model that provides a stronger non-Qwen comparison point without gated-model friction.",
    },
}


def get_model_config(model_name):
    normalized = model_name.strip().lower()
    if normalized not in LOCAL_MODEL_CONFIGS:
        raise ValueError(
            f"Unsupported local model '{model_name}'. Expected one of: {', '.join(sorted(LOCAL_MODEL_CONFIGS))}."
        )
    return dict(LOCAL_MODEL_CONFIGS[normalized])
