# RELEASE v1.3: DEIC Self-Model Layer

## What was added
- **Self-Model Module** (`deic_core/self_model.py`): Deterministic high-level cognitive representation focusing on beliefs, goals, and counterfactual triggers.
- **Global Workspace Extension**: Fully integrated `CognitiveState` as the central shared record.
- **Counterfactual Reasoning**: Logic to identify and expose primary belief-flipping evidence (MAP vs Runner-up).
- **Self-Limitation Detection**: Automated warnings for budget exhaustion and high entropy fragmentation.
- **Sample Generation** (`experiments/self_model_samples.py`): Demonstrated agentic transparency across C6, Cyber, and Clinical domains.
- **Dedicated Testing**: `tests/test_self_model.py` for validation.

## What stayed frozen
- **DEIC Core Inference Engine**: Bayesian logic remains unchanged.
- **Benchmarks**: C6, cyber, and clinical evaluation environments are unmodified.
- **Transfer Adapters**: Interface stability maintained.

## What passed
- **Full Regression Suite**: 100% success across all 29 core and transfer tests.
- **Self-Model Unit Tests**: 100% success (6 tests).

## Next Planned Phase: Minimal Planner
Moving from passive InfoGain toward goal-aware strategic selection (Exploration vs Refining vs Early Commit).
