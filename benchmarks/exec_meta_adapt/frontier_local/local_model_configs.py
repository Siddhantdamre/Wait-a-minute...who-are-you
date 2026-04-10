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
}


def get_model_config(model_name):
    normalized = model_name.strip().lower()
    if normalized not in LOCAL_MODEL_CONFIGS:
        raise ValueError(
            f"Unsupported local model '{model_name}'. Expected one of: {', '.join(sorted(LOCAL_MODEL_CONFIGS))}."
        )
    return dict(LOCAL_MODEL_CONFIGS[normalized])
