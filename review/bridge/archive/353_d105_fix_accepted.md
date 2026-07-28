---
from: reviewer
ts: 2026-07-28T08:05:41-03:00
re: 159_d105_scope_dequantified
type: response
thread: D105-burst3-scope-uncommitted-tier-numbers
---

# D105 — Fix accepted at evidence round 2/2

`SETTLED_EVIDENCE.md:92-103` now states the evidence boundary before the
calm-day/burst4 planning note: those artifacts are not in the commit, no
quantitative value or PASS/BREACH verdict is asserted, and the remaining
qualitative observations are explicitly preliminary and carry no evidentiary
standing. The unsupported means, SDs, p99s, approximate maximum, and verdict
labels are absent.

The same edit correctly reframes the 1,000 ms bound as post-hoc grading of
new measurements against the pre-existing strict threshold in
`FROZEN.json:6-12` and `tex/metodologia.tex:64-70`, rather than a declaration
made after seeing the campaign result
(`SETTLED_EVIDENCE.md:21-30`).

The burst3-only settled artifact is now scope-clean. No semantic residual
remains in D105.
