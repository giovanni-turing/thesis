---
from: reviewer
ts: 2026-07-26T21:39:12-03:00
re: new
type: finding
thread: D16-regime-u-residuals
---

## Moderate — the corrected `U` regime still contains unit, threshold, and grounding contradictions

Four exact residues remain after the otherwise-correct D05/D06 rewrite:

1. `tex/conclusion.tex:107-112` calls `thr_60s_224` a
   "60 s/224-worker detection threshold." The artifact quantity is
   224 **images/s** at 60-second aggregation, not 224 workers
   (`onset_audit_issuetime.json:275-303`).
2. The row condition is `U >= L`, but the same measured-instance cell reports
   the strict-threshold `U=15 s` against `L=30 s`. Only the coarse
   60-second/224-images-per-second reading (`U=345 s`) supports a full startup
   lead; the strict 15-second/286-images-per-second crossing has positive
   anticipation but cannot hide a 30-second startup
   (`onset_audit_issuetime.json:367-395`).
3. Chapter 6 still calls burst4 a threshold-unspecified "345 second usable
   issue-lead" (`tex/closedloop.tex:386-390`), so the new threshold caveat has
   not propagated to the load-bearing mechanism paragraph.
4. The "Nothing responds" row assigns `U approximately 0` to a fixed-topology
   measurement in which neither a forecast path nor an aggregate-signal
   controller was instantiated (`tex/conclusion.tex:138-145`). Under the
   caption's definition, `U` is undefined there, not measured as zero.

State separately: positive forecast anticipation (`U>0`), enough issued lead
to hide startup (`U>=L`) at a named threshold, and signal-decoupled
non-responsiveness where no `U` was measured.
