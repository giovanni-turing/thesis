---
from: reviewer
ts: 2026-07-26T21:08:05-03:00
re: 009_rereview_request
type: finding
thread: D09-oracle-bound-overclaim
---

## Major — `0.292x` is a perfect-information reference, not a lower bound on achievable worker-time

The thesis calls the oracle a bound on "what any forecast could buy" and says
the forecast captures 53% of the "achievable saving"
(`tex/closedloop.tex:57-61,587-592`; repeated at
`tex/conclusion.tex:52-58`, `tex/tese.tex:84-95`, and
`tex/closedloop.tex:1251-1257`).

The frozen artifact states the narrower scope: it bounds the signal-quality
axis under the same point conversion, not the headroom axis
(`simulation/results/comparator_frontier/FROZEN.json:59-75`). The implementation
does not minimize worker-time subject to p99 `<1 s`; it maps true per-bin image
rate through `ceil(rate/rho)`, then applies fixed readiness/hysteresis mechanics
(`simulation/comparator_frontier_oracle.py:100-142`). Because the gate permits
some queueing and tail violations below the one-percent cutoff, a deliberately
biased or SLA-optimized schedule could use less capacity than this zero-error
point mapping and still pass. The selected oracle also uses `H=0`, whereas the
other arms use the frozen three-minute scale-down hysteresis
(`FROZEN.json:15-27,59-74`).

The arithmetic is fine:

```
(1 - 0.62305) / (1 - 0.29213) = 0.5325
```

but its defensible interpretation is "53% of the measured saving gap to this
perfect-information, fixed-conversion reference," not 53% of all achievable
saving. Establishing a true lower bound would require solving the
SLA-constrained cost optimization problem over the admissible policy class.

