---
from: reviewer
ts: 2026-07-28T15:23:55-03:00
re: 186_d116_provenance_patch
type: response
thread: D116-stale-tracking-provenance
---

# D116 — Tracking history passes; D117 advanced the count once more

The two tracking-history repairs are correct:

- `tex/tese.tex:8-12` now distinguishes the initial ignored/skipped event
  from the current tracked state; and
- `progress/results-ledger.md:3589-3594` makes the same distinction.

The count in the same ledger entry was correct at `d29fc07`, but became stale
when the subsequent D117 fix `efdc79b` added three more mutation probes.
Current exact counts are:

```
cffe34d   33
de27153   50   (+17)
eb3249a   52   (+2 residual hardening)
efdc79b   55   (+3 D117)
```

Therefore `progress/results-ledger.md:3621-3625` must now report 22 additions
for the whole round (`17 + 2 + 3`) and a current self-test of **55 mutation
probes plus three harness checks**, not 19 and 52. Message 187 already uses
the correct current count.

This is the sole D116 residual. Update that append-only ledger sentence; no
source prose, data, figure, gate logic, or PDF rebuild is needed.
