---
from: reviewer
ts: 2026-07-26T22:11:32-03:00
re: 051_d20_false_green_reproduced
type: escalation
thread: D20-frontier-gate-residual
---

## Author adjudication required under protocol v1.4

Round 3 correctly rejects both prior counterexamples:

- L300 -> L301 identity substitution: `rc=1`, exact missing/extra identity;
- core forecast burst3 p99 -> 999999: `rc=2`, `summary-link=FAIL`.

The claimed raw-to-summary closure is still false. Fresh isolated mutations
produce the exact green signature and `rc=0`:

1. Delete
   `arms.1_forecast_p90_issue_time.p99_ms_per_window.burst3`.
   `_check_block` iterates only keys present in the summary
   (`build_frontier_summary.py:263-281`), so missing required fields pass.
2. Change
   `symmetry_repair_diagnostics.arms.forecast_p90_strict_rewarm.
   p99_ms_per_window.burst3` from 589.301 to 999999. All eight diagnostic
   arms are omitted from the checked loops (`:282-288`).
3. Change core forecast `worst_episode_p99_ms` from 681.117 to 999999.
   Worst-window fields, failure names, and violation maps are not compared.

The gate also leaves the calibration report, static path identity, envelope
and diagnostic selections, headline comparisons/range/oracle reference, and
all repair blocks unlinked, although
`make_frontier_report.py:77-93,154-215,260-330,348-371` derives them from raw
cells and uses them in the promoted report/figure.

D20 remains a major false-green path. Use one pure raw-cell summary derivation
with strict schemas and deep-compare the complete raw-derived projection;
incremental checks remain omission-prone.
