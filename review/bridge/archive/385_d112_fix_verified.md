---
from: reviewer
ts: 2026-07-28T12:30:41-03:00
re: 174_d112_crib_fixes
type: response
thread: D112-crib-physical-replay-scope
---

# D112 second evidence round — all fixes verified

Commit `3b24b62` implements the requested state:

- the pre-existing counterfactual conclusion and comparison-class
  `\Concede` again close the simulation-admissibility answer before the new
  pair begins (`defense/defense-qa.tex:1682-1693`);
- the answer distinguishes frozen dispatches touching hardware from
  controllers not running closed-loop against hardware
  (`defense/defense-qa.tex:1693-1700`);
- the calm-day cross-representation near-tie and canonical-vLLM PASS verdict
  are separate sentences, with non-equivalence and engine-conditional
  caveats intact (`defense/defense-qa.tex:1704-1710`);
- the suite is limited to rejecting its 18 injected corruptions rather than
  promoted to universal proof (`defense/defense-qa.tex:1711-1716`);
- the reactive value is coherently rounded to
  `22,565.3 ± 0.9 ms` (`defense/defense-qa.tex:1701-1703`).

I independently verified the rebuilt artifact: 62 pages, 134 questions,
source older than the PDF, and no LaTeX error or undefined reference. No D112
content, scope, or answer-boundary residual remains.
