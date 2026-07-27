---
from: reviewer
ts: 2026-07-26T21:08:07-03:00
re: 009_rereview_request
type: finding
thread: D11-readiness-not-equalized
---

## Major — the strict-readiness endpoint is not equalized between forecast and reactive

The chapter and conclusion say readiness is equalized in both directions and
use the resulting `1.20--1.69x` interval
(`tex/closedloop.tex:539-548,570-583`;
`tex/conclusion.tex:45-55`). The warm-pool direction is algorithmically
symmetric, but the strict direction is not.

Reactive strict readiness requires the desired level to survive the entire
trailing lead window:

```
avail_i = min(desired[i-lead_bins : i+1])
```

(`simulation/forecast_schedule.py:135-150`).

Forecast `--strict-rewarm`, however, retains every matured order as freely
reusable for `165 s`, even after billed capacity scales down; only after that
hold expires must it reorder
(`verification/scripts/forecast_schedule_issuetime.py:69-77,122-162`).
That is a finite free warm pool, not the reactive arm's strict re-warm
semantics.

Consequently the `1.689x` endpoint
(`frontier_summary.json:1190-1197`) is not from two arms under the same strict
physical model. The symmetric warm-pool result, `1.197x`
(`frontier_summary.json:1200-1206`), stands. The upper endpoint requires a
shared strict implementation and rerun; otherwise the text must stop calling
that direction equalized and cannot use it to support the full
`1.20--1.69x` readiness-robust range.

