---
from: reviewer
ts: 2026-07-26T21:39:18-03:00
re: new
type: finding
thread: D22-evaluation-unit-terminology
---

## Moderate — cross-chapter evaluation-unit terminology still names raw episodes where the metric uses padded windows

Chapter 6 now correctly defines five overlapping evaluation **windows**
(`tex/closedloop.tex:38-49`). The methodology instead says the evaluation unit
is the burst episode/day and then distinguishes the scenario window that
envelops it (`tex/metodologia.tex:88-99`). Promoted/result loci still call the
five graded objects "composed evaluation episodes," including
`tex/tese.tex:84-90`, `tex/intro.tex:274-282`,
`tex/conclusion.tex:40-50`, and multiple Chapter 6 captions/summaries.

The p99 and pass/fail quantities are computed on the padded scenario slices in
`simulation/windows.json`, including their 1,705-request overlap, not on the
raw above-threshold burst episodes. The major independence overclaim is fixed,
but the metric's declared unit remains internally inconsistent. Use
"evaluation window" at result-bearing loci; reserve "episode" for the burst
event enclosed by a window.
