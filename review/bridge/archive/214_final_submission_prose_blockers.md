---
from: reviewer
ts: 2026-07-27T21:11:57-03:00
re: claude:102_203_208_implementation
type: ack
---

## Final thesis-wide sweep: two surgical submission blockers outside D64/D65

The metric-stack correction is scientifically favorable. Two pre-existing
presentation issues remain before an absolute defense/submission close.

### 1. Narrow the defense's approximately 3% silicon claim

`defense/reveal/index.html:602-604` and
`defense/deck_single.html:1002-1005` currently say the “kernel ledger” was
closed against physical measurement to approximately 3%.

That generalizes the attention result to the whole stack:

- attention is within approximately 3%
  (`tex/metodologia.tex:324-326`);
- GEMM is approximately 6% high (`:325-327`);
- AIC-comparable work is within approximately 12% (`:327-330`); and
- the complete measured vLLM vision tower is within 12.8% over the serving
  regime (`:269-275`).

A compact defensible tile is:

> Consumer-GPU encoder anchor (RTX 5090, locked clocks, PR #1312):
> attention within approximately 3%; complete vLLM vision tower within
> 12.8% over N <= 64.

### 2. Remove the printed preliminary-draft note

`tex/tese.tex:205-220` still emits a “Note on this draft” whose source comment
explicitly says “REMOVE for the defense/submission version” and whose text says
institutional formatting and final institutional review remain pending.
Remove that complete printed block for the defense/submission artifact.

These are prose-only corrections. No metric recomputation, figure change, or
chapter restructure is requested. The optional Phase-2 appendix migration can
remain gradual and is not a closeout blocker.
