# Frontier Local Metacognition Expansion Abstract

We expanded the frozen no-API metacognition benchmark from two to four small open-weight models on the same 40-task task set, with unchanged prompts, parser, and scoring. The resulting comparison shows that the benchmark does not merely reward one generic notion of safe behavior: it separates qualitatively different metacognitive failure modes across models.

In the current expansion, `qwen` and `smollm` show over-escalation collapse, `granite` shows an under-escalation / over-abstention tradeoff, and `tinyllama` serves as a fragility baseline with substantial parse error and bluffing. This makes the benchmark more informative than a single-score ranking because it distinguishes different safety and calibration failures under partial observability.
