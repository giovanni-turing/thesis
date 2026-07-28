---
from: reviewer
ts: 2026-07-28T04:07:35-03:00
re: new
type: finding
thread: D93-defense-wape-and-horizon-duplicates
---

# D93 — Corrected forecast crib still has contradictory oral answers

The rapid crib was corrected, but an earlier answer still says one-minute
image WAPE is 98.8% versus EWMA 146.1%, interprets it as barely above the
100% zero-predictor, and concludes that models cannot predict the next minute
(`defense/defense-qa.tex:340-359`).

Canonical values are:

- one minute: Chronos-cov 52.9%, EWMA 54.2%
  (`predictors/results/metrics/summary.md:24-34`);
- one second: Toto 98.8%, EWMA 146.1%
  (`predictors/results/metrics/summary.md:240-250`).

This requires an interpretive rewrite, not a number substitution: the
near-no-skill caveat belongs to the one-second cell; the one-minute point
forecast has material skill. The calibrated upper-edge result remains the
operational reason to provision on the quantile.

The same answer set now calls the 15-second $h=1\ldots12$ range “15--180
seconds of lead” (`defense/defense-qa.tex:725-731`). Those are
forecast-evaluation target horizons. Issue-time usable lead is at most
165 seconds, with tested issued leads 15/30/45/165
(`tex/closedloop.tex:348-362`). Please preserve the target-horizon versus
issued-lead distinction in the oral answer too.
