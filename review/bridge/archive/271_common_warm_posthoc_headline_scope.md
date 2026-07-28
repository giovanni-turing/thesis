---
from: reviewer
ts: 2026-07-28T03:51:37-03:00
re: new
type: finding
thread: D81-common-warm-posthoc-headline-scope
---

# D81 — High-visibility comparator claims still hide post-hoc/readiness scope

The body now states the correct boundary: the common-warm floor sweep is a
reactive-favorable post-hoc sensitivity, the forecast remains one fixed point,
and a symmetric forecast-plus-floor family was not run
(`tex/closedloop.tex:686-694`; `tex/closedloop.tex:1595-1601`). Several
high-visibility claims still compress past that boundary.

1. The thesis statement claims a better resource-time “frontier” than reactive
   control given the same signal and standing capacity (`tex/intro.tex:153-155`).
   As written, this reads as policy-class or symmetrically swept dominance,
   which the stated design-space asymmetry does not establish.
2. Both abstracts call the protocol pre-frozen and then say the
   calibration-selected warm floor fails, followed by the cheapest all-passing
   member and a 1.20x claim (`tex/tese.tex:86-101`;
   `tex/tese.tex:166-185`). The conclusion and chapter summary repeat the same
   compression (`tex/conclusion.tex:69-79`;
   `tex/closedloop.tex:1686-1696`).
3. The floor failure needs readiness scope. The frozen calibration choice is
   $M=4$ (`simulation/results/comparator_frontier/FROZEN.json:60-94`). It fails
   under shipped strict re-warm, but unchanged $M=4$ passes the post-hoc
   common-warm diagnostic with zero failed windows
   (`simulation/results/comparator_frontier/frontier_summary.json:1042-1065`;
   common-warm comparison explicitly marked passing at
   `simulation/results/comparator_frontier/frontier_summary.json:1209-1215`).
4. “Forecast is 1.20x cheaper” is ratio-ambiguous. Under common-warm readiness,
   forecast uses 2,410,754.7 worker-seconds and ex-post passing $M=2$ uses
   2,886,614.5 (`simulation/results/comparator_frontier/frontier_summary.json:976-999`;
   comparison at `simulation/results/comparator_frontier/frontier_summary.json:1200-1206`).
   Thus $M2/forecast=1.197390$ and forecast uses 16.485% less worker-time.

The defensible compact claim is tested-point, not class-level: in a
reactive-favorable post-hoc common-warm envelope, the cheapest
evaluation-passing floor costs 1.197 times the fixed forecast point; the
symmetric forecast-plus-floor extension is untested. Please carry that
post-hoc/readiness status into the EN/PT abstracts, thesis statement,
conclusion, and chapter summary, and replace “1.20x cheaper” with either
“the floor costs 1.20x the forecast” or “forecast uses 16.5% less.”
