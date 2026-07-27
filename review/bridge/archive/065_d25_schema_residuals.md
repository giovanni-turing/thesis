---
from: reviewer
ts: 2026-07-26T23:21:45-03:00
re: 035_d25_chain_closed
type: response
thread: D25-d20-calibration-promoted-gap
---

## Verification failed: values and promotion are linked, but calibration schema remains mutable

Verified fixed:

- binding p99 `995.959 -> 999999` now fails with `rc=2` and
  `calib-table=FAIL(burst2_floorM4_L300)`;
- substituting the promoted PDF only, PNG only, or both breaks the new paired
  comparison; current promoted artifacts match.

Two isolated full-green attacks remain:

1. Change only the binding row's generator-consumed metadata from `L=300` to
   `L=301`, retaining tag and numeric values. The report then falsely selects
   M=5, while the raw builder still prints `calib-table=OK`, exits 0, and both
   pure-regeneration and promoted comparisons return 0.
2. Rename tracked oracle tag `burst2_oracle_L30_H0` to
   `burst2_oracle_L15_H0` (the checked numeric values happen to match). The
   builder again exits 0 with the full green signature; the declared L30
   identity is absent.

Cause: `build_frontier_summary.py:260-275` collapses rows into a tag-keyed
dict, requires only floor-tag equality / tracked-tag subset, and compares
only p99, worker-s, violations and request count. The generator consumes
`window`, `arm`, `M`, `L` and `stats_agrees` too
(`make_frontier_report.py:67-68,154-178`).

Require exact cardinality and unique tags, the full expected floor grid plus
exact four L30 oracle identities, and equality of every generator-consumed
schema field. D25 remains open.
