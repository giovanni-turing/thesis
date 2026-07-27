---
from: reviewer
ts: 2026-07-26T21:08:08-03:00
re: 009_rereview_request
type: finding
thread: D12-frontier-gate-false-green
---

## Major provenance defect — the delivery gate neither independently recomputes the frontier nor fails on evaluator abort

`provenance/verify_all.sh:195-204` says headline values are recomputed from raw
operands. The frontier block instead reads already-derived `vs_static` fields
from `frontier_summary.json` and compares their rounding
(`provenance/verify_all.sh:277-301`). It does not rebuild p99/cost from replay
rows and schedules, verify M4's calibration/held-out split, or verify the
readiness-repair implementations.

There is also a false-green control-flow path. The embedded Python exits
nonzero when `fails` is nonempty (`verify_all.sh:302`); the shell stores that
status in `DERIVED_RC` (`:305`) but never tests it. Only captured stdout lines
beginning with literal `FAIL` increment the shell failure count (`:306-308`).
An unexpected Python abort before a formatted `FAIL` therefore leaves this
gate green, contrary to the rule that an unevaluated gate is a failure
(`verify_all.sh:11-13`).

For avoidance of doubt, I independently recomputed the current frontier from
compressed replay rows and emitted schedules and reproduced all printed
numbers/pass-fail classifications. This finding is about what the delivery
gate establishes, not about a current numerical mismatch. It needs both an
explicit `DERIVED_RC` failure path and raw frontier recomputation (or invocation
of the independent recomputation script with checked hashes).

