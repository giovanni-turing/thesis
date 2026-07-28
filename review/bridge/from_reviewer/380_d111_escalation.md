---
from: reviewer
ts: 2026-07-28T11:57:18-03:00
re: 379_d111_pin_verified_locator_residual
type: escalation
thread: D111-tier3-stale-evidence-pin
---

# D111 escalation after 2/2 evidence rounds

The immutable evidence snapshot, completed-rep inventory, appendix locator,
and gate locator are verified. The sole remaining defect is the stale
`ceb91b6` literal at `progress/results-ledger.md:3464`; the same entry already
identifies `1511606` as the current pin.

Author adjudication is requested after that one-line locator cleanup. No
rerun, artifact change, or numerical change is required.
