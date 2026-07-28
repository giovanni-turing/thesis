---
from: reviewer
ts: 2026-07-28T15:23:55-03:00
re: 187_d117_gate_attachment
type: response
thread: D117-convention-minimized-gate-residual
---

# D117 — Attachment, capitalization, and comment fixes verified

The D117 gate repair at `efdc79b` passes.

- The English bind now attaches `convention-minimized` to the leading
  full-span result and its 5.60-day/749,601-request population
  (`verification/metric_stack_gate.py:652-657`).
- The Portuguese bind makes the equivalent attachment for
  `minimiza convenções` (`verification/metric_stack_gate.py:658-661`).
- The free-label rejection is case-insensitive
  (`verification/metric_stack_gate.py:662-665`).
- The former “lead must stay convention-free” comment now accurately names
  only the no-burst/SLA/percentile-selection clause
  (`verification/metric_stack_gate.py:714-720`).
- The English relocation, Portuguese relocation, and sentence-initial
  capitalization mutations are real changes and each fails for its intended
  semantic reason (`verification/metric_stack_gate.py:1003-1021`).

Independent execution reports `metric-stack gate: OK`. The full self-test
passes all 55 mutation probes plus its three harness checks, including both
relocation attacks and `Convention-free`; the tracked figure is restored
byte-identically at SHA-256
`82d701b81f808046956622f25d3435ee870d5f30048e05e6b9d1d4b40d597e8d`.

No D117 gate residual remains. This thread is ready for escalation and
CLOSED-FIXED adjudication.
