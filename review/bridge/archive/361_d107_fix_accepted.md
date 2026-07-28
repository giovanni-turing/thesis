---
from: reviewer
ts: 2026-07-28T09:19:30-03:00
re: 162_d107_precision_wording_fixed
type: response
thread: D107-retiming-precision-overclaims
---

# D107 — Fix accepted at evidence round 2/2

The retiming paragraph now gives the per-N table its supported role: a second
frozen-dispatch service representation, explicitly not a test of composition
re-formation (`tex/metodologia.tex:351-358`). The reconstruction statement now
matches the implemented numerical gate rather than claiming byte identity
(`tex/metodologia.tex:382-386`;
`simulation/silicon_anchor_runner.py:793-803`), and the integration ledger is
consistent (`progress/results-ledger.md:3425-3430`).

The reported estimands and verdicts are unchanged. The current 135-page PDF
postdates the edited sources, has no LaTeX error or undefined-reference
diagnostic, and the live metric-stack gate passes. D107 has no substantive
residual.
