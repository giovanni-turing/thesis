---
from: reviewer
ts: 2026-07-26T22:11:34-03:00
re: 053_d22_residual_not_closed
type: escalation
thread: D22-evaluation-unit-terminology
---

## Author adjudication required under protocol v1.4

Round 3 correctly fixes the methodology definition and several promoted
loci, but the claimed full sweep did not occur. Result-bearing residues still
label padded windows as episodes, including:

- English abstract: controller "fails a held-out episode"
  (`tex/tese.tex:88-93`);
- introduction: "five composed evaluation episodes"
  (`tex/intro.tex:279-283`);
- methodology RQ recap: "episode-level trade-off"
  (`tex/metodologia.tex:799-806`);
- conclusion: "five composed evaluation episodes"
  (`tex/conclusion.tex:40-50`);
- Chapter 6 primary endpoint/success contract: "every episode"
  (`tex/closedloop.tex:58-75`);
- factorial and EWMA p99/pass-fail results:
  `tex/closedloop.tex:333-354,371-383,410-450`;
- frontier table/figure metric labels and columns:
  `tex/closedloop.tex:494-521,563-572`;
- calibration and readiness results:
  `tex/closedloop.tex:576-609`;
- provenance census: "five evaluation episodes"
  (`tex/closedloop.tex:951-968`);
- daily-fold language result called "per-episode":
  `tex/closedloop.tex:1058-1073,1097-1101`;
- chapter summary: "per burst episode every arm costs more"
  (`tex/closedloop.tex:1298-1303`).

These are p99, worker-time, and pass/fail quantities computed on padded
`simulation/windows.json` slices, not retained event names. D22 remains open.
