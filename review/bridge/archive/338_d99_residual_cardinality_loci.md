---
from: reviewer
ts: 2026-07-28T05:35:07-03:00
re: 148_d99_sweep_cardinality_fix
type: response
thread: D99-silicon-sweep-cardinality
---

# D99 — Still standing at evidence round 2/2

The story spine and cram-card locus are corrected
(`defense/defense-qa.tex:131-135`,
`defense/defense-qa.tex:2927-2932`), but the same cardinality error remains in
two answers:

- `defense/defense-qa.tex:1628-1630` still calls the experiment “a dense
  sweep of 69 batch sizes” before attaching the $N\le64$ bound;
- `defense/defense-qa.tex:1799-1803` still says “a dense sweep of 69 batch
  sizes, $N=1$ through 512,” although the five values above 64 are sparse
  probes, not a dense continuation.

Please make both loci say that the sweep contains 69 points total: the dense
64-point $N=1,\ldots,64$ serving grid plus five off-cap probes
$\{96,128,192,256,512\}$. Keep the 12.8% claim explicitly scoped to the
in-cap $N\le64$ points. D99 cannot close while a defense answer still teaches
the false 69-point-dense construction.
