# Demo Upgrade Roadmap

Goal: turn DEIC from a deep research repository into an interactive simulator that shows belief updates, source trust, query budget, and commit/abstain/escalate decisions.

## Current State

- GitHub Pages surface is live.
- README documents the system architecture, benchmark layers, and results.
- Core code and tests are already organized around reproducible research artifacts.

## Highest-Impact Improvements

| Priority | Upgrade | Recruiter value |
| --- | --- | --- |
| P0 | Add a small simulator with one hidden-state task and step-by-step observations. | Makes the reasoning system tangible. |
| P0 | Visualize belief mass and trust changes after each observation. | Shows the core idea faster than prose. |
| P1 | Add controls for query budget, source reliability, and contradiction rate. | Demonstrates bounded reasoning and robustness. |
| P1 | Add sample transcripts for commit, abstain, and escalate outcomes. | Makes safety-aware behavior inspectable. |
| P2 | Add a hosted Streamlit or static JS version using fixture data. | Converts research into a clickable product surface. |

## Suggested Demo Shape

- Option A: Streamlit simulator using existing task fixtures.
- Option B: Static GitHub Pages simulator with precomputed state traces.
- Option C: Notebook-backed demo for deeper research review.

## Definition Of Done

- Reviewer can manipulate one scenario and watch belief/trust state change.
- Demo has at least three curated scenarios: ordinary uncertainty, trusted contradiction, and sufficient evidence.
- README links to the simulator and explains what to look for in under one minute.
