# DEIC Research Log: Clinical Transfer & Architectural Hardening
**Date:** 2026-04-06
**Session Focus:** Transfer-Validation (Clinical), Hypothesis Generator Framework (v1.1 - v1.2)

---

## 🔬 Empirical Baseline: Gate 1 (Zero-Change)
**Tag:** `gate1-zero-change-clinical`
**Status:** Frozen result.

**Constraint:** `deic_core/core.py` was UNCHANGED (hardcoded `group_size=4`).
**Environment:** Clinical deterioration (variable group sizes 2–6).

| Parameter | Result | Verdict |
|---|---|---|
| GS=4 episodes | **56.6%** | **MATCH**: Inference logic transfers |
| GS≠4 episodes | **0.0%** | **FAIL**: Structural hypothesis mismatch |
| Overall (B=8) | 10.7% | Failure to generalize |

**Finding:** The inference core (trust, InfoGain, posterior) is domain-agnostic. The hypothesis bank is the hard constraint.

---

## 🔬 Extension Validation: Gate 2 (Variable GS)
**Tag:** `v1.1-deic-transfer-generalization`
**Status:** Success.

**Change:** Minimal backward-compatible update to `initialize_beliefs()` to allow `group_sizes` list.

### Clinical Transfer Accuracy (Budget=8)
- **Overall:** 26.2% (+15.5pp)
- **GS=4:** 26.5% (-30.1pp) — cost of larger hypothesis space
- **GS=6:** 48.4%
- **GS≠4 average:** ~26.1% (recovered from 0%)

### Budget Scaling (Clinical)
| Budget | Gate 1 (0.0% gs!=4) | Gate 2 (variable gs) |
|---|---|---|
| 6 | 3.5% | 6.0% |
| 8 | 10.7% | 25.3% |
| 10 | 16.5% | **63.5%** |
| 12 | 18.0% | **83.2%** |

**Finding:** DEIC scales powerfully once the structural assumption is removed.

---

## 🏗️ Architectural Milestone: v1.2 Hypothesis Framework
**Tag:** `v1.2-deic-hypothesis-framework`
**Status:** Hardened.

**Implementation:** Extracted hypothesis setup from `core.py` into `deic_core/hypothesis.py`.

### Regression Verification (Final Parity)
| Suite | Metric | Result | Target Band | Status |
|---|---|---|---|---|
| **C6 Benchmark** | Budget=8 | **57.0%** | 55-68% | ✅ PASS |
| **C6 Benchmark** | Budget=12 | **93.3%** | 88-98% | ✅ PASS |
| **Cyber Transfer** | Budget=8 | **56.7%** | 45-70% | ✅ PASS |
| **Clinical Transfer** | Budget=12 | **83.0%** | >70% | ✅ PASS |

---

## 🗺️ Roadmap State: 2026-04-06
1.  **DEIC Core** (v1.2): Domain-agnostic inference core. [STABLE]
2.  **Hypothesis Layer**: Domain-specific generators. [STABLE]
3.  **Belief Inspector**: Read-only observability layer. [PLANNED]
4.  **Commit Controller**: Minimal planner (confident-or-wait). [PLANNED]
5.  **Long-term Memory**: Cross-episode prior bias. [PLANNED]

---

**End of Research Log**
