"""
DEIC Cross-Episode Memory — Empirical Study
=============================================

Compares Memory OFF vs Memory ON across C6, Cyber, and Clinical domains
under Stationary and Shifted regimes.

────────────────────────────────────────────────────────────────────────
LOCKED COMPARISON INVARIANTS
  - Same 30 seeds for OFF and ON in every condition.
  - Same episode order.
  - Same shift point (episode 15).
  - Same parameter overrides per episode index.

────────────────────────────────────────────────────────────────────────
MEMORY UPDATE POLICY: after successful episodes only.

Rationale: CrossEpisodeMemory.observe_episode_outcome records which
hypothesis (group size, multiplier) was the ground truth. Failed
episodes do not provide verified structural identity, so including
them would inject unverified noise into the prior-bias computation.
The implementation already enforces this: observe_episode_outcome
returns immediately when success=False.

────────────────────────────────────────────────────────────────────────
SHIFTED REGIME DEFINITIONS

  C6:       Episodes 0-14: c6_multiplier = 2.0
            Episodes 15-29: c6_multiplier = 1.2
            Group size = 4 throughout. Group *composition* varies by seed.
            Tests: whether learned multiplier prior hurts after shift.

  Cyber:    Episodes 0-14: severity_multiplier = 2.0
            Episodes 15-29: severity_multiplier = 5.0
            Affected group = 4 services throughout (composition varies by seed).
            Tests: whether learned severity prior hurts under extreme shift.

  Clinical: Episodes 0-14: severity = 1.8, group_size = 4
            Episodes 15-29: severity = 2.5, group_size = 2
            Tests: whether learned group-size AND multiplier priors both
            hurt under a double distribution shift.

────────────────────────────────────────────────────────────────────────
METRICS
  - Accuracy             : fraction of correct episodes
  - Avg Budget Used      : mean total env interactions per episode
  - Avg Commit Step      : mean queries before commit action
  - Escalation Freq      : fraction of episodes where controller escalated
                           (C6 only; cyber/clinical adapters don't expose this)
  - Post-Shift Recovery  : accuracy in first 5 post-shift episodes

────────────────────────────────────────────────────────────────────────
SCOPE
  - No DEIC core changes.
  - No new modules.
  - No benchmark environment changes.
  - Study only.
"""

import sys
import os
import random
from collections import defaultdict

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from deic_core.memory import CrossEpisodeMemory
from benchmark.environment import ProceduralEnvironment, EpisodeConfig
from benchmark.deic_adapter import DEICBenchmarkAdapter
from experiments.cyber_transfer.environment import CyberIncidentEnvironment, CyberEpisodeConfig
from experiments.cyber_transfer.adapter import CyberDEICAdapter
from experiments.clinical_transfer.environment import ClinicalEnvironment, ClinicalEpisodeConfig
from experiments.clinical_transfer.adapter import ClinicalDEICAdapter

# ── Configuration ────────────────────────────────────────────────────

N_EPISODES    = 30
SHIFT_POINT   = 15          # first post-shift episode index
RECOVERY_WIN  = 5           # episodes used to measure recovery speed
SEEDS         = list(range(10000, 10000 + N_EPISODES))

# Per-domain regime parameters
REGIMES = {
    "C6": {
        "stationary": {"multiplier": 2.0},
        "shifted": {
            "pre":  {"multiplier": 2.0},
            "post": {"multiplier": 1.2},
        },
    },
    "Cyber": {
        "stationary": {"severity": 2.0},
        "shifted": {
            "pre":  {"severity": 2.0},
            "post": {"severity": 5.0},
        },
    },
    "Clinical": {
        "stationary": {"severity": 1.8, "group_size": 4},
        "shifted": {
            "pre":  {"severity": 1.8, "group_size": 4},
            "post": {"severity": 2.5, "group_size": 2},
        },
    },
}

# ── Episode runners ──────────────────────────────────────────────────

def _run_c6(seed, params, memory):
    config = EpisodeConfig(seed=seed, condition="c6_hidden_structure")
    config.c6_multiplier = params["multiplier"]
    env = ProceduralEnvironment(config)

    adapter = DEICBenchmarkAdapter(use_controller=True, memory=memory)
    trajectory, result = adapter.solve(env)

    success   = result.get("consensus_reached", False)
    budget    = result.get("budget_used", 0)
    escalated = any(
        e.get("next_action", {}).get("escalated", False) for e in trajectory
    )
    commit_step = max(0, len(trajectory) - 1)   # queries before commit
    true_hyp  = {
        "S": list(config.categories[config.shifted_category]),
        "m": config.c6_multiplier,
    }
    return success, true_hyp, budget, commit_step, escalated


def _run_cyber(seed, params, memory):
    config = CyberEpisodeConfig(seed=seed)
    config.severity_multiplier = params["severity"]
    env = CyberIncidentEnvironment(config)

    adapter = CyberDEICAdapter(use_controller=True, memory=memory)
    result  = adapter.diagnose(env)

    success     = result.get("correct", False)
    queries     = result.get("queries_used", 0)
    commit_step = max(0, queries - 1)
    true_hyp    = {
        "S": list(config.affected_group),
        "m": config.severity_multiplier,
    }
    return success, true_hyp, queries, commit_step, None  # no escalation data


def _run_clinical(seed, params, memory):
    config = ClinicalEpisodeConfig(seed=seed)
    # Override group structure and severity
    gs  = params["group_size"]
    rng = random.Random(seed + 80000)          # deterministic, seed-locked
    pts = list(config.patients)
    rng.shuffle(pts)
    config.deteriorating = pts[:gs]
    config.stable        = pts[gs:]
    config.severity      = params["severity"]

    env     = ClinicalEnvironment(config)
    adapter = ClinicalDEICAdapter(use_controller=True, memory=memory)
    result  = adapter.diagnose(env)

    success     = result.get("correct", False)
    queries     = result.get("queries_used", 0)
    commit_step = max(0, queries - 1)
    true_hyp    = {
        "S": list(config.deteriorating),
        "m": config.severity,
    }
    return success, true_hyp, queries, commit_step, None

RUNNERS = {"C6": _run_c6, "Cyber": _run_cyber, "Clinical": _run_clinical}

# ── Study engine ─────────────────────────────────────────────────────

def run_condition(domain, regime, use_memory):
    """
    Run one full condition (domain × regime × memory flag).
    Returns list of per-episode dicts.
    """
    run_fn     = RUNNERS[domain]
    regime_cfg = REGIMES[domain][regime]
    memory     = CrossEpisodeMemory() if use_memory else None
    rows       = []

    for i, seed in enumerate(SEEDS):
        if regime == "stationary":
            params = regime_cfg
        else:
            params = regime_cfg["pre"] if i < SHIFT_POINT else regime_cfg["post"]

        success, true_hyp, budget, commit_step, esc = run_fn(seed, params, memory)

        # Memory updates after successful episodes only
        if memory is not None:
            memory.observe_episode_outcome({}, success, true_hyp)

        rows.append({
            "ep":          i,
            "seed":        seed,
            "success":     success,
            "budget":      budget,
            "commit_step": commit_step,
            "escalated":   esc,
            "phase":       "pre" if i < SHIFT_POINT else "post",
        })

    return rows


def metrics(rows, label="all"):
    """Aggregate metrics from a list of episode rows."""
    n = len(rows) or 1
    acc        = sum(r["success"] for r in rows) / n
    avg_budget = sum(r["budget"]  for r in rows) / n
    avg_commit = sum(r["commit_step"] for r in rows) / n
    esc_rows   = [r for r in rows if r["escalated"] is not None]
    esc_freq   = (sum(r["escalated"] for r in esc_rows) / len(esc_rows)
                  if esc_rows else None)
    return {
        "label":       label,
        "accuracy":    acc,
        "avg_budget":  avg_budget,
        "avg_commit":  avg_commit,
        "esc_freq":    esc_freq,
    }


def recovery_accuracy(rows):
    """Accuracy in the first RECOVERY_WIN post-shift episodes."""
    post = [r for r in rows if r["phase"] == "post"][:RECOVERY_WIN]
    if not post:
        return None
    return sum(r["success"] for r in post) / len(post)


# ── Reporting ────────────────────────────────────────────────────────

def fmt(v, pct=False):
    if v is None:
        return "N/A"
    return f"{v:.1%}" if pct else f"{v:.2f}"


def print_domain_table(domain, data):
    """Print one compact table for a domain."""
    print(f"\n### {domain}")
    print("| Regime | Condition | Accuracy | Avg Budget | Avg Commit Step | Escalation | Recovery (first 5 post-shift) |")
    print("|--------|-----------|----------|------------|-----------------|------------|-------------------------------|")
    for regime in ("stationary", "shifted"):
        for cond in ("Memory OFF", "Memory ON"):
            m  = data[regime][cond]["metrics"]
            rc = data[regime][cond]["recovery"]
            esc_str = fmt(m["esc_freq"], pct=True)
            rc_str  = fmt(rc, pct=True) if regime == "shifted" else "—"
            print(f"| {regime:<10} | {cond:<11} | {fmt(m['accuracy'], True):<8} "
                  f"| {fmt(m['avg_budget']):<10} | {fmt(m['avg_commit']):<15} "
                  f"| {esc_str:<10} | {rc_str:<29} |")


def print_summary_table(all_data):
    """Print the cross-domain Memory OFF vs ON summary."""
    print("\n## Summary: Memory OFF vs Memory ON")
    print("| Domain | Regime | OFF Acc | ON Acc | Delta | OFF Budget | ON Budget | OFF Recovery | ON Recovery |")
    print("|--------|--------|---------|--------|-------|------------|-----------|--------------|-------------|")
    for domain in ("C6", "Cyber", "Clinical"):
        for regime in ("stationary", "shifted"):
            off = all_data[domain][regime]["Memory OFF"]
            on  = all_data[domain][regime]["Memory ON"]
            delta = on["metrics"]["accuracy"] - off["metrics"]["accuracy"]
            rc_off = fmt(off["recovery"], pct=True) if regime == "shifted" else "—"
            rc_on  = fmt(on["recovery"],  pct=True) if regime == "shifted" else "—"
            print(f"| {domain:<8} | {regime:<10} "
                  f"| {fmt(off['metrics']['accuracy'], True):<7} "
                  f"| {fmt(on['metrics']['accuracy'],  True):<6} "
                  f"| {delta:+.1%} "
                  f"| {fmt(off['metrics']['avg_budget']):<10} "
                  f"| {fmt(on['metrics']['avg_budget']):<9} "
                  f"| {rc_off:<12} | {rc_on:<11} |")


def print_verdict(all_data):
    """One short technical verdict."""
    print("\n## Technical Verdict")

    # (a) stationary benefit
    stat_deltas = []
    for d in ("C6", "Cyber", "Clinical"):
        off = all_data[d]["stationary"]["Memory OFF"]["metrics"]["accuracy"]
        on  = all_data[d]["stationary"]["Memory ON"]["metrics"]["accuracy"]
        stat_deltas.append(on - off)
    avg_stat = sum(stat_deltas) / len(stat_deltas)

    if avg_stat > 0.02:
        a = f"YES — average accuracy lift of {avg_stat:+.1%} across domains."
    elif avg_stat >= -0.02:
        a = f"NEUTRAL — average delta of {avg_stat:+.1%}; within noise."
    else:
        a = f"NO — average accuracy drop of {avg_stat:+.1%}."

    # (b) shifted harm
    shift_deltas = []
    for d in ("C6", "Cyber", "Clinical"):
        off = all_data[d]["shifted"]["Memory OFF"]["metrics"]["accuracy"]
        on  = all_data[d]["shifted"]["Memory ON"]["metrics"]["accuracy"]
        shift_deltas.append(on - off)
    avg_shift = sum(shift_deltas) / len(shift_deltas)

    if avg_shift < -0.05:
        b = f"YES — average accuracy drop of {avg_shift:+.1%} under shift."
    elif avg_shift <= 0.05:
        b = f"NO — average delta of {avg_shift:+.1%}; memory does not measurably hurt."
    else:
        b = f"NO — surprisingly, memory helps even under shift ({avg_shift:+.1%})."

    # (c) recommendation
    if avg_stat > 0.02 and avg_shift >= -0.05:
        c = "OPTIONAL-ON — memory provides benefit and does not hurt under shift. Ship as opt-in default-on."
    elif avg_stat > 0.02 and avg_shift < -0.05:
        c = "OPTIONAL-OFF — memory helps in stationary but hurts under shift. Ship as opt-in default-off with reset-on-shift heuristic."
    elif avg_stat <= 0.02 and avg_shift >= -0.05:
        c = "DEFAULT-OFF — memory provides no significant benefit. Keep implemented but disabled."
    else:
        c = "DEFAULT-OFF — memory provides no benefit and may hurt. Keep disabled."

    print(f"\n**(a) Does memory help in stationary settings?**\n  {a}\n")
    print(f"**(b) Does memory hurt under distribution shift?**\n  {b}\n")
    print(f"**(c) Recommendation: default-off, optional, or standard?**\n  {c}\n")


# ── Main ─────────────────────────────────────────────────────────────

def main():
    print("# DEIC Cross-Episode Memory — Empirical Study")
    print()
    print(f"- Episodes per condition: {N_EPISODES}")
    print(f"- Shift point: episode {SHIFT_POINT}")
    print(f"- Seeds: {SEEDS[0]}–{SEEDS[-1]} (locked across OFF/ON)")
    print(f"- Memory update policy: **after successful episodes only**")
    print(f"- Controller: enabled (use_controller=True)")
    print()

    all_data = {}

    for domain in ("C6", "Cyber", "Clinical"):
        domain_data = {}
        for regime in ("stationary", "shifted"):
            regime_data = {}
            for use_mem, label in [(False, "Memory OFF"), (True, "Memory ON")]:
                rows = run_condition(domain, regime, use_mem)
                regime_data[label] = {
                    "metrics":  metrics(rows),
                    "recovery": recovery_accuracy(rows) if regime == "shifted" else None,
                    "rows":     rows,
                }
            domain_data[regime] = regime_data
        all_data[domain] = domain_data

    # ── Per-domain tables ────────────────────────────────────────────
    for domain in ("C6", "Cyber", "Clinical"):
        print_domain_table(domain, all_data[domain])

    # ── Summary table ────────────────────────────────────────────────
    print_summary_table(all_data)

    # ── Verdict ──────────────────────────────────────────────────────
    print_verdict(all_data)


if __name__ == "__main__":
    main()
