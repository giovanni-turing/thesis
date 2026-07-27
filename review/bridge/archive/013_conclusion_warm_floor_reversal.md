---
from: reviewer
ts: 2026-07-26T21:08:00-03:00
re: 009_rereview_request
type: finding
thread: D04-warm-floor-cost-reversal
---

## Major — the conclusion reverses the measured warm-floor cost ordering

`tex/conclusion.tex:112-117` correctly cites the warm-pool `M=2` arm at
`0.746x` static, then prescribes: "Stand a fixed floor; a forecast adds cost,
not compliance." The cited arm is not a fixed floor alone: it is the reactive
controller plus a minimum floor under warm-pool readiness
(`simulation/results/comparator_frontier/frontier_summary.json:976-999`).
More importantly, the equal-readiness forecast costs `0.6231x`, not more
(`frontier_summary.json:1200-1206`).

The direct operands are:

```
reactive_warmpool_M2 = 2,886,614.5 worker-s
forecast             = 2,410,754.7 worker-s
ratio                 = 2,886,614.5 / 2,410,754.7 = 1.19739
forecast saving       = 1 - 2,410,754.7 / 2,886,614.5 = 16.48%
```

The artifact itself states that no floor reaches forecast cost
(`frontier_summary.json:1243-1251`). Thus the measured instance supports
"a warm-floor reactive can pass and may be operationally simpler, but costs
1.20x the forecast in measured worker-time." It does not support "forecast
adds cost." The categorical follow-on at `tex/conclusion.tex:135-142` inherits
the same reversal.

