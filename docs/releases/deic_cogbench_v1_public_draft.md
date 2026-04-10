# DEIC-CogBench v1 Public Draft

## Audit Summary

DEIC-CogBench v1 is public-draft ready as a bounded cognitive benchmark package.

What is complete:
- frozen contract in [benchmarks/exec_meta_adapt/spec.md](C:/Users/siddh/Projects/Emotion_and_AI/benchmarks/exec_meta_adapt/spec.md)
- runnable suite and ablation entry points in [benchmarks/exec_meta_adapt/run_suite.py](C:/Users/siddh/Projects/Emotion_and_AI/benchmarks/exec_meta_adapt/run_suite.py) and [benchmarks/exec_meta_adapt/run_ablations.py](C:/Users/siddh/Projects/Emotion_and_AI/benchmarks/exec_meta_adapt/run_ablations.py)
- explicit train and held-out transfer splits
- auditable traces, self-model snapshots, and explanation traces in the package output
- safety metrics surfaced directly in the report, including silent failure and false adaptation
- a clean local results bundle under `results/deic_cogbench/public_draft_release/`

What remains intentionally modest:
- this is a public draft, not a polished benchmark website or paper release
- the benchmark is bounded to the current DEIC platform and three current domains
- the benchmark favors transparency over headline score chasing

## Benchmark Summary Table

| Cohort | Episodes | Final Accuracy | Accuracy On Commit | Abstention | Silent Failure | False Adaptation |
|---|---:|---:|---:|---:|---:|---:|
| baseline_train | 300 | 0.23 | 1.00 | 0.77 | 0.00 | 0.17 |
| anomaly_train | 250 | 0.06 | 0.24 | 0.73 | 0.00 | 0.20 |
| heldout_transfer | 150 | 0.33 | 1.00 | 0.67 | 0.00 | 0.00 |
| full_package | 700 | 0.19 | 0.73 | 0.73 | 0.00 | 0.14 |

## Ablation Summary Table

| Variant | Episodes | Final Accuracy | Delta vs Frozen Full | Silent Failure | False Adaptation |
|---|---:|---:|---:|---:|---:|
| frozen_full | 550 | 0.15 | 0.00 | 0.00 | 0.18 |
| no_planner | 550 | 0.13 | -0.02 | 0.00 | 0.00 |
| no_self_model | 550 | 0.15 | 0.00 | 0.00 | 0.18 |
| no_memory | 550 | 0.15 | 0.00 | 0.00 | 0.18 |
| no_adaptation | 550 | 0.13 | -0.03 | 0.00 | 0.18 |
| no_safety_circuit | 550 | 0.25 | +0.09 | 0.75 | 0.00 |

Interpretation:
- planner support helps modestly on the frozen package aggregate
- bounded adaptation contributes measurable anomaly performance
- the safety circuit is not optional, because removing it improves superficial score while collapsing silent-failure behavior

## Known Limitations

- The benchmark measures a bounded cognitive subsystem, not open-ended intelligence.
- Absolute anomaly performance is still low in the hardest train mismatch cohorts.
- The package uses the current repo's three domains rather than a broader external task set.
- The C6 budget-8 path has shown mild noise in earlier validation history and should be treated as slightly noisy rather than perfectly rigid.
- This public draft emphasizes reproducibility and failure visibility over polished presentation.

## Reproduction

Primary suite:

```bash
python benchmarks/exec_meta_adapt/run_suite.py --output-dir results/deic_cogbench/public_draft_release
```

Ablations only:

```bash
python benchmarks/exec_meta_adapt/run_ablations.py --output-dir results/deic_cogbench/public_draft_release
```

Expected local output bundle:
- `results/deic_cogbench/public_draft_release/package_run.json`
- `results/deic_cogbench/public_draft_release/package_report.md`
- `results/deic_cogbench/public_draft_release/ablations_train.json`

Reproducibility notes:
- splits are frozen by seed in the YAML split files
- outputs are written outside committed source paths
- held-out transfer is explicit rather than mixed into the train split

## Public Draft Release Note

DEIC-CogBench v1 is a public-draft benchmark package for a bounded cognitive subsystem built around executive function, metacognition, adaptive learning under partial observability, and safety-aware abstention. The package includes three domains, an explicit held-out transfer split, runnable ablations, auditable traces, and first-class safety metrics such as silent failure and false adaptation. This is not a claim of AGI. It is a reproducible evaluation surface for a frozen DEIC platform that makes its successes, abstentions, and failure modes legible to other researchers.
