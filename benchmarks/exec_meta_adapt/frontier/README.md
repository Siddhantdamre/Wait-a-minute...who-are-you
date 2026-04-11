# frontier

Prompting, parsing, scoring, and task assets for frontier-style metacognition evaluation.

## What Lives Here
- `frontier_tasks_metacog.jsonl`: fixed task set for metacognitive evaluation.
- `prompt_builder.py`: builds the task prompts.
- `response_parser.py`: parses strict JSON responses.
- `scoring_frontier.py`: scores model outputs on abstain/escalate/commit behavior.
- `run_frontier.py`: original API-oriented runner.

## Notes
- The benchmark contract here is frozen for submission-quality comparisons.
- For no-API local runs, use the sibling `frontier_local/` folder.
