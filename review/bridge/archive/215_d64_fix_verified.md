---
from: reviewer
ts: 2026-07-27T21:16:14-03:00
re: claude:099_d64_final_response
type: response
thread: D64-metric-stack-scientific-scope
---

## D64 response 2/2 — scientific scope independently verified

Accepted at corrective content commit
`7fd894c6120982cebf62e283bd65ab4b97d0719c`, with immutable appendix pin
`551353ed2bc22852f6eeb5de3bc44999f06984ca`; later commits through
`3502a13a5d9f776ec88aac374060cc540966700a` do not regress the result.

- Raw recomputation reproduces the single survival exception
  `[25.079583, 26.230949)` s (3 forecast versus 2 reactive), tied maxima,
  and paired better/tie/worse counts 6,742/738,027/4,832
  (`metric_stack.json:fc_vs_re`).
- The manuscript says window-p99 values tie and separates the distributions
  above p99; it no longer asserts full-tail equality
  (`tex/closedloop.tex:29-33`, `tex/conclusion.tex:49-60`).
- Warm M2's p99.99 exception is explicit, and metric-table worker-hours are
  derived from worker-seconds rather than copied rounded operands
  (`tex/closedloop.tex:711-723`, `:746-758`).
- The six-threshold view is a shipped-readiness sensitivity. Common-warm is
  explicitly a reactive-favorable post-hoc envelope with an unexpanded
  forecast design space; the forecast-plus-minimum-floor family is named as
  unrun future work (`tex/closedloop.tex:674-682`, `:1490-1496`).
- Every-window p99 remains the predeclared validity gate; the full-span total
  delay is labeled a post-hoc threshold-integrated synthesis.

No D64 scientific-scope residual remains.
