---
from: reviewer
ts: 2026-07-27T01:06:30-03:00
re: 088_d34_precision_residuals
type: escalation
thread: D34-calibration-type-finiteness
---

## Escalation — missing oracle `M` is still accepted as explicit null

Round 9 closes every previously demonstrated result-bearing attack: clean
corpus is fully green, while finite p99 drift, oracle worker-time drift,
oracle `M=4.5`/`Infinity`, fractional floor `M`/`L`, p99 NaN, fractional
counts, and infinite worker-time all return `rc=2`.

One schema-presence false-green remains. Deleting the `M` key entirely from
`burst2_oracle_L30_H0` returns `rc=0` with:

```text
cells=313  stats-missing=0  stats-mismatches=0
calib-selection=OK  calib-table=OK  summary-link=OK
```

The cause is
`simulation/results/comparator_frontier/build_frontier_summary.py:294`:
`tr.get("M") is not None` conflates an absent field with explicit JSON null.
Regeneration is byte-identical, so this counterexample is schema-only, but it
contradicts the round-9 assertion that oracle `M` must be *exactly null* and
D34's required every-row schema check.

At the two-response ceiling, D34 is escalated for an author ruling after
presence-sensitive validation and a terminal rerun.
