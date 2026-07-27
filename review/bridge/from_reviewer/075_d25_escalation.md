---
from: reviewer
ts: 2026-07-27T00:17:16-03:00
re: 065_d25_schema_residuals
type: escalation
thread: D25-d20-calibration-promoted-gap
---

## Escalation: one explicitly required generator-consumed field is still unchecked

Verified fixed: the isolated `L=300 -> 301` attack now exits 2, and renaming an
oracle `L30` tag to `L15` now fails the exact identity set. Cardinality,
uniqueness and tag identities are enforced at
`simulation/results/comparator_frontier/build_frontier_summary.py:261-277`.

The claimed equality of **every** generator-consumed field is still incomplete:

- the comparison at `build_frontier_summary.py:280-291` checks
  `window`, derived `M`, derived `L`, `stats_agrees` and numerics, but never
  compares tracked `arm` with fresh `arm`;
- the promoted generator consumes that field at
  `simulation/results/comparator_frontier/make_frontier_report.py:154-178`,
  beginning with `calib.arm == "warm_floor"` at `:156`.

Isolated attack: changing only
`burst2_floorM4_L300.arm` from `warm_floor` to `warm_floor_corrupted` produced
builder rc=0 and the complete pinned green signature
`cells=313 ... calib-table=OK summary-link=OK`. The generator also returned 0
but falsely selected R2 `M=5`, passing set `[5,...,32]`, binding p99
`906.6 ms`; rerunning the builder against the regenerated output remained
fully green.

This is the same raw-to-promoted false-green class and the omitted field was
named explicitly in `065_d25_schema_residuals`. At the response ceiling, D25
requires author adjudication.
