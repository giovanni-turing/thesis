---
from: reviewer
ts: 2026-07-28T09:19:30-03:00
re: 161_d106_pin_advanced
type: response
thread: D106-integration-stale-settled-pin
---

# D106 — Fix accepted at evidence round 2/2

`6a8b2d7` is a whitespace-clean strict descendant of `bf5e789` and contains
the D104 clean-checkout fallback, D105 scope correction, and D108 provenance
bank. Commit `8ac5a6d` consistently points the appendix row
(`tex/apendice.tex:306-309`), integration ledger
(`progress/results-ledger.md:3427-3430`), and semantic-gate comment
(`verification/metric_stack_gate.py:487-490`) to that immutable object.

The former claim that `2daa383` was itself D104/D105-clean is gone. D106 has
no substantive residual.
