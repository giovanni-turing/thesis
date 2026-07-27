---
from: reviewer
ts: 2026-07-26T23:38:02-03:00
re: new
type: finding
thread: D32-burst5-lower-bound-resurrected
---

## HIGH — the new burst5 dagger resurrects a superseded divergence interpretation

`tex/closedloop.tex:929-932` says the 501-image queue makes burst5/static's
composed p99 “a lower bound ... not a settled tail.” That is contradicted by
both the producer and the repository's adjudicated correction.

Producer semantics:

- `workload/trace_to_two_pool.py:91-100` defines `queue_divergent` as a
  queue-at-the-**end-of-arrivals** heuristic and explicitly says a finite
  window subsequently drains.
- `:303-339` computes a finish time for every included request.
- `:517-521` sets the simulation end to the last finish and builds the series
  through that drain tail.

Artifact evidence:

```text
simulation/results/composed_fill/burst5_static_C8.jsonl.stats.json:17-18
arrival horizon = 4857.936 s; vision simulation end = 4858.322 s

:60-61
queue at arrival end = 501; heuristic flag = true

simulation/results/composed_fill/burst5_static.report.json:2,33
completed_requests = num_requests = 8983
```

The final series bins, derived with

```text
jq '.series[-2:]' burst5_static_C8.series.json
```

are:

```text
t=4857: queue=501, busy=8
t=4858: queue=0,   busy=0
```

The remaining queue drains in 0.386 s and every request contributing to the
composed percentile is complete. The 1471.0-ms result is therefore the settled
p99 of the declared finite population; only extrapolation beyond the window is
unknown.

Most decisively, `provenance/schema/10_residual.sql:668-677` and `:713-731`
record the author-approved burst5 correction: this exact boundary backlog was
an endpoint artifact, a threefold tiled replay was stable at every `C >= 8`,
and the honest C8 p99 knee superseded the old divergence gate. The new dagger
reverses that adjudication and also conflicts with `tex/closedloop.tex:881-887`
within the same ledger section.

Remove the lower-bound/unsettled-tail claim. The raw heuristic flag may be
reported only with its boundary-artifact interpretation.
