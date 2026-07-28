---
from: reviewer
ts: 2026-07-28T03:51:37-03:00
re: new
type: finding
thread: D80-issued-lead-horizon-scope
---

# D80 — Forecast-evaluation horizon is conflated with realizable issued lead

This is a standing scientific-scope defect.

The predictor chapter first states that the 15-second archive covers
$h=1\ldots12$, or 15--180 seconds (`tex/predictors.tex:126-129`), but then
calls $\{15,30,45,300\}$ seconds the tested encoder startup leads
(`tex/predictors.tex:130-132`). Its summary and the thesis conclusion compress
that to tested 15--300-second startup leads (`tex/predictors.tex:371-376`;
`tex/conclusion.tex:29-35`).

The closed-loop chapter now establishes the narrower operational fact:

- the issue-time grid is $\{15,30,45,165\}$ seconds
  (`tex/closedloop.tex:344-347`);
- the 15-second, $H=12$ archive supplies at most
  $(12-1)\times15=165$ seconds of forecast-issued lead
  (`tex/closedloop.tex:354-356`);
- the old 300-second cell reached the plateau only through target-time
  indexing and is explicitly an upper bound, not an issued lead
  (`tex/closedloop.tex:356-358`).

The one-minute forecast evaluation does extend beyond 300 seconds
(`tex/predictors.tex:127-130`), but that is not a realizable 300-second
issue-time closed-loop result. Please separate forecast-evaluation horizon from
actuation evidence everywhere: the controller evidence covers issued leads
15--165 seconds; 300 seconds may be described only as lying inside the
one-minute forecast-evaluation horizon or as the superseded target-indexed
diagnostic.
