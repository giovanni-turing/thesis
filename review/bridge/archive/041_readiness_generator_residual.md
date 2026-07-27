---
from: reviewer
ts: 2026-07-26T21:39:15-03:00
re: new
type: finding
thread: D19-readiness-generator-residual
---

## Major provenance/cross-section residue — canonical outputs still call the nonidentical strict pairing symmetric

`make_frontier_report.py:289-306,371-373` still labels the forecast
165-second-hold variant and reactive trailing-window variant "both arms under
strict re-warm (symmetric)" and uses that pair to construct the
`defensible_range_x` upper endpoint. The generated artifact repeats this at
`frontier_summary.json:1190-1220,1240-1248`. The figure generator labels panel
B "readiness models equalised" while plotting that nonidentical strict
forecast variant beside the warm-pool family
(`make_frontier_report.py:537-565`).

The Chapter 6 frontier setup also still says all five arms use "identical
mechanics" (`tex/closedloop.tex:473-482`), contradicting its own corrected
readiness caveat at `tex/closedloop.tex:585-605`.

The current promoted 1.20x claim is defensible. The generator, JSON, figure
label, and setup paragraph must be aligned so regeneration cannot restore the
rejected symmetric-strict/fully-equalized interpretation.
