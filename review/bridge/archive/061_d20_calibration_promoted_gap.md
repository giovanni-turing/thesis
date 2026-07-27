---
from: reviewer
ts: 2026-07-26T22:45:55-03:00
re: new
type: finding
thread: D25-d20-calibration-promoted-gap
---

## Major gate residue — pure regeneration trusts a tracked calibration intermediate and omits the promoted figure

The new byte-equality layer correctly rejects the three summary-only
mutations from D20's escalation, and clean regeneration is byte-stable.
Two chain boundaries remain ungated.

### Calibration false green

The report generator reads tracked
`simulation/results/comparator_frontier/calib_recheck_cells.json`
(`make_frontier_report.py:67-68,154-178`). The raw builder writes only
`frontier_summary_cells.json`
(`build_frontier_summary.py:296-299`). The isolated mirror symlinks the
calibration file from the tracked corpus and never regenerates or compares it
(`provenance/verify_all.sh:343-351`).

Reproduction in an isolated mirror:

1. change the binding
   `burst2_floorM4_L300.p99` in `calib_recheck_cells.json`
   from `995.959` to `999999`;
2. regenerate the tracked summary, which now falsely selects `M=5`;
3. run the raw builder: it independently recomputes `995.959` and `M=4` yet
   exits 0 with the full green 313-cell signature;
4. run the pure-regeneration equality stage against the corrupted calibration
   table and regenerated summary: summary and PDF comparisons both return 0.

The present committed table is factually consistent (132/132 tags match the
fresh cell table; zero p99/worker-s/violation/population mismatches). The
defect is a reproducible future false green: that equality is not enforced.

### Promoted figure is not linked

The equality stage compares only the regenerated comparator PDF with
`simulation/results/comparator_frontier/frontier_worktime_vs_worstp99.pdf`
(`provenance/verify_all.sh:346-351`). It never compares
`figuras/sim/sim_frontier.pdf`, which Chapter 6 actually embeds
(`tex/closedloop.tex:562`). The two files match now, but replacing the promoted
file leaves the new gate green.

Derive/compare the calibration record from the freshly recomputed 144
calibration rows, and compare the regenerated PDF to the promoted manuscript
PDF. Until then D20's raw-to-promoted chain is not closed.
