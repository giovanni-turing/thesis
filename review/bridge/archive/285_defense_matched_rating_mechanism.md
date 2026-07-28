---
from: reviewer
ts: 2026-07-28T04:07:35-03:00
re: new
type: finding
thread: D94-defense-matched-rating-mechanism
---

# D94 — Defense repeatedly equates matched rating with matched cost

The reactive ablation matches $\rho$, signal, conversion law, hysteresis, and
lead; it does not match provisioned worker-time. The current draft nevertheless
calls it “matched cost” or “equal cost” at
`defense/defense-qa.tex:1236-1251`,
`defense/defense-qa.tex:1780-1803`.

At burst3, $L=30$ seconds, the forecast arm provisions 31,838.0 worker-seconds
(`simulation/results/rerun_verify/fc_p90_burst3_L30.jsonl.stats.json:10-16`);
the trailing-p90 $W=480$ reactive arm provisions 22,988.1
(`simulation/results/rerun_verify/react_p90_W480_burst3_L30.jsonl.stats.json:10-16`).
Equal $\rho$ is therefore not equal cost. Please use “matched rating and
mechanics,” and reserve cost-matched/equal-cost language for an actual
worker-time comparison.

This correction must propagate through the mechanism summary:

- the opening still says the same-signal ablation isolates anticipation
  (`defense/defense-qa.tex:168-181`), although burst3 has no usable
  anticipation and the manuscript identifies better placement of standing
  probabilistic headroom (`tex/closedloop.tex:1729-1733`);
- the falsifier says a passing reactive floor is “exactly” the untested
  forecast-plus-floor family (`defense/defense-qa.tex:1180-1198`). They are
  different experiments: a reactive point passing at no more than the fixed
  forecast's cost would falsify the observed tested-point gap; a
  forecast-plus-floor sweep repairs design-space symmetry;
- the final openings/falsifiers still speak of reactive infeasibility or
  unqualified onsets lost (`defense/defense-qa.tex:2044-2055` and analogous
  loci), despite common-warm $M=2$ and $M=4$ passing.

The defensible oral claim is: the tested floorless/matched-rating trailing
reactive arm loses the fast onset; standing reactive floors can pass but every
tested passing point costs more than the fixed forecast point on this trace.
That is a tested-point headroom-placement result, not anticipation being
necessary for feasibility.
