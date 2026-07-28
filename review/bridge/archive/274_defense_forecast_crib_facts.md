---
from: reviewer
ts: 2026-07-28T03:51:37-03:00
re: new
type: finding
thread: D84-defense-forecast-crib-facts
---

# D84 — Defense forecast-calibration and WAPE crib facts are stale

Two factual defense aids no longer match the evidence.

1. The Q&A says horizon- and burst-conditional coverage are open and
   per-step calibration is unmeasured
   (`defense/defense-qa.tex:720-731`;
   `defense/defense-qa.tex:902-914`). The manuscript now reports
   horizon-step coverage across all twelve steps
   (`tex/predictors.tex:126-130`) and pooled in-burst versus outside-burst
   coverage (`tex/predictors.tex:104-123`). What remains absent is
   onset-stratified, per-episode calibration—not all horizon- or
   burst-conditional evidence.
2. The rapid-fire crib labels 98.8%/146.1% WAPE as images at one minute
   (`defense/defense-qa.tex:1463-1468`). Canonical metrics show one-minute
   Chronos-cov 52.9% and EWMA 54.2%
   (`predictors/results/metrics/summary.md:24-34`); 98.8% and 146.1% are the
   one-second Toto and EWMA values
   (`predictors/results/metrics/summary.md:240-250`).

Please distinguish existing horizon-step and pooled-burst evidence from the
missing episode/onset-stratified statistic, and correct the crib to:
images@1min 52.9% versus 54.2%; images@1s 98.8% versus 146.1% (with the
zero-predictor 100% caveat where relevant).
