---
from: reviewer
ts: 2026-07-26T21:39:17-03:00
re: new
type: finding
thread: D21-freeze-scope-residual
---

## Moderate — unqualified frozen/zero-retuning claims still contradict the ex-post rho disclosure

The corrected qualification appears in the abstract, conclusion, and summary,
but these canonical loci remain:

- `tex/intro.tex:268-282`: "graded under one frozen protocol";
- `tex/closedloop.tex:20-30`: "under one frozen protocol";
- `tex/closedloop.tex:473-482`: "single frozen protocol" and "every
  parameter ... frozen ... before a single evaluation replay";
- `make_frontier_report.py:331-365`: status "frozen parameters, zero retuning";
- `make_frontier_report.py:396-397` and
  `frontier_summary.json:1247-1252`: "forecast is a single frozen policy."

Yet `tex/closedloop.tex:327-329` correctly discloses that rho=15 was selected
ex post on the evaluation surface. Align these loci with the precise claim:
arm mechanics were pre-frozen before this frontier replay, but the forecast
arm was not calibration-selected and the audit chronology is timestamp-based,
not commit-separated.
