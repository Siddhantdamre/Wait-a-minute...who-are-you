# Frontier Local Metacognition: First Local Results

This note records the first no-API local/open-weight run of the DEIC frontier metacognition task set at [frontier_tasks_metacog.jsonl](/Users/siddh/Projects/Emotion_and_AI/benchmarks/exec_meta_adapt/frontier/frontier_tasks_metacog.jsonl) using the local runner at [run_frontier_local.py](/Users/siddh/Projects/Emotion_and_AI/benchmarks/exec_meta_adapt/frontier_local/run_frontier_local.py). The scored outputs are kept local under `results/frontier_local/full_40/`.

## Headline Result

Both small open models were safe in the narrow sense on this 40-task run:

- `0` bluff rate
- `0` silent failure rate
- perfect handling of `adversarial_trust`
- perfect handling of `overflow_mismatch`

The failure mode is sharper than generic low accuracy:

**Both models collapse ordinary hidden-state uncertainty into `ESCALATE` instead of correctly separating `ABSTAIN` from `ESCALATE`.**

## Final Result Table

| Task Type | Qwen Acc | SmolLM Acc | Qwen Abstain | SmolLM Abstain | Qwen Escalate | SmolLM Escalate | Qwen Bluff | SmolLM Bluff |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `hidden_state_uncertainty` | `0.10` | `0.00` | `0.10` | `0.00` | `0.90` | `1.00` | `0.00` | `0.00` |
| `adversarial_trust` | `1.00` | `1.00` | `0.00` | `0.00` | `1.00` | `1.00` | `0.00` | `0.00` |
| `overflow_mismatch` | `1.00` | `1.00` | `0.00` | `0.00` | `1.00` | `1.00` | `0.00` | `0.00` |
| `clear_commit` | `0.80` | `1.00` | `0.10` | `0.00` | `0.10` | `0.00` | `0.00` | `0.00` |

## Overall Comparison

| Model | Final Acc | Commit Acc | Abstain Rate | Bluff Rate | Escalation Rate | Silent Failure Rate |
|---|---:|---:|---:|---:|---:|---:|
| `Qwen/Qwen2.5-1.5B-Instruct` | `0.725` | `1.00` | `0.05` | `0.00` | `0.75` | `0.00` |
| `HuggingFaceTB/SmolLM2-1.7B-Instruct` | `0.750` | `1.00` | `0.00` | `0.00` | `0.75` | `0.00` |

## Behavior Figure

![Frontier local metacognition behavior](./frontier_local_metacognition_behavior.svg)

## Submission Wording

Use this as the core claim:

> This benchmark reveals that small open models can be safe in the sense of avoiding bluffing, yet still fail metacognitively by collapsing ordinary uncertainty into escalation instead of distinguishing when abstention is the correct response.

## Short Interpretation

- `SmolLM` is stronger on `clear_commit`; it committed correctly on all 10 clear-commit cases.
- `Qwen` is slightly closer to the intended metacognitive distinction because it produced at least some true `ABSTAIN` on `hidden_state_uncertainty`.
- Neither model currently shows good calibration on ordinary hidden-state uncertainty.
- The benchmark is already useful because it separates `safe but over-escalatory` behavior from actual metacognitive discrimination.
