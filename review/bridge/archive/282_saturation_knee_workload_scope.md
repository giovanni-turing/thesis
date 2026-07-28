---
from: reviewer
ts: 2026-07-28T04:01:47-03:00
re: new
type: finding
thread: D91-saturation-knee-workload-scope
---

# D91 — “Order-of-magnitude knees” loses its steady-head population

Both abstracts and the conclusion promote that the pools' saturation knees
sit an order of magnitude apart without naming the workload
(`tex/tese.tex:83-85`; `tex/tese.tex:168-170`;
`tex/conclusion.tex:20-23`).

The measured greater-than-10x separation exists on the 2,000-request
**steady head**: the calibrated language knee is $s=2$, while vision remains
uncrossed through $s=32$ (`tex/metodologia.tex:451-489`;
`tex/metodologia.tex:511-516`). On the burst window, both calibrated pools
are already over their respective bounds at $s=1$
(`tex/metodologia.tex:486-489`; `tex/metodologia.tex:523-540`).

Please qualify the promoted claim as “on the steady head” or “in calm
traffic,” and keep the burst result separate: both pools fail there, through
different mechanisms. Without the population qualifier, the summary reads as
a workload-invariant saturation separation that the sweep explicitly does
not show.
