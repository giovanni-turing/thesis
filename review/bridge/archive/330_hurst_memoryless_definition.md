---
from: reviewer
ts: 2026-07-28T05:17:10-03:00
re: new
type: finding
thread: D100-hurst-memoryless-definition
---

# D100 — $H=0.5$ does not imply a memoryless process

The new theory section defines $H=0.5$ as “a memoryless process”
(`defense/defense-qa.tex:2013-2015`). That is scientifically too strong.
$H=0.5$ is the no-long-range-dependence scaling benchmark; it does not imply
the Markov/memoryless property. Short-range-dependent processes, including
ordinary stationary ARMA processes, can have $H=0.5$ while retaining finite-lag
dependence.

This thesis's own $H$ is only a spectral-slope-derived persistence proxy
(`tex/trace-eda.tex:187-205`), explicitly described as one endpoint-sensitive
estimator rather than an independent Hurst measurement
(`tex/trace-eda.tex:273-283`). It cannot establish or exclude memorylessness.

Please replace “memoryless process” with “no-long-range-dependence benchmark”
or “short-memory benchmark.” The neighboring caveats about the single
spectral estimator should remain.
