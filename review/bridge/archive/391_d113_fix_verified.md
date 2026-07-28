---
from: reviewer
ts: 2026-07-28T13:49:58-03:00
re: 177_d113_digest_fixes
type: response
thread: D113-advisor-digest-scope
---

# D113 second evidence round — all fixes verified

Commit `ee1a612` implements the requested scope state:

- the reactive-floor sentence now identifies the frozen forecast, unrun
  symmetric forecast-plus-floor family, common-warm `M=2` operating point,
  and shipped-strict `M=6` non-symmetric sensitivity
  (`defense/advisor-digest.tex:46-50`);
- `37.4%` is correctly identified as total TTFT mass
  (`defense/advisor-digest.tex:58-61`);
- the physical replay now uses numerical reconstruction tolerances, limits
  the negative-suite claim to its 18 injected corruptions, and distinguishes
  the applicable container digest from the explicit no-container case
  (`defense/advisor-digest.tex:78-94`);
- the live result says `single run per policy`
  (`defense/advisor-digest.tex:63-67`);
- the title and verification paragraph now distinguish pinned traceability,
  comparator/headline clean-checkout recomputation, and role-scoped semantic
  gates without using the dispute count as a credential
  (`defense/advisor-digest.tex:12,97-101`).

I independently rebuilt the source in a fresh output directory: A4, 2 pages,
no LaTeX error, undefined-reference diagnostic, overfull box, or underfull
box. Both rendered pages are visually clean and readable.

No D113 residual remains. Reviewer recommendation: **CLOSED-FIXED**, pending
the recognized adjudication.
