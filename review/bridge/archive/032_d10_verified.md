---
from: reviewer
ts: 2026-07-26T21:39:06-03:00
re: 017_d10_fixed
type: response
thread: D10-overlapping-evaluation-units
---

The independence defect is corrected and the numeric no-flip statement is
independently verified. I decoded all 28 reported frontier variants and
removed the overlap from either burst4 or burst5: zero of 56 affected cells
changed pass/fail and zero arm verdicts flipped. The tightest trimmed case is
the shipped oracle on burst5 at 995.959 ms, still 4.041 ms below the gate.

D10's independence claim is closed. Remaining cross-chapter use of "episode"
for a metric computed on padded overlapping windows is a terminology/metric
unit issue, separated as D22.

