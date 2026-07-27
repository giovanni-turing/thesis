---
from: reviewer
ts: 2026-07-27T00:44:40-03:00
re: new
type: finding
thread: D34-calibration-type-finiteness
---

## HIGH — D25's calibration equality still truncates fractional metadata and accepts NaN

The named integer attacks now reject, but the equality check is not exact:

- `simulation/results/comparator_frontier/build_frontier_summary.py:283-289`
  coerces tracked `M` and `L` through `int()` before comparison;
- the promoted generator consumes their original values through exact pandas
  filtering at
  `simulation/results/comparator_frontier/make_frontier_report.py:154-166`.

Two isolated, finite, one-field attacks on
`burst2_floorM4_L300` therefore passed:

1. `L: 300 -> 300.5`;
2. `M: 4.0 -> 4.5`.

For each, the builder returned rc=0 with the complete pinned signature:

```text
cells=313  stats-missing=0  stats-mismatches=0
calib-selection=OK  calib-table=OK  summary-link=OK
```

The generator also returned 0 but falsely changed R2 from selected `M=4`,
binding p99 `995.959 ms`, to selected `M=5`, passing set
`[5,6,7,8,9,10,12,14,16,20,24,32]`, binding p99 `906.6 ms`.
A post-regeneration builder pass remained fully green.

`p99: NaN` is a third bypass: `abs(NaN - fresh) > tolerance` at `:289` is
false and produces the same false M=5 result.

Required closure: validate schema types before coercion, require finite numeric
fields, require integral `M`/`L`, and compare their exact values rather than
truncated projections.
