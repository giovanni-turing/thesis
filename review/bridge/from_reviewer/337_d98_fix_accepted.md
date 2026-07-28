---
from: reviewer
ts: 2026-07-28T05:35:07-03:00
re: 147_d98_worker_hour_operands_fix
type: response
thread: D98-worker-hour-operand-selection-scope
---

# D98 — Fix accepted at evidence round 2/2

The worker-hour crib now makes the required distinction
(`defense/defense-qa.tex:3028-3038`): threshold-free arithmetic begins only
after the declared population and arms are fixed, while the operands retain
their selection conventions. It identifies 669.7 h as the Chronos p90
schedule and static $C=8$ as the minimum fleet selected by the every-window
SLA feasibility rule.

The current standalone defense artifact is 61 pages; its log has no LaTeX
error, undefined-control, fatal, or emergency-stop diagnostic, and
`git diff --check -- defense/defense-qa.tex` is clean.

No semantic residual remains in D98. Accepted for terminal verification once
the corrected source state is committed.
