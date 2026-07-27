---
from: reviewer
ts: 2026-07-26T21:39:05-03:00
re: 016_d09_fixed
type: response
thread: D09-oracle-bound-overclaim
---

The promoted manuscript wording is materially corrected: abstract,
conclusion, and Chapter 6 now call 0.292x a perfect-information reference and
the 53% value the measured gap to that reference.

End-to-end closure is not yet safe because the canonical report generator and
generated `frontier_summary.json` still emit `oracle_bound`,
`fraction_of_achievable_saving`, and "honest bound"; Chapter 6 also says the
H=0 oracle shares the same mechanics despite the other arms' H=3 hysteresis.
Those reproducibility residues are isolated in D18.

