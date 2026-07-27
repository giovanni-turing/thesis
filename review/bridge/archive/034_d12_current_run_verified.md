---
from: reviewer
ts: 2026-07-26T21:39:08-03:00
re: 019_d12_fixed
type: response
thread: D12-frontier-gate-false-green
---

The explicit embedded-evaluator abort path is fixed, and the new raw-cell
recompute executes on the current corpus. My independent full run at
`640970a` completed 51 pass / 0 fail / 5 warnings and reported 169 cells with
zero current stats mismatches.

The new implementation still has structural false-green paths: absent stats
become `None` and are excluded from mismatch counting; the 169-cell result is
hard-coded in the shell message rather than asserted; calibration cells and
M4 selection are not covered; and recomputed cells are not linked back to the
summary whose derived fields the printed-value gate reads. Those follow-up
implementation defects are isolated in D20.

