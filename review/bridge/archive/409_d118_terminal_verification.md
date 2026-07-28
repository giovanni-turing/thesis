---
from: reviewer
ts: 2026-07-28T17:10:00-03:00
re: 193_d118_escalation
type: verification
thread: D118-itl-delta-full-precision
---

# D118 — Terminal verification

The recognized delegated ruling in `194_adjudication_d118.md` is
**CLOSED-FIXED**.

The forecast-ITL delta now uses the governed full-precision operands:
11.469605181217391 ms live and 9.718327791667738 ms offline, yielding
1.751277 ms and 18.020357%. The table correctly renders the dual-unit result
as `+18.0% (+1.8 ms)`, and the prose uses the same 18.0%.

The independent 111-page A4 build is clean, including zero fatal,
undefined-reference/citation, overfull-box, and PDF-string diagnostics. No
D118 residual remains.
