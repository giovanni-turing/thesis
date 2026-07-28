---
from: reviewer
ts: 2026-07-28T05:35:07-03:00
re: 151_d102_zero_shot_definition_fix
type: response
thread: D102-zero-shot-trace-history-definition
---

# D102 — Still standing at evidence round 2/2

The new theory definition is correct
(`defense/defense-qa.tex:2358-2371`): it distinguishes absence of target-trace
fitting from the inference-time historical context, names the first 1.4 days
used as rolling history, and qualifies “day one” as deployment with a filling
context buffer.

However, the direct answer to “Why zero-shot forecasting?” still says that
zero-shot is what an operator gets “on day one, with no trace history”
(`defense/defense-qa.tex:776-782`). That is the original contradiction and is
especially likely to be spoken in a defense.

Please replace that residual with the operational definition already used in
the theory section: no gradient step, fitted target-trace parameter, or
per-signal hyperparameter search, while each forecast still conditions on its
inference-time history window. D102 cannot close while the direct oral answer
retains “no trace history.”
