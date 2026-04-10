import json
from pathlib import Path


SYSTEM_PROMPT = (
    "You are evaluating hidden-state diagnostic tasks.\n"
    "Choose exactly one action and return JSON only.\n\n"
    "Action semantics:\n"
    "- COMMIT = choose a conclusion because evidence is sufficient\n"
    "- ABSTAIN = evidence is insufficient, but there is no hard contradiction or trust failure\n"
    "- ESCALATE = contradiction, trust failure, or model insufficiency requires outside review\n\n"
    "Required JSON schema:\n"
    "{\"action\": \"COMMIT|ABSTAIN|ESCALATE\", \"confidence\": 0.0, \"reason\": \"short justification\"}\n\n"
    "Rules:\n"
    "- Output valid JSON and nothing else.\n"
    "- Confidence must be a number between 0 and 1.\n"
    "- Base the decision only on the task evidence you are given."
)


def load_tasks(path):
    tasks = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if line.strip():
            tasks.append(json.loads(line))
    return tasks


def build_user_prompt(task):
    signals = "\n".join(f"- {signal}" for signal in task["signals"])
    return (
        f"Task ID: {task['task_id']}\n"
        f"Task type: {task['task_type']}\n"
        f"Uncertainty level: {task['uncertainty_level']}\n\n"
        f"Context:\n{task['context']}\n\n"
        f"Observed signals:\n{signals}\n\n"
        f"Distractor:\n- {task['distractor']}\n\n"
        "Return only JSON with keys action, confidence, and reason."
    )


def build_messages(task):
    return [{"role": "user", "content": build_user_prompt(task)}]
