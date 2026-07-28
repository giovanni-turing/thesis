---
from: reviewer
ts: 2026-07-28T03:51:37-03:00
re: new
type: finding
thread: D83-defense-comparator-staleness
---

# D83 — Defense answers predate the common-warm and daily-fold adjudications

Several high-risk defense answers contradict the current manuscript/artifacts.

## Reactive feasibility versus lower-cost placement

The Q&A says a reactive fast-onset pass would make anticipation unnecessary,
that headroom without anticipation is insufficient, and that the residual is
anticipation (`defense/defense-qa.tex:1160-1175`;
`defense/defense-qa.tex:1212-1228`). It later says a roughly 21-worker floor
was never run (`defense/defense-qa.tex:1756-1767`) and that a nonforecast
static-saving reactive option does not exist (`defense/defense-qa.tex:1621-1631`).

The $M=1\ldots32$ floor family was run (`tex/closedloop.tex:576-584`).
Post-hoc common-warm $M=2$ passes every evaluation window at 0.746x static
(`simulation/results/comparator_frontier/frontier_summary.json:976-999`);
unchanged calibration-frozen $M=4$ also passes at 0.8869x static
(`simulation/results/comparator_frontier/frontier_summary.json:1042-1065`).
The supported mechanism is therefore cheaper placement of standing headroom:
at matched rating trailing reactive fails, while tested passing floors cost
more than the fixed forecast. Forecasting is not established as necessary for
feasibility.

## “Every onset” and causal-selection scope

The two-minute and closing answers say forecast holds through every burst onset
(`defense/defense-qa.tex:102-113`;
`defense/defense-qa.tex:1996-2003`). The finer F6 audit has pure-forecast p99
1264.206 ms (`simulation/results/encoder_hybrid/folds/F6_fc.jsonl.stats.json:41`);
only the post-hoc hybrid clears it at 678.66 ms
(`simulation/results/encoder_hybrid/folds/F6_hybrid.jsonl.stats.json:41`).
The accurate headline is all five declared evaluation windows at 0.62x, with
one additional daily-fold miss recovered post hoc at 0.76x.

The Q&A also says 0.62x uses “only causal information”
(`defense/defense-qa.tex:1784-1791`). Runtime issue-time actuation is causal,
but $\rho=15$ was selected ex post with the whole frontier disclosed
(`tex/closedloop.tex:337-339`;
`simulation/results/comparator_frontier/frontier_summary.json:1251`).

Please synchronize these answers with the live thesis and preserve all three
boundaries: post-hoc common-warm selection, declared-window versus finer-fold
population, and causal actuation versus ex-post operating-point selection.
