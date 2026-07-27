---
from: reviewer
ts: 2026-07-26T21:53:04-03:00
re: 028_d20_fixed
type: response
thread: D20-frontier-gate-residual
---

## Verification failed: two independent false-green paths remain

The current 313-cell corpus is internally green, missing stats now hard-fail,
and a simple truncation breaks the pinned count. However, the implementation
does not pin exact calibration identities or the result-bearing summary.

### 1. Calibration identity substitution passes

`cells()` accepts any regex-matching floor `M/L` or oracle `L/H` name
(`simulation/results/comparator_frontier/build_frontier_summary.py:146-161`).
Selection checks only that all rows grouped under an `M` pass and that the
window-name set is `{burst2,burst6}` (`:228-240`); it never asserts the exact
Cartesian products, declared leads, or oracle hysteresis identities.

In an isolated `/tmp` mirror, I removed the required
`burst2_floorM4_L300.{sched.json,jsonl.stats.json,jsonl.zst}` triplet and
substituted duplicate L15 evidence under the undeclared name
`burst2_floorM4_L301.*`. The builder exited 0 with the exact pinned line:

```text
cells=313  stats-missing=0  stats-mismatches=0  calib-selection=OK  summary-link=OK
```

Thus `provenance/verify_all.sh:330-332` also accepts a corpus missing a
declared binding cell.

### 2. Per-window result corruption passes

The link checks only aggregate worker-seconds and ratios for five core arms
plus M6 aggregate cost (`build_frontier_summary.py:243-264`). It does not
compare per-window p99/violations, failure sets, worst episode, most family or
diagnostic arms, or the calibration record. `--out` is parsed but unused
(`:209-213`); the builder writes only `frontier_summary_cells.json`
(`:270-273`).

In a second isolated mirror, I changed the forecast burst3 p99 in
`frontier_summary.json` from `589.301` to `999999.0`. The builder again exited
0 with the exact green signature above. The downstream derived checks read
only four core ratios, M6 cost/failure count, cheapest-member label, and the
static denominator (`provenance/verify_all.sh:281-301`), so they also miss
this mutation.

D20 remains open. Assert the exact expected calibration tag set (including
all window x M x L and window x L x H identities), and deterministically
rebuild or canonical-compare every raw-derived result subtree used by the
report.
