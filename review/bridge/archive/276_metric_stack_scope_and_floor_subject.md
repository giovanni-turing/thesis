---
from: reviewer
ts: 2026-07-28T03:51:37-03:00
re: new
type: finding
thread: D86-metric-stack-scope-and-floor-subject
---

# D86 — Convention-minimized wording and floor subject remain too absolute

Two local corrections are needed in the convention-minimized metric-stack
discussion.

First, “Total delay mass is not another convention”
(`tex/closedloop.tex:650-660`) is too absolute. The integral removes the
choice of an SLA threshold or percentile, but it remains conditional on the
declared evaluation population/span, encoder-delay definition, and linear loss
functional. A rigorous compact statement is that it introduces no
SLA-threshold or percentile cut under the declared population and delay
definition.

Second, the paragraph says “Static C=8 and the deeper floors,” explicitly
mentions $M=2$, then attributes a 1.6--1.7x bill and compliance to every one of
them (`tex/closedloop.tex:720-737`). Under shipped mechanics $M=2$ costs
2,769,659.6 worker-seconds, only 1.149x the 2,410,754.7 forecast point, and
fails burst3 at 9,352.179 ms
(`simulation/results/comparator_frontier/EVAL_RESULTS.json:157-165`).
Static C=8 passes at 1.605x forecast
(`simulation/results/comparator_frontier/EVAL_RESULTS.json:197-205`), and the
cheapest passing shipped floor $M=6$ costs 1.673x forecast
(`simulation/results/comparator_frontier/EVAL_RESULTS.json:207-215`).

Please narrow the subject of the 1.6--1.7x/pass sentence to static C=8 and the
cheapest passing shipped floor M=6; do not imply that every deeper floor or
the cited M=2 shares that cost and verdict.
