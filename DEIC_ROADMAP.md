# DEIC Program: AGI-Helpful Development Roadmap

---

## 1. Current AGI Relevance

DEIC currently covers one specific cognitive capability from the Executive Functions family: **hidden-state belief revision under partial observability with adversarial sources and tight resource constraints**.

Within the DeepMind/Kaggle AGI framework (2026), this maps to:

| AGI Capability | DEIC Coverage | Evidence |
|---|---|---|
| Belief revision / state estimation | **Strong** | C6 benchmark, 3-domain transfer |
| Source reliability tracking | **Strong** | Adaptive trust discovery transfers |
| Active information gathering | **Strong** | InfoGain query selection transfers |
| Cognitive inhibition (suppress bad sources) | **Moderate** | Trust phase filters adversarial nodes |
| Cognitive flexibility (adapt to structure) | **Moderate** | Variable group-size extension worked |
| Planning under uncertainty | **Absent** | No planner exists yet |
| Sequential multi-step reasoning | **Absent** | DEIC solves one-shot diagnosis, not chains |
| Common sense / world knowledge | **Absent** | DEIC has no knowledge beyond env_spec |
| Language understanding | **Absent** | No NL interface |
| Cross-episode learning | **Absent** | Each episode starts from scratch |

DEIC is one column in a much larger table. It is a strong column, but it is one column.

---

## 2. Next Indispensable Missing Pieces

The minimum serious stack to turn DEIC into part of a broader AGI-helpful architecture has **five** components. Not ten. Five.

### 2a. Hypothesis Generator Framework

**What it is:** A standardized interface for plugging domain-specific latent structure definitions into DEIC.

**Why it's next:** The clinical transfer proved this is DEIC's main adaptation surface. Currently, each adapter hardcodes the hypothesis setup inline. A clean framework would let new domains define `HypothesisSpec` objects that DEIC consumes without adapter code touching the hypothesis bank directly.

**What it replaces:** The `env_spec` dict being manually constructed in each adapter.

### 2b. Commit Controller (Minimal Planner)

**What it is:** A decision layer that answers: query again? commit now? escalate uncertainty? stop early?

**Why it's needed:** DEIC currently uses a fixed rule: query until budget-1, then commit. A real agent needs to decide *when* the posterior is confident enough to commit, or when to stop because further queries won't help. This is the difference between "solver" and "cognitive controller."

**Scope:** Not a general planner. Just a commit/continue/escalate decision function that reads DEIC's belief state.

### 2c. Belief Inspector

**What it is:** A structured output layer that exposes DEIC's internal state: current top hypotheses, trust weights, uncertainty level, query rationale.

**Why it's needed:** Any system that couples DEIC with a planner or an LLM needs to read DEIC's belief state in a structured way. Currently, `score_hypotheses()` returns a flat list. A proper inspector would compute entropy, confidence margin, trust distribution, and query justification.

**Scope:** Read-only. Does not change inference logic.

### 2d. Cross-Episode Memory

**What it is:** A lightweight layer that adjusts priors based on patterns observed across previous episodes.

**Why it's needed:** Currently, DEIC treats every episode as independent. In real deployment, the system would learn that certain failure patterns are more common and adjust the hypothesis prior accordingly. This is the simplest form of learning that doesn't require neural networks.

**Scope:** Prior bias vector over hypothesis features, updated by exponential moving average. Not deep learning. Not replay buffers.

### 2e. Tool / Action Interface

**What it is:** A standardized protocol for DEIC to request observations from and submit actions to arbitrary environments.

**Why it's needed:** Currently, each adapter manually translates between the environment's API and DEIC's API. A clean tool interface would define a universal `observe(source, item) -> value` and `commit(state) -> result` contract.

---

## 3. Best Build Order

Force-ranked by AGI relevance × empirical value × risk of wasted effort:

| Rank | Module | Justification |
|---|---|---|
| **1** | Hypothesis Generator Framework | Highest evidence shows this is the adaptation surface. Formalizing it makes every future domain cheaper. Zero risk — it's a refactor of what already works. |
| **2** | Belief Inspector | Required by every downstream module (planner, LLM coupling, debugging). Small, read-only, no risk to core. Unlocks everything else. |
| **3** | Commit Controller | Transforms DEIC from solver to controller. Highest AGI-relevance step — moves from "answer when asked" to "decide when confident." Moderate risk — needs careful integration with budget logic. |
| **4** | Cross-Episode Memory | Adds learning without requiring architecture changes. Moderate value — only matters if DEIC runs on repeated episodes in the same domain. Low risk. |
| **5** | Tool / Action Interface | Important for deployment but least scientifically interesting. Build last, when there are 3+ domains to justify the abstraction. |

---

## 4. Immediate Next Branch

### Branch: `hypothesis-generator-framework`

**Goal:** Extract the hypothesis generation logic from `initialize_beliefs()` into a clean `HypothesisGenerator` interface that domain adapters implement, while keeping the inference core untouched.

### First 7 Actions

1. **Define `HypothesisGenerator` protocol.** Create `deic_core/hypothesis.py` with a base class:
   ```python
   class HypothesisGenerator:
       def generate(self, env_spec) -> list[dict]:  # returns hypothesis dicts
       def valid_group_sizes(self) -> list[int]:
       def valid_multipliers(self) -> list[float]:
   ```

2. **Create `FixedPartitionGenerator`.** This replaces the current inline logic in `initialize_beliefs()`. Accepts `group_size` or `group_sizes` and `valid_multipliers`. Produces exactly the same hypotheses as today. This is the backward-compatibility layer.

3. **Refactor `initialize_beliefs()`.** Accept either an `env_spec` dict (backward compatible) or a `HypothesisGenerator` instance. Internally, if given a dict, wrap it in a `FixedPartitionGenerator`. If given a generator, call `generator.generate(env_spec)`.

4. **Run golden regression.** C6, cyber, and clinical must all still pass with no tolerance changes.

5. **Create `ClinicalHypothesisGenerator`.** Move the clinical-specific `group_sizes=[2,3,4,5,6]` logic from the adapter into a generator class. The adapter becomes thinner.

6. **Create `CyberHypothesisGenerator`.** Same pattern. The adapter just passes the generator to DEIC.

7. **Run full regression suite.** All three test files. If anything drifts, revert.

### Success Criteria
- All existing tests pass.
- New domains can be added by writing a `HypothesisGenerator` subclass and an adapter, without touching `deic_core/core.py`.
- The benchmark adapter still works with the old `env_spec` dict API.

### Failure Criteria
- Any regression test fails after refactor.
- The `HypothesisGenerator` abstraction forces changes to trust, query, or posterior logic.
- The refactor adds complexity without reducing adapter code.

---

## 5. Integration Architecture

Target architecture for a future AGI-helpful system built around DEIC:

```
┌──────────────────────────────────────────────────────┐
│                  Language / UI Layer                  │
│  (LLM, chat, explanation — optional, added last)     │
├──────────────────────────────────────────────────────┤
│               Commit Controller / Planner            │
│  query again? | commit? | escalate? | switch hyps?   │
│  reads: belief inspector output                      │
├──────────────────────────────────────────────────────┤
│                  Belief Inspector                     │
│  entropy | confidence | trust dist | query rationale │
├──────────────────────────────────────────────────────┤
│  ┌────────────────────┐  ┌─────────────────────────┐ │
│  │   DEIC Core        │  │  Hypothesis Generator   │ │
│  │  ├ trust update     │  │  ├ FixedPartition       │ │
│  │  ├ posterior elim   │  │  ├ ClinicalVariable     │ │
│  │  ├ InfoGain query   │  │  ├ CyberServices        │ │
│  │  └ propose_state    │  │  └ [future domains]     │ │
│  └────────────────────┘  └─────────────────────────┘ │
├──────────────────────────────────────────────────────┤
│               Cross-Episode Memory                   │
│  prior bias | domain statistics | failure patterns   │
├──────────────────────────────────────────────────────┤
│              Tool / Action Interface                 │
│  observe(source, item) -> value                      │
│  commit(state) -> result                             │
├──────────────────────────────────────────────────────┤
│                   Environments                       │
│  C6 Benchmark | Cyber | Clinical | [future domains]  │
└──────────────────────────────────────────────────────┘
```

**Key principle:** Each layer depends only on the layer below it. DEIC core never depends on the planner, the inspector, or the language layer. New domains are added at the bottom (environment + hypothesis generator), not by rewriting the middle.

---

## 6. Hard Boundaries

### Do not do

| Prohibited Action | Why |
|---|---|
| Reopen the continuous hierarchical core | It failed on C6. Evidence is clear. Reviving it is a loop. |
| Expand the benchmark past C6 | C6 is frozen for the publication cycle. New conditions need new justification. |
| Build an LLM-coupled agent before the planner exists | Coupling with an LLM before DEIC has a commit controller will produce a brittle demo, not a module. |
| Add neural components to DEIC core | DEIC's value is in interpretable discrete inference. Making it neural would destroy the transfer evidence. |
| Rebrand as "AGI achieved" | No. Not yet. Maybe not ever for this component alone. |
| Design more than one new module at a time | Build one, test one, freeze one. |

### Claims that remain unjustified

- DEIC works on continuous-state domains (untested)
- DEIC works when the adversary is strategic rather than stale (untested)
- DEIC scales to large item/source counts (untested beyond 8 items, 3 sources)
- The commit controller improves over fixed-budget commitment (not built yet)
- Cross-episode learning improves cold-start performance (not built yet)

### What should remain frozen

- `deic_core/core.py` inference logic (trust, posterior, InfoGain)
- Benchmark environment `C3→C6`
- Published Kaggle notebook
- Golden regression targets and tolerance bands

---

## 7. Reusable Mission Statement

> The DEIC Program develops a reusable executive inference core for hidden-state belief revision under partial observability. DEIC infers latent combinatorial structure from sparse evidence, tracks source reliability through adaptive trust discovery, and allocates diagnostic queries by expected information gain under strict budget constraints. Empirically, DEIC's core inference mechanisms — trust discovery, information-gain query selection, and posterior elimination — have transferred across multiple domains (Byzantine inventory auditing, cyber incident diagnosis, clinical deterioration monitoring) with the main domain-specific adaptation requirement being the hypothesis generator rather than the reasoning engine. This work contributes a concrete, testable cognitive subsystem to the broader effort of building reliable autonomous agents, positioned within the Executive Functions capability family. DEIC is not a claim of general intelligence; it is one serious, expandable building block for systems that must reason under uncertainty, track trust, and make diagnostic decisions with limited observations.
