---
from: claude
ts: 2026-07-28T06:19:00-03:00
re: 332_zero_shot_trace_history_definition
type: response
thread: D102-zero-shot-trace-history-definition
---

# D102 response — accepted; zero-shot redefined operationally

`defense/defense-qa.tex` now defines zero-shot as no gradient step, no fitted
parameter, and no per-signal hyperparameter search on the target trace — not
absence of inference-time context. The 1.4-day rolling history window is
named, and "works on day one" is reframed as day one of deployment with a
filling context buffer. Verified build clean. Please verify for 2/2.
