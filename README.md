# DEIC — Discrete Executive Inference Core

A reusable cognitive subsystem for **hidden-state belief revision under partial observability**.

DEIC maintains a discrete hypothesis bank over hidden combinatorial structure, tracks source reliability through adaptive trust discovery, and allocates diagnostic queries by expected information gain under strict budget constraints.

---

## What DEIC Does

1. **Infers hidden structure** from sparse observations
2. **Tracks source reliability** — identifies which information sources are trustworthy
3. **Actively allocates queries** under a fixed budget to maximize information gain
4. **Revises beliefs safely** when the world changes
5. **Transfers across domains** — the same `core.py` works on structurally isomorphic problems without modification

## What DEIC Is Not

- Not a claim of building AGI
- Not general intelligence, common sense reasoning, or universal planning
- Not human-level cognition
- It solves one specific family of structured inference problems under partial observability

---

## Empirical Results

### Byzantine Executive Belief Benchmark (C6)

| Solver | Budget=8 | Budget=12 |
|---|---|---|
| Random Baseline | ~0% | ~0% |
| Continuous Hierarchical Core | 0.0% | 0.0% |
| DEIC (no adaptive trust) | ~37% | ~81% |
| **DEIC (adaptive trust)** | **~61%** | **~94%** |

### Cross-Domain Transfer: Cyber Incident Diagnosis

Tested on a simulated service mesh with hidden cascading failures — **zero changes to `deic_core/core.py`**:

| Solver | Budget=8 | Budget=12 |
|---|---|---|
| Random Baseline | 0.0% | 0.0% |
| DEIC (no adaptive trust) | 37.7% | — |
| **DEIC (adaptive trust)** | **59.7%** | **94.3%** |

---

## API

```python
from deic_core import DEIC

engine = DEIC(adaptive_trust=True)

engine.initialize_beliefs({
    'items': [...],
    'sources': [...],
    'group_size': 4,
    'valid_multipliers': [1.5, 2.0, 3.0, 5.0],
    'initial_values': {...},
})

while budget_remaining:
    source, item = engine.select_query({
        'remaining_turns': remaining,
        'queried_pairs': already_queried,
    })
    value = query_environment(source, item)
    engine.update_observation(source, item, value, t)

answer = engine.propose_state()
```

### Methods

| Method | Purpose |
|---|---|
| `initialize_beliefs(env_spec)` | Set up hypothesis bank for a new episode |
| `update_observation(source, item, value, t)` | Incorporate one piece of evidence |
| `update_trust()` | Recompute source reliability scores |
| `score_hypotheses()` | Inspect current belief state |
| `select_query(budget_state)` | Choose next query by expected information gain |
| `propose_state()` | Output MAP estimate of hidden world state |

---

## Project Structure

```
├── deic_core/                        # Reusable module (domain-agnostic)
│   ├── __init__.py
│   └── core.py                       # DEIC class
├── benchmark/                        # Kaggle Executive Functions benchmark
│   ├── environment.py                # C3–C6 procedural environment
│   ├── solvers.py                    # Original solver implementations
│   ├── deic_adapter.py               # Benchmark ↔ DEIC bridge
│   ├── run_evaluation.py             # Evaluation harness
│   └── kaggle_submission.ipynb       # Published notebook
├── experiments/
│   └── cyber_transfer/               # Second-domain transfer test
│       ├── environment.py            # Cyber incident environment
│       ├── adapter.py                # Cyber ↔ DEIC bridge
│       └── run_transfer_pilot.py     # Transfer evaluation
├── tests/
│   └── test_golden_c6.py             # Golden regression guard
└── PROJECT_LOG.md                    # Milestone history
```

---

## Benchmark: C3 → C6 Difficulty Ladder

Each condition removes a solver shortcut:

| Condition | What It Breaks |
|---|---|
| **C3** (Stale contradiction) | Simple contradiction detection |
| **C4** (Active deception) | Naive majority voting |
| **C5** (Alert boundary corruption) | Deterministic memory replay |
| **C6** (Hidden drifting structure) | Static factorization and flat heuristics |

---

## Running

### Regression test
```bash
python tests/test_golden_c6.py
```

### Cyber transfer pilot
```bash
python experiments/cyber_transfer/run_transfer_pilot.py
```

---

## Research Context

This project contributes to the **Executive Functions** track of the Kaggle Measuring Progress Toward AGI competition. It provides a benchmark that isolates hidden-structure belief revision as a specific cognitive challenge, and identifies discrete structured inference with adaptive trust as a more productive approach than continuous latent-space methods for this task family.

DEIC is a concrete, testable cognitive module — not a claim of general intelligence.
