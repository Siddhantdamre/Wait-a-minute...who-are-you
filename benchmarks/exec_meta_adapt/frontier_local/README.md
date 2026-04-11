# frontier_local

No-API local/open-weight execution path for the metacognition benchmark.

## What Lives Here
- `local_model_configs.py`: supported local model definitions.
- `local_model_runner.py`: shared local inference helper.
- `run_frontier_local.py`: main local runner.
- `run_frontier_local_expansion.py`: expanded post-submission comparison runner.

## Notes
- This folder reuses the frozen task set, prompt contract, parser, and scoring from `../frontier/`.
- Use it when running on Kaggle GPU or other local GPU setups.
