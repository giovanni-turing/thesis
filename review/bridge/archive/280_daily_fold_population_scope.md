---
from: reviewer
ts: 2026-07-28T04:01:47-03:00
re: new
type: finding
thread: D89-daily-fold-population-scope
---

# D89 — Claim-bounds paragraph collapses two failing daily folds into one

The conclusion currently says “one daily fold misses the encoder bound”
(`tex/conclusion.tex:203-208`). Pure forecast actually fails two whole
calendar folds for different reasons:

- F2 p99 is 1318.984 ms
  (`simulation/results/encoder_hybrid/folds/F2_fc.jsonl.stats.json:38-42`);
  this is the partial-archive coverage failure;
- F6 p99 is 1264.206 ms
  (`simulation/results/encoder_hybrid/folds/F6_fc.jsonl.stats.json:38-42`);
  this is the genuine missed onset inside forecast coverage.

The body already distinguishes the archive-coverage and covered-onset cases in
the daily-fold audit. Please preserve that population in the conclusion:
one fully forecast-covered daily fold misses the bound, and a second partially
covered fold also fails because the fixed-context forecast archive does not
cover it fully. “One daily fold” alone understates the observed whole-fold
failure count.
