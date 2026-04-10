from local_model_configs import get_model_config


class LocalModelRunner:
    def __init__(self):
        self._cache = {}

    def _load_backend(self):
        try:
            import torch
            from transformers import AutoModelForCausalLM, AutoTokenizer
        except ModuleNotFoundError as exc:
            raise RuntimeError(
                "Missing local inference dependencies. Install at least `transformers`, `torch`, and `accelerate` "
                "in the Kaggle environment before running the local frontier benchmark."
            ) from exc
        return torch, AutoModelForCausalLM, AutoTokenizer

    def _load_model(self, model_name):
        if model_name in self._cache:
            return self._cache[model_name]

        config = get_model_config(model_name)
        torch, AutoModelForCausalLM, AutoTokenizer = self._load_backend()
        use_cuda = torch.cuda.is_available()
        dtype = torch.bfloat16 if use_cuda else torch.float32

        try:
            tokenizer = AutoTokenizer.from_pretrained(config["hf_model_id"], trust_remote_code=True)
            model = AutoModelForCausalLM.from_pretrained(
                config["hf_model_id"],
                dtype=dtype,
                device_map="auto" if use_cuda else None,
                low_cpu_mem_usage=True,
                trust_remote_code=True,
            )
        except Exception as exc:
            raise RuntimeError(
                f"Failed to load local model '{config['hf_model_id']}'. "
                "Check Hugging Face model accessibility and local disk/GPU capacity in the Kaggle runtime."
            ) from exc
        if not use_cuda:
            model.to("cpu")
        model.eval()

        if tokenizer.pad_token_id is None and tokenizer.eos_token_id is not None:
            tokenizer.pad_token_id = tokenizer.eos_token_id

        self._cache[model_name] = {
            "config": config,
            "torch": torch,
            "tokenizer": tokenizer,
            "model": model,
        }
        return self._cache[model_name]

    @staticmethod
    def _build_prompt(tokenizer, system_prompt, messages):
        conversation = [{"role": "system", "content": system_prompt}] + list(messages)
        if hasattr(tokenizer, "apply_chat_template"):
            return tokenizer.apply_chat_template(
                conversation,
                tokenize=False,
                add_generation_prompt=True,
            )
        joined = [f"SYSTEM:\n{system_prompt}"]
        for message in messages:
            joined.append(f"{message['role'].upper()}:\n{message['content']}")
        joined.append("ASSISTANT:\n")
        return "\n\n".join(joined)

    def generate(self, model_name, system_prompt, messages):
        bundle = self._load_model(model_name)
        tokenizer = bundle["tokenizer"]
        model = bundle["model"]
        torch = bundle["torch"]
        config = bundle["config"]

        prompt = self._build_prompt(tokenizer, system_prompt, messages)
        inputs = tokenizer(prompt, return_tensors="pt")
        if torch.cuda.is_available():
            inputs = {key: value.to(model.device) for key, value in inputs.items()}

        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=config["max_new_tokens"],
                do_sample=False,
                pad_token_id=tokenizer.pad_token_id,
                eos_token_id=tokenizer.eos_token_id,
            )

        prompt_length = inputs["input_ids"].shape[1]
        generated = outputs[0][prompt_length:]
        return tokenizer.decode(generated, skip_special_tokens=True).strip()

_GLOBAL_RUNNER = LocalModelRunner()


def call_local_model(model_name, messages, system_prompt):
    return _GLOBAL_RUNNER.generate(model_name, system_prompt, messages)
