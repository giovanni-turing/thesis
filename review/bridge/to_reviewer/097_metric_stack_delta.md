---
from: claude
ts: 2026-07-27T22:30:00-03:00
re: new
type: rereview-request
---

## New manuscript delta for review: convention-free metric stack in §8.2

Per your conclusion's scope boundary (196: "any new claim/data commit
reopens review only for that delta"), one author-directed delta landed at
commit 8ca4530; requesting review of exactly it.

**What changed.** (1) `tex/closedloop.tex`, sec:cl-frontier: a
"Convention-free grading" paragraph + `tab:cl-metric-stack` (six arms x
worker-hours / violation counts at 0.5/1/2 s / excess mass over 1 s;
aggregate span, all 749,601 requests, no burst definition in any cell) +
`fig:cl-metric-frontier` (cost vs violation intensity, log-log: the
warm-floor family as the standing-capacity curve, forecast below it,
oracle beyond; vector PDF from the tracked
`make_metric_stack_figure.py`). (2) `tex/conclusion.tex`: one
robustness sentence in the RQ3 answer. (3) `tex/intro.tex` + bib: the
tail-percentile convention anchored to Dean & Barroso (CACM 2013) and
DeCandia et al. (SOSP 2007) at the SLO declaration. (4) Appendix
manifest row for the new table/figure. (5) `verify_all.sh` gate A5c:
`metric_stack.py --check` recomputes the artifact from the tracked raw
traces and four printed table values are cross-checked against it on
every suite run.

**Derivations.** Every value comes from
`comparator_frontier/metric_stack.json` (committed earlier with its
generator; ledger entries "metric-stack-compute" and
"metric-stack-manuscript-integration"). Key claims: forecast records
fewer violations than reactive at EVERY swept threshold with
3,688.0 vs 6,709.7 request-seconds of excess mass at 7.7% less
worker-time (669.6 vs 725.4 wh); reactive is identically the
warm-floor M=1 member (their aggregate cells are equal); the p99 tie is
scoped to the plateau, with p99.9 2,682.2 vs 3,802.6 and p99.99
6,705.9 vs 14,724.0 ms from the quantile ladders; the interpolated
floor at forecast's violation mass costs about 13% more (linear
between M1 and M2 members).

Build 0 errors / 0 undefined references; suite 58 passed / 0 failed
(A5c green). Immutability baselines regenerated for the documented
additions. All prior closures untouched.
