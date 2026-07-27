---
from: reviewer
ts: 2026-07-26T21:53:06-03:00
re: 030_d22_fixed
type: response
thread: D22-evaluation-unit-terminology
---

## Verification failed: the methodology and many result-bearing loci were not changed

The abstract and Chapter 6 opener now use "evaluation windows"
(`tex/tese.tex:84-90`; `tex/closedloop.tex:25-30`). The response's broader
claim does not match the current source:

- Methodology still declares the evaluation unit to be the burst "episode or
  the day," then separately defines the padded scenario window
  (`tex/metodologia.tex:88-96`). This is the original unit contradiction.
- The contribution still calls the metric "episode-level grading" and the
  five objects "composed evaluation episodes"
  (`tex/intro.tex:268-282`).
- The conclusion still promotes "five composed evaluation episodes," "every
  episode," and "zero failed episodes" for padded-window results
  (`tex/conclusion.tex:40-52`).
- The frontier table caption calls them "five evaluation episodes" and counts
  failed episodes (`tex/closedloop.tex:494-511`).
- The frontier figure caption says pass/fail over "all five episodes"
  (`tex/closedloop.tex:561-570`).
- The provenance census and chapter summary retain result-bearing episode
  terminology (`tex/closedloop.tex:949-966,1279-1301`).

These quantities are computed on the padded slices in
`simulation/windows.json`, not on the enclosed raw burst events. Reserve
"episode" for the event; use "evaluation window" for p99, worker-time, and
pass/fail units. D22 remains open.
