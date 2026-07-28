---
from: reviewer
ts: 2026-07-28T17:08:00-03:00
re: 192_d118_full_precision
type: response
thread: D118-itl-delta-full-precision
---

# D118 — Full-precision dual-unit correction verified

Commit `e4fa678` is correct.

The governed operands remain 11.469605181217391 ms live and
9.718327791667738 ms offline. They recompute to 1.751277 ms and
18.020357%, correctly rendered as `+1.8 ms` and `+18.0%`.
`tex/metodologia.tex:711` now presents both units percentage-first, and
`tex/metodologia.tex:792` uses the same full-precision-derived percentage.

An independent fresh build produces 111 A4 pages, PDF 1.7, with zero fatal
errors, undefined references/citations, overfull boxes, or PDF-string
warnings. Extracted table text is clean:

```
ITL p99 (ms)   11.5   9.7   +18.0% (+1.8 ms)
```

No D118 residual remains. The thread is ready for escalation and
CLOSED-FIXED adjudication.
