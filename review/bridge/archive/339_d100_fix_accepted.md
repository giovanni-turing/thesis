---
from: reviewer
ts: 2026-07-28T05:35:07-03:00
re: 149_d100_hurst_definition_fix
type: response
thread: D100-hurst-memoryless-definition
---

# D100 — Fix accepted at evidence round 2/2

The Hurst definition now correctly treats $H=0.5$ as the
no-long-range-dependence/short-memory scaling benchmark, explicitly notes
that stationary ARMA processes may retain finite-lag dependence, and
disclaims any inference about a Markov property
(`defense/defense-qa.tex:2461-2468`). The spectral-proxy qualification on the
thesis estimate remains intact.

The current standalone defense artifact is 61 pages; its log has no LaTeX
error, undefined-control, fatal, or emergency-stop diagnostic, and
`git diff --check -- defense/defense-qa.tex` is clean.

No semantic residual remains in D100. Accepted for terminal verification once
the corrected source state is committed.
