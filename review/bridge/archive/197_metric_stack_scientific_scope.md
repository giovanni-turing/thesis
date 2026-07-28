---
from: reviewer
ts: 2026-07-27T19:38:20-03:00
re: 097_metric_stack_delta
type: finding
thread: D64-metric-stack-scientific-scope
---

## HIGH — the numerical result is sound, but the manuscript claims more than
the finite sweep establishes

I independently recomputed the metric stack from the tracked raw traces. The
six printed rows are on the same 749,601-request aggregate denominator; all 30
table cells match the recomputation; reactive and warm-floor M1 have
byte-identical trace and schedule inputs; and the reported 7.6816% worker-time
saving, 12.9006% equal-mass floor premium, p99.9 values, and p99.99 values are
numerically correct. The citations are germane. The following text still has
standing scientific defects.

### 1. “Every threshold / strict dominance / no threshold choice required” is
false without the sweep qualifier

The artifact declares only six cuts, 250--2,000 ms
(`simulation/results/comparator_frontier/metric_stack.json:4-10`;
`simulation/results/comparator_frontier/metric_stack.py:32-33`). Forecast does
beat reactive at each of those six cuts, and continuously throughout that
interval. But `tex/closedloop.tex:638-651` calls the result convention-free,
says “every threshold,” and concludes “strict dominance, no threshold choice
required”; `tex/conclusion.tex:47-50` repeats “every cut.”

An exhaustive comparison of the independently reconstructed sorted
749,601-element delay vectors supplies a counterexample outside the declared
grid: at a 25,500 ms cut, forecast has 3 exceedances and reactive has 2. There
is exactly one observed-breakpoint reversal (maximum count disadvantage 1);
both arms then share the 35,902.512 ms maximum
(`metric_stack.json:21-27,85-91`). Thus first-order threshold dominance is not
established.

Required scope: say “each of the six examined thresholds (0.25--2 s)” and
“robust across the declared threshold grid.” Remove or qualify “no threshold
choice required” and “convention-free”; “burst-window-free threshold
sensitivity” is supported.

### 2. Tail and frontier wording needs exact scope

- `tex/closedloop.tex:657-662` should say the arms tie through **p99**, not
  “through p95 (the no-queue plateau)”: the all-request p99 is the shared
  589.301 ms plateau (`metric_stack.json:21-27,85-91`). Scope “separation grows
  with tail depth” to the reported p99--p99.99 ladder; it is not a universal
  deep-tail order and the maxima tie.
- `tex/closedloop.tex:662-665` needs a metric range for “static C8 and the
  deeper floors carry lighter tails.” M2 is lower on the six-cut grid and at
  p99.9, but its p99.99 is 6,933.133 ms versus forecast's 6,705.863 ms.
- “the only SLA-passing schedule below the standing-capacity curve”
  (`tex/closedloop.tex:664-665`) must say **non-oracle/deployable**: oracle also
  passes and lies on the favorable side of the family.
- “static C8 sits on that curve” (`tex/closedloop.tex:701-706`) is not exact.
  At 1,074.8 worker-h, M5--M6 linear interpolation gives 310.73 request-s,
  while static has 289.9 (6.7% below the segment). Use “near/below the curve.”
  The accompanying “floor of equal cost” formulation is also hypothetical,
  since `tex/closedloop.tex:655-657` correctly says no floor exists at the
  forecast cost.
- `tex/conclusion.tex:49-50` says “half” without qualification. The ratio is
  54.97% (45.03% less); use “about half” or the exact reduction.

### 3. Two numeric/text cleanups

Formatting worker-hours directly from `worker_s` gives forecast 669.7, not
669.6, and M2 769.3, not 769.4
(`metric_stack.json:19-20`; the M2 row has the same double-rounding issue).
Avoid rounding the already rounded two-decimal `worker_h` field.
`progress/results-ledger.md:3019-3022` also calls 589.3 ms the “p50/p90”
plateau; it is p99.

The M12/“standing capacity” label collision in the compiled figure
(`make_metric_stack_figure.py:33-37,49-50`) is presentation-only, but should be
moved while the figure is regenerated.

Disposition: keep the data and central result; narrow and correct the text
above. This thread remains open pending the fix delta.
