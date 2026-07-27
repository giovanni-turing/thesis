---
from: reviewer
ts: 2026-07-26T21:39:14-03:00
re: new
type: finding
thread: D18-oracle-generator-residual
---

## Major provenance residue — the canonical report generator regenerates the rejected oracle-bound claim

The manuscript now says "reference," but
`simulation/results/comparator_frontier/make_frontier_report.py:307-327`
still emits the keys/claims `oracle_bound`, "honest signal-quality bound," and
`fraction_of_achievable_saving_captured_by_forecast`; its verdict again calls
the oracle "the honest bound" (`make_frontier_report.py:381-384`).
The current generated artifact retains those exact claims
(`frontier_summary.json:1222-1237,1240-1245`).

In addition, Chapter 6 says the oracle uses the "same fixed point conversion
and mechanics" (`tex/closedloop.tex:609-612`), while the selected oracle is
H=0 and the other frozen arms use three-minute hysteresis
(`FROZEN.json:15-27,59-74`). "Same fixed conversion" is supported; "same
mechanics" is not.

Regenerating the canonical report would therefore restore the D09
interpretation just removed from the thesis. Rename/reframe the generator and
artifact fields as a perfect-information fixed-conversion reference and a
measured gap, then regenerate; narrow the Chapter 6 sentence to the mechanics
actually shared.
