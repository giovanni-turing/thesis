---
from: reviewer
ts: 2026-07-28T17:58:00-03:00
re: 198_d121_barrier
type: response
thread: D121-doi-pagination
---

# D121 round 2 — float barrier independently verified

Verified from a fresh build of `db6b436`:

- 113 A4 pages, PDF 1.7;
- zero fatal errors, undefined references, overfull boxes, or PDF-string
  warnings;
- metric-stack gate OK;
- physical page 103 / printed 83 now completes A.4 with “tracks the record
  status”;
- physical page 104 contains Table A.3 and its caption without A.5 prose;
- physical page 105 opens A.5 and keeps its entire first paragraph, including
  the Phase-E self-lock sentence, together before Table A.4.

The `\clearpage` at `tex/apendice.tex:401` removes the cross-section float
interruption without increasing the 113-page count.  No counterclaim remains
on D121.
