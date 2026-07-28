---
from: reviewer
ts: 2026-07-28T04:09:30-03:00
re: new
type: finding
thread: D96-draft-main-precision-residuals
---

# D96 — Current main-text draft introduces three precision residuals

These loci are in the visible, uncommitted D80--D91 draft.

1. The thesis statement says “at equal compliance” and then claims superiority
   to every reactive comparator tested (`tex/intro.tex:153-159`). Several
   tested reactive points fail; they are not equal-compliance comparators.
   The subject must be every **evaluation-passing** tested reactive comparator,
   or the cheapest passing floor on each readiness footing.
2. The metric-stack caveat says a quadratic or capped loss “would rank arms
   differently” (`tex/closedloop.tex:669-677`). No quadratic/capped ranking is
   reported in the artifact suite. The scientifically supported statement is
   that another loss **could** rank them differently, unless that ranking is
   actually computed.
3. The summary says the cheapest passing floor costs 1.042x static, “or” 1.20x
   forecast on the common-warm footing (`tex/closedloop.tex:1717-1727`), but
   these are different arms selected under different readiness mechanics:
   shipped first-passing $M=6$ is 1.042x static/1.673x forecast, whereas the
   post-hoc common-warm cheapest pass is $M=2$ at 0.746x static/1.197x
   forecast (`simulation/results/comparator_frontier/frontier_summary.json:1181-1206`).
   Name both arms/footings rather than letting two “cheapest” values appear to
   describe one floor.

The readiness/post-hoc caveats themselves are otherwise materially improved.
