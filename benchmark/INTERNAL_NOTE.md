# Internal Engineering Note

**Date:** 2026-04-01
**Subject:** Continuous vs. Discrete Representation Mismatch on C6

For hidden discrete structure under tight budgets, our current continuous
active-inference core (True_AGI_Core / HierarchicalActiveInferenceNetwork)
underperforms discrete latent inference and can degrade it when hybridized.

Specifically:
- Continuous core alone on C6: 0.0% accuracy (N=100)
- Discrete hypothesis solver on C6: 36–37% accuracy (N=100)
- Hybrid (discrete front-end feeding continuous core): 8.0% accuracy (N=100)

The continuous core's variational updates smooth discrete combinatorial
states into real-valued approximations that fail the environment's exact
integer consensus checks. When correct discrete structure is injected
upstream, the continuous back-end actively destroys the signal.

**Engineering decision:** Freeze the continuous core for this benchmark line.
Do not attempt further hybrid integration or fine-tuning of perception.py
for C6. Future progress requires either a native discrete solver track or
a fundamentally different continuous architecture with discrete inductive
biases.
