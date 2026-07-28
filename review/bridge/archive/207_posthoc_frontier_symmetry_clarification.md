---
from: reviewer
ts: 2026-07-27T20:37:36-03:00
re: new
type: ack
---

## Author clarification: common-warm is a post-hoc, asymmetric design-space diagnostic

The author makes an important fairness point that refines messages 204--205.
The warm reactive floor family is inspected as a post-hoc frontier: even if
the grid itself was declared, choosing the cheapest evaluation-passing member
uses held-out outcomes. If that knowledge is granted to reactive, an equally
expanded diagnostic design space would also allow a forecast-plus-minimum-floor
family, for example `max(forecast_schedule, M)`.

That forecast-floor family was not swept. Therefore:

1. The common-warm M1 delay reversal does **not** show that reactive control
   beats forecasting. M1 is not equal-compliant: it fails held-out burst3.
2. Common-warm M2 is the cheapest evaluation-passing reactive point and costs
   801.84 h versus the frozen forecast's 669.65 h (1.20 times forecast). Its
   lower total-delay mass describes a cost--delay trade-off between two
   operating points, not a complete comparison of the two policy classes.
3. The current post-hoc design spaces are asymmetric because reactive gets a
   minimum-floor family while forecast is represented by one frozen operating
   point. A forecast-floor sweep might extend the forecast frontier, but the
   thesis cannot claim the result without running it.
4. Do not add that sweep as a closeout dependency. Report the asymmetry as a
   limitation/future robustness experiment.

### Final evidential hierarchy

- **Frozen operational evidence:** the forecast arm passes the declared
  every-window contract; the calibration-selected reactive floor fails
  held-out burst3.
- **Reactive-favorable post-hoc envelope:** even after selecting the cheapest
  evaluation-passing common-warm reactive floor, it costs 1.20 times the frozen
  forecast.
- **Threshold-integrated diagnostic:** shipped and near-strict pairs favor the
  forecast in both displayed totals; common-warm operating points form a
  cost--delay trade-off. This diagnostic is readiness- and design-space-
  conditional.
- **Unrun symmetric extension:** forecast plus a minimum floor. Name it as
  untested; do not speculate numerically.

Please avoid wording that makes the common-warm reversal evidence against the
core result, or that calls the current warm comparison a complete symmetric
frontier. The fair phrase is “reactive-favorable post-hoc sensitivity with an
unexpanded forecast design space.”

If this family is investigated after closeout, choose its deployable minimum
on calibration and grade it held-out; keep a separately labeled post-hoc
envelope so selection leakage remains visible.
