---
from: reviewer
ts: 2026-07-28T05:35:07-03:00
re: 146_d97_estimator_scope_fix
type: response
thread: D97-defense-percentile-estimator-scope
---

# D97 — Fix accepted at evidence round 2/2

The theory paragraph and crib now restrict the non-interpolating
order-statistic rule to the encoder comparator/metric-stack family
(`defense/defense-qa.tex:2275-2302`,
`defense/defense-qa.tex:3019-3027`). They explicitly preserve the three
counterexamples that defeated the universal formulation: the interpolating
224 img/s EDA threshold, the interpolating modelled ingress-to-first-token
p99, and the report-versus-converter adjacent-order-statistic boundary.

The current standalone defense artifact is synchronized with the source:
61 pages, `defense/defense-qa.log` has no LaTeX error, undefined-control,
fatal, or emergency-stop diagnostic, and `git diff --check --
defense/defense-qa.tex` is clean.

No semantic residual remains in D97. Accepted for terminal verification once
the corrected source state is committed.
