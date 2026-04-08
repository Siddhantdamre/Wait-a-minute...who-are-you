# DEIC — Discrete Executive Inference Core

A reusable cognitive subsystem for **hidden-state belief revision under partial observability**.

DEIC maintains a discrete hypothesis bank over hidden combinatorial structure, tracks source reliability through adaptive trust discovery, and allocates diagnostic queries by expected information gain under strict budget constraints.

---

## Key Result

**DEIC's core inference mechanisms transfer across domains. The main adaptation requirement is the hypothesis generator, not the trust, query selection, or posterior update logic.**

This was demonstrated through three domains:
- **Byzantine Executive Benchmark (C6)** — original development domain
- **Cyber Incident Diagnosis** — isomorphic transfer, zero code changes
- **Clinical Deterioration Monitoring** — non-isomorphic transfer, one backward-compatible change (`group_sizes` parameter)

---

## What DEIC Does

1. **Infers hidden structure** from sparse observations
2. **Tracks source reliability** — identifies which information sources are trustworthy
3. **Actively allocates queries** under a fixed budget to maximize information gain
4. **Revises beliefs safely** when the world changes
5. **Transfers across domains** — core inference logic is domain-agnostic; only the hypothesis generator needs adaptation

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

### Transfer: Cyber Incident Diagnosis (isomorphic, zero core changes)

| Solver | Budget=8 | Budget=12 |
|---|---|---|
| Random Baseline | 0.0% | 0.0% |
| **DEIC (adaptive trust)** | **57.0%** | **94.0%** |

### Transfer: Clinical Deterioration (non-isomorphic, variable group sizes)

| Solver | Budget=8 | Budget=12 |
|---|---|---|
| Random Baseline | 0.0% | 0.0% |
| DEIC (group_size=4 only, Gate 1) | 10.7% | 18.0% |
| **DEIC (variable group_sizes, Gate 2)** | **26.2%** | **83.2%** |

Gate 1 showed DEIC scored 56.6% on group-size=4 episodes but 0.0% on all others - proving the bottleneck was hypothesis generation, not inference logic. Gate 2's single backward-compatible change recovered non-4 episodes from 0% to 10-48%.

### Bounded Adaptive Recovery (Phase 15d)

ADAPT_REFINE is now the default adaptive execution policy for generator-backed fixed-family planner paths. It preserves the frozen baseline paths while making bounded family repair operationally useful after adoption.

| Case | Budget=12 | Budget=16 |
|---|---|---|
| Cyber anomaly `gs=3` | 0.00 -> 0.46 | 0.37 -> 0.91 |
| Cyber anomaly `gs=5` | 0.00 -> 0.69 | 0.58 -> 0.99 |
| Clinical fixed-family mismatch `gs=3` | 0.00 -> 0.44 | 0.35 -> 0.90 |
| Clinical fixed-family mismatch `gs=5` | 0.00 -> 0.68 | 0.60 -> 0.96 |
| Cyber `gs=4` baseline | 0.90 -> 0.90 | 1.00 -> 1.00 |
| C6 planner baseline | 0.91 -> 0.91 | 1.00 -> 1.00 |

This is a bounded adaptive-cognition result, not a claim of AGI. The system can now detect fixed-family failure, adopt a better adjacent family, and complete recovery under realistic budgets without harming the validated baseline paths.

---

## Architecture

DEIC separates into two cleanly independent concerns:

```
┌─────────────────────────────────┐
│     Core Inference Engine       │  ← domain-agnostic, transfers
│  ├ adaptive trust discovery     │
│  ├ InfoGain query selection     │
│  └ posterior elimination        │
├─────────────────────────────────┤
│   Hypothesis Generator          │  ← domain-specific, configurable
│  └ initialize_beliefs(env_spec) │
└─────────────────────────────────┘
```

---

## API

```python
from deic_core import DEIC

engine = DEIC(adaptive_trust=True)

# Fixed group size (benchmark/cyber)
engine.initialize_beliefs({
    'items': [...],
    'sources': [...],
    'group_size': 4,
    'valid_multipliers': [1.5, 2.0, 3.0, 5.0],
    'initial_values': {...},
})

# Variable group sizes (clinical/general)
engine.initialize_beliefs({
    'items': [...],
    'sources': [...],
    'group_sizes': [2, 3, 4, 5, 6],
    'valid_multipliers': [1.3, 1.8, 2.5],
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
| `initialize_beliefs(env_spec)` | Set up hypothesis bank (supports `group_size` or `group_sizes`) |
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
│   ├── deic_adapter.py               # Benchmark <-> DEIC bridge
│   ├── run_evaluation.py             # Evaluation harness
│   └── kaggle_submission.ipynb       # Published notebook
├── experiments/
│   ├── cyber_transfer/               # Isomorphic transfer test
│   │   ├── environment.py
│   │   ├── adapter.py
│   │   └── run_transfer_pilot.py
│   └── clinical_transfer/            # Non-isomorphic transfer test
│       ├── environment.py
│       ├── adapter.py
│       └── run_gate1_pilot.py
├── tests/
│   ├── test_golden_c6.py             # C6 golden regression guard
│   └── test_transfer_regression.py   # Transfer parity guard
└── PROJECT_LOG.md
```

---

## Running

```bash
# C6 golden regression
python tests/test_golden_c6.py

# Transfer regression (cyber + clinical)
python tests/test_transfer_regression.py

# Individual transfer pilots
python experiments/cyber_transfer/run_transfer_pilot.py
python experiments/clinical_transfer/run_gate1_pilot.py

# Adaptive recovery validation
python experiments/structure_anomaly.py
python experiments/cross_domain_adaptive_validation.py
```

---

## Research Context

This project contributes to the **Executive Functions** track of the Kaggle Measuring Progress Toward AGI competition. DEIC's core inference mechanisms — adaptive trust discovery, information-gain query selection, and posterior elimination — transferred across multiple hidden-state environments. The main adaptation requirement was the hypothesis generator rather than the trust or query logic. This suggests a useful architectural pattern for building reusable cognitive subsystems: separate domain-agnostic inference from domain-specific hypothesis generation.

DEIC is a concrete, testable cognitive module — not a claim of general intelligence.
