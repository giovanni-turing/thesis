---
from: reviewer
ts: 2026-07-28T03:23:50-03:00
re: new
type: finding
thread: D75-distribution-independence-equivalence-guarantee
---

## D75 — four statistical-inference scope defects

These require wording corrections, not new experiments.

### 1. Equal selected quantiles are not identical distributions

English `tex/tese.tex:86-90`, Portuguese `tex/tese.tex:166-171`, and
`tex/closedloop.tex:726-731` say the forecast and reactive encoder-delay
distributions are “identical through p99.”

The artifact supports equality only at the selected all-request quantiles
p50, p90, p95, and p99:

```text
forecast: p50 0.0, p90 52.392, p95 141.5, p99 589.301 ms
reactive: p50 0.0, p90 52.392, p95 141.5, p99 589.301 ms
```

But the CDFs differ below p99:

```text
count >250 ms: forecast 31,066; reactive 31,536
count >500 ms: forecast 20,512; reactive 20,988
total delay: 30,277.488 vs 34,015.615 request-s
```

Source:
`simulation/results/comparator_frontier/metric_stack.json:21-29,41-53,90-98,110-122`.
The body itself admits at `tex/closedloop.tex:729-731` that the p99 tie is not
a statement about the distributions.

Safe repair at all three loci: “the selected all-request quantiles through
p99 (p50/p90/p95/p99) coincide; the upper tails differ,” or retain only the
exact p99 tie.

### 2. Weak rank association is promoted to independence

`tex/trace-eda.tex:286-294` correctly limits the tested relations to
constant-fraction scaling, rank correlation, and lagged linear
cross-correlation, explicitly leaving nonlinear relations open, but then
calls image count and generation length “independent” from Spearman
\(-0.06\) and flat per-bucket medians.

Those summaries can reject a useful monotonic relationship; they do not
establish statistical independence.

Safe repair: “weakly rank-correlated (Spearman \(-0.06\)), with no monotonic
trend under the tested bucket summaries.”

### 3. Failure to distinguish from zero is called equivalence

`tex/predictors.tex:353-356` and `tex/closedloop.tex:431-433` call ARIMA
“statistically indistinguishable from Chronos.” The actual paired-origin
bootstrap interval for ARIMA minus Chronos-cov is
\([-4.6031,+6.9480]\) WAPE points:
`predictors/matched_origin_rescore_2026-07-26.json:340-348`.

That interval includes zero and also material differences in both directions;
there is no prespecified equivalence margin or equivalence test. The precise
wording already exists at `tex/predictors.tex:283-286`: the paired-origin
bootstrap “cannot distinguish [the gap] from zero.”

Use that wording at both propagated loci. Likewise, if retaining
“statistically significant” for Toto at `tex/predictors.tex:286`, name the
actual scope: its 95% paired-origin-bootstrap interval excludes zero
(`...json:364-368`). The bootstrap resamples 300 time-ordered origins
independently (`...json:340-341`), so it is not a day/block-level population
test.

### 4. Empirical common-span calibration is called a guarantee

`tex/predictors.tex:142-152` says “Calibration guarantees that about one bin
in ten sits above the provisioned edge,” then reports the observed
common-span rates for one consumed cell: 10.9% overall and 11.2% in bursts.
This is an empirical frequency, not a future or distribution-free guarantee.

Safe repair: “On the common span, the calibrated edge leaves about one bin in
ten above it,” retaining the consumed-cell qualifier required by D73.
