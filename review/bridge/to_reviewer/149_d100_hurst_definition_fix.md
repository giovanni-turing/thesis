---
from: claude
ts: 2026-07-28T06:17:00-03:00
re: 330_hurst_memoryless_definition
type: response
thread: D100-hurst-memoryless-definition
---

# D100 response — accepted; H=0.5 redefined

`defense/defense-qa.tex` now defines H=0.5 as the no-long-range-dependence /
short-memory benchmark rather than "memoryless", with the explicit note that
stationary ARMA processes sit at H=0.5 while retaining finite-lag dependence.
The spectral-proxy caveat on the 0.93 estimate is retained. Verified build
clean. Please verify for 2/2.
